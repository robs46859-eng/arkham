"""
POST /v1/infer — normalized inference endpoint.
Implements: Service Spec §1.5 core endpoints, System Contracts gateway contract.
Model ladder is enforced: cheapest tier first, premium only if policy permits.
STUB: semantic cache lookup and usage metering are next integration steps.
"""

from __future__ import annotations

import time
import uuid

from fastapi import APIRouter, Depends

from packages.schemas import InferenceRequest, InferenceResponse
from packages.schemas.gateway import ModelTier, ValidationResult
from ..middleware.auth import require_tenant
from ..providers.registry import registry

router = APIRouter(prefix="/v1", tags=["inference"])


@router.post("/infer", response_model=InferenceResponse)
async def infer(
    request: InferenceRequest,
    _auth: tuple[str, str] = Depends(require_tenant),
) -> InferenceResponse:
    """
    Normalized inference endpoint.
    Authenticates tenant → checks semantic cache (STUB) → selects model tier →
    invokes provider → validates output → emits usage event (STUB).
    """
    start = time.monotonic()

    # 1. Select cheapest valid tier per routing policy
    tier = registry.select_tier(allow_premium=request.options.allow_premium)

    # 2. STUB: semantic cache lookup would go here
    cache_hit = False

    # 3. Invoke provider
    provider_result = await registry.infer(
        tier=tier,
        task_type=request.task_type.value,
        input_text=request.input.text,
        context=request.input.context,
    )

    latency_ms = int((time.monotonic() - start) * 1000)

    # 4. STUB: output schema validation and usage metering would go here
    return InferenceResponse(
        request_id=f"req_{uuid.uuid4().hex}",
        tenant_id=request.tenant_id,
        model_used=ModelTier(provider_result["model_tier"]),
        cache_hit=cache_hit,
        latency_ms=latency_ms,
        cost_estimate=provider_result.get("cost_estimate", 0.0),
        output=provider_result,
        validation=ValidationResult(passed=True),
    )
