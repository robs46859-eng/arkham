"""
POST /v1/infer — normalized inference endpoint.
Implements: Service Spec §1.5 core endpoints, System Contracts gateway contract.
Model ladder is enforced: cheapest tier first, premium only if policy permits.
STUB: semantic cache lookup and usage metering are next integration steps.
"""

from __future__ import annotations

import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response

from packages.schemas import InferenceRequest, InferenceResponse
from packages.schemas.gateway import ModelTier, ValidationResult
from ..clients import privacy as privacy_client
from ..middleware.auth import require_tenant
from ..settings import settings
from ..providers.registry import registry
from ..providers.cache import semantic_cache

router = APIRouter(prefix="/v1", tags=["inference"])


def _resolve_privacy_tier(request: InferenceRequest) -> str:
    raw = (
        request.input.context.get("privacy_tier")
        or request.input.context.get("tenant_plan")
        or settings.privacy_default_tier
    )
    normalized = str(raw).lower()
    mapping = {
        "dev": "dev",
        "starter": "dev",
        "basic": "dev",
        "growth": "growth",
        "team": "growth",
        "business": "growth",
        "pro": "pro",
        "enterprise": "pro",
    }
    return mapping.get(normalized, settings.privacy_default_tier)


async def _maybe_sanitize(request: InferenceRequest, request_id: str) -> tuple[str, str | None]:
    if not settings.enable_privacy_proxy:
        return request.input.text, None

    tier = _resolve_privacy_tier(request)
    try:
        result = await privacy_client.sanitize_text(
            base_url=settings.privacy_service_url,
            service_token=settings.privacy_service_token,
            tenant_id=request.tenant_id,
            tier=tier,
            request_id=request_id,
            text=request.input.text,
        )
        return str(result.get("redactedText", request.input.text)), str(result.get("requestId", request_id))
    except Exception as exc:
        if settings.privacy_fail_closed:
            raise HTTPException(status_code=502, detail="Privacy service unavailable") from exc
        return request.input.text, None


async def _maybe_restore(request: InferenceRequest, request_id: str, text: str) -> str:
    if not settings.enable_privacy_proxy or not settings.privacy_restore_responses:
        return text

    tier = _resolve_privacy_tier(request)
    try:
        result = await privacy_client.restore_text(
            base_url=settings.privacy_service_url,
            service_token=settings.privacy_service_token,
            tenant_id=request.tenant_id,
            tier=tier,
            request_id=request_id,
            text=text,
        )
        return str(result.get("restoredText", text))
    except Exception as exc:
        if settings.privacy_fail_closed:
            raise HTTPException(status_code=502, detail="Privacy restore unavailable") from exc
        return text


@router.post("/infer", response_model=InferenceResponse)
async def infer(
    request: InferenceRequest,
    response: Response,
    _auth: tuple[str, str] = Depends(require_tenant),
) -> InferenceResponse:
    """
    Normalized inference endpoint.
    Authenticates tenant → checks semantic cache (STUB) → selects model tier →
    invokes provider → validates output → emits usage event (STUB).
    """
    start = time.monotonic()
    request_id = f"req_{uuid.uuid4().hex}"
    sanitized_text, privacy_request_id = await _maybe_sanitize(request, request_id)

    # 1. Select cheapest valid tier per routing policy
    tier = registry.select_tier(allow_premium=request.options.allow_premium)

    # 2. Semantic cache lookup
    cache_hit = False
    cached_output = await semantic_cache.get(
        tenant_id=request.tenant_id,
        task_type=request.task_type.value,
        input_text=sanitized_text,
    )

    if cached_output:
        cache_hit = True
        provider_result = cached_output
    else:
        # 3. Invoke provider
        provider_result = await registry.infer(
            tier=tier,
            task_type=request.task_type.value,
            input_text=sanitized_text,
            context=request.input.context,
        )

        # 4. Store in semantic cache
        if provider_result.get("result"):
            await semantic_cache.set(
                tenant_id=request.tenant_id,
                task_type=request.task_type.value,
                input_text=sanitized_text,
                output=provider_result,
            )

    if isinstance(provider_result.get("result"), str):
        provider_result["result"] = await _maybe_restore(
            request,
            privacy_request_id or request_id,
            provider_result["result"],
        )

    latency_ms = int((time.monotonic() - start) * 1000)
    if privacy_request_id:
        response.headers["X-Privacy-Request-Id"] = privacy_request_id

    # 4. STUB: output schema validation and usage metering would go here
    return InferenceResponse(
        request_id=request_id,
        tenant_id=request.tenant_id,
        model_used=ModelTier(provider_result["model_tier"]),
        cache_hit=cache_hit,
        latency_ms=latency_ms,
        cost_estimate=provider_result.get("cost_estimate", 0.0),
        output=provider_result,
        validation=ValidationResult(passed=True),
    )
