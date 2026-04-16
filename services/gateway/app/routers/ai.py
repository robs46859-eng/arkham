"""FullStack single AI endpoint with first automation path."""

from __future__ import annotations

import hashlib
import hmac
import smtplib
import time
import uuid
import csv
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Literal

import redis
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from packages.db import get_db
from packages.models import AutomationLogRecord, TenantAPIKey, UsageEventRecord

from ..auth.tokens import TokenError, verify_token
from .crm import (
    WORKFLOW_MEMORY_SCHEMA_VERSION,
    build_workflow_memory_envelope,
    build_workflow_memory_input_text,
    build_workflow_memory_task_type,
    log_workflow_memory_decision,
    semantic_cache,
    unpack_workflow_memory_envelope,
    workflow_outcome_stats,
    workflow_reuse_min_score,
)
from ..settings import settings

router = APIRouter(prefix="/v1", tags=["ai"])

ModuleName = Literal["discover", "monitor", "convert"]

MODULE_CONFIG = {
    "discover": {"prompt_key": "niche_radar_v1", "model": "qwen3", "ttl_seconds": 24 * 60 * 60},
    "monitor": {"prompt_key": "tech_radar_v1", "model": "claude-haiku", "ttl_seconds": 24 * 60 * 60},
    "convert": {"prompt_key": "autopitch_v1", "model": "claude-sonnet", "ttl_seconds": 4 * 60 * 60},
}
CACHE_VERSION = "fullstack_ai_v2"
CONVERT_WORKFLOW_VERSION = "fullstack-offer.v1"
CONVERT_PROMPT_SCHEMA_VERSION = "fullstack-convert.v1"
WORKFLOW_MEMORY_TIME_SAVED_MS = {
    "convert": 1800,
}

FULLSTACK_PRODUCTS = {
    "solo": {
        "name": "Solo",
        "product_id": "prod_UHovdD34eRiRwB",
        "payment_url": "https://buy.stripe.com/bJe5kw1110EM9Tr0mbfnO01",
        "price": "$12/mo",
    },
    "agency": {
        "name": "Agency",
        "product_id": "prod_UICyBy4ItoEBsW",
        "payment_url": "https://buy.stripe.com/bJefZaeRR4V20iRfh5fnO02",
        "price": "$30/mo",
    },
}

DEFAULT_TARGET_BUYER = (
    "Founders and owners of digital marketing agencies, automation consultants, "
    "and freelance SaaS operators with 1-50 employees already using Make.com, "
    "Zapier, or HubSpot."
)


class AiRequest(BaseModel):
    module: ModuleName
    inputs: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    chain: bool = False
    auto_execute: bool = False
    automation: dict[str, Any] = Field(default_factory=dict)


class AiResponse(BaseModel):
    request_id: str
    tenant_id: str
    module: ModuleName
    prompt_key: str
    model: str
    cache_hit: bool
    output: dict[str, Any]
    automation: list[dict[str, Any]] = Field(default_factory=list)
    usage: dict[str, Any] = Field(default_factory=dict)


def _hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def _split_api_key(api_key: str) -> tuple[str, str]:
    prefix, separator, secret = api_key.partition(".")
    if not separator or not prefix or not secret:
        raise HTTPException(status_code=401, detail="Invalid API key format.")
    return prefix, secret


def _list_api_keys(db: object) -> list[TenantAPIKey]:
    if hasattr(db, "_objects"):
        return [record for record in db._objects.values() if isinstance(record, TenantAPIKey)]
    if hasattr(db, "query"):
        return list(db.query(TenantAPIKey).all())
    raise HTTPException(status_code=500, detail="Database session does not support API key lookup.")


def _resolve_tenant_from_api_key(db: object, api_key: str) -> str:
    key_prefix, secret = _split_api_key(api_key.strip())
    secret_hash = _hash_secret(secret)
    for record in _list_api_keys(db):
        if record.key_prefix != key_prefix or not record.is_active:
            continue
        if hmac.compare_digest(record.secret_hash, secret_hash):
            record.last_used_at = datetime.utcnow()
            record.updated_at = record.last_used_at
            if hasattr(db, "commit"):
                db.commit()
            return record.tenant_id
    raise HTTPException(status_code=401, detail="Invalid API key.")


def _resolve_tenant(db: object, authorization: str | None, x_tenant_id: str | None) -> str:
    if x_tenant_id and x_tenant_id.startswith("tenant_") and settings.is_test:
        return x_tenant_id

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Authorization: Bearer <api_key> is required.")

    credential = authorization[7:].strip()
    try:
        payload = verify_token(credential, signing_key=settings.effective_signing_key)
        tenant_id = payload.get("sub", "")
        if tenant_id.startswith("tenant_"):
            return tenant_id
    except TokenError:
        pass

    return _resolve_tenant_from_api_key(db, credential)


def _cache_key(module: str, inputs: dict[str, Any], context: dict[str, Any]) -> str:
    normalized = f"{CACHE_VERSION}:{module}:{inputs!r}:{context!r}"
    return f"cache:{hashlib.md5(normalized.encode('utf-8')).hexdigest()}"


def _redis_client():
    try:
        return redis.Redis.from_url(settings.redis_url, decode_responses=True)
    except Exception:
        return None


def _build_module_output(request: AiRequest) -> dict[str, Any]:
    if request.module == "discover":
        keywords = request.inputs.get("keywords", [])
        return {
            "niches": [{"name": str(keyword), "score": 0.74, "tags": ["b2b", "automation"]} for keyword in keywords],
            "domains": [],
            "opportunity_score": 0.74 if keywords else 0.5,
        }

    if request.module == "monitor":
        products = request.inputs.get("products", [])
        return {
            "products": [
                {"name": str(product), "version": "unknown", "changes": [], "sentiment_score": 0.0, "alerts": []}
                for product in products
            ]
        }

    product_key = str(request.automation.get("product") or request.inputs.get("product") or "solo").lower()
    product = FULLSTACK_PRODUCTS.get(product_key, FULLSTACK_PRODUCTS["solo"])
    target_buyer = request.inputs.get("target_buyer") or DEFAULT_TARGET_BUYER
    pain_point = request.inputs.get("pain_point") or "manual prospecting and follow-up"
    payment_url = request.automation.get("payment_url") or request.inputs.get("payment_url") or product["payment_url"]

    pitch = {
        "headline": request.inputs.get("headline") or f"{request.inputs.get('industry', 'Your business')} automation that ships",
        "body": request.inputs.get("body")
        or (
            f"FullStack helps {str(target_buyer).rstrip('.')} turn {pain_point} into an automated Discover -> Monitor -> Convert "
            f"pipeline, with payment and follow-up handled from the gateway."
        ),
        "time_saved": request.inputs.get("time_saved") or "5-10 hours per week",
        "cost_equiv": request.inputs.get("cost_equiv") or "$500-$1,500/month",
        "roi_days": request.inputs.get("roi_days") or 30,
        "cta": request.inputs.get("cta") or f"Want to try {product['name']} for {product['price']}?",
    }
    return {
        "pitch": pitch,
        "template_id": "autopitch_v1",
        "product": product,
        "execution": {
            "email": {
                "to": request.automation.get("to"),
                "subject": request.automation.get("subject") or pitch["headline"],
                "body": f"{pitch['body']}\n\n{pitch['cta']}\n\n{payment_url or ''}".strip(),
            },
            "crm_payload": {
                "industry": request.inputs.get("industry"),
                "pain_point": request.inputs.get("pain_point"),
                "payment_url": payment_url,
            },
            "follow_up_sequence": request.automation.get("follow_up_sequence", [2, 5, 10]),
        },
    }


def _convert_workflow_metadata(request: AiRequest, config: dict[str, Any]) -> dict[str, Any]:
    product_key = str(request.automation.get("product") or request.inputs.get("product") or "solo").lower()
    target_buyer = str(request.inputs.get("target_buyer") or DEFAULT_TARGET_BUYER)
    stage = str(request.automation.get("stage") or request.inputs.get("stage") or "first_touch")
    workflow_name = str(request.automation.get("workflow_name") or "fullstack_outreach")
    offer_version = str(request.automation.get("offer_version") or request.inputs.get("offer_version") or CONVERT_WORKFLOW_VERSION)
    return {
        "workflow_name": workflow_name,
        "offer_type": product_key,
        "offer_version": offer_version,
        "stage": stage,
        "audience": target_buyer,
        "prompt_key": str(config["prompt_key"]),
        "prompt_schema_version": CONVERT_PROMPT_SCHEMA_VERSION,
        "workflow_memory_schema_version": WORKFLOW_MEMORY_SCHEMA_VERSION,
    }


def _convert_workflow_context(request: AiRequest, config: dict[str, Any]) -> dict[str, Any]:
    metadata = _convert_workflow_metadata(request, config)
    return {
        "workflow_name": metadata["workflow_name"],
        "offer_type": metadata["offer_type"],
        "offer_version": metadata["offer_version"],
        "stage": metadata["stage"],
        "audience": metadata["audience"],
        "industry": request.inputs.get("industry"),
        "pain_point": request.inputs.get("pain_point") or "manual prospecting and follow-up",
        "prompt_key": metadata["prompt_key"],
        "prompt_schema_version": metadata["prompt_schema_version"],
    }


def _convert_workflow_input_text(request: AiRequest, config: dict[str, Any]) -> str:
    metadata = _convert_workflow_metadata(request, config)
    industry = str(request.inputs.get("industry") or "general")
    pain_point = str(request.inputs.get("pain_point") or "manual prospecting and follow-up")
    return (
        f"workflow={metadata['workflow_name']}\n"
        f"audience={metadata['audience']}\n"
        f"industry={industry}\n"
        f"pain_point={pain_point}"
    )


def _validate_recalled_convert_payload(
    payload: dict[str, Any] | None,
    workflow_memory: dict[str, Any],
    expected_metadata: dict[str, Any],
) -> tuple[bool, str]:
    if not isinstance(payload, dict):
        return False, "bad_payload"
    if not isinstance(workflow_memory, dict):
        return False, "missing_envelope"
    if workflow_memory.get("schema_version") != WORKFLOW_MEMORY_SCHEMA_VERSION:
        return False, "schema_version_mismatch"
    cached_metadata = workflow_memory.get("metadata")
    if not isinstance(cached_metadata, dict):
        return False, "bad_metadata"
    required_keys = [
        "workflow_name",
        "offer_version",
        "stage",
        "audience",
        "prompt_key",
        "prompt_schema_version",
    ]
    for key in required_keys:
        if cached_metadata.get(key) != expected_metadata.get(key):
            return False, f"{key}_mismatch"
    expected_payload_keys = {"pitch", "template_id", "product", "execution"}
    if not expected_payload_keys.issubset(payload.keys()):
        return False, "partial_payload"
    return True, "hit"


def _workflow_memory_observability(module: ModuleName) -> dict[str, Any]:
    return {
        "enabled": bool(module == "convert" and settings.enable_semantic_cache),
        "attempted": False,
        "status": "disabled",
        "reason": None,
        "task_type": None,
        "estimated_time_saved_ms": 0,
        "stored": False,
    }


def _workflow_memory_reason_path(workflow_memory: dict[str, Any], cache_hit: bool) -> list[str]:
    path: list[str] = []
    if not workflow_memory.get("attempted"):
        return ["cache_disabled", "decision:regenerate"]
    path.append("recall_attempted")
    if cache_hit:
        path.extend(["cache_found", "validation:hit", "quality_gate:pass", "decision:reuse"])
        return path
    reason = str(workflow_memory.get("reason") or "not_found")
    if reason == "not_found":
        path.extend(["cache_miss", "decision:regenerate"])
        return path
    if reason == "low_quality_score":
        path.extend(
            [
                "cache_found",
                "validation:hit",
                "policy:auto_reuse_requires_nonnegative_score",
                "quality_gate:fail",
                "decision:regenerate",
            ]
        )
        return path
    path.extend(["cache_found", f"validation:{reason}", "decision:regenerate"])
    return path


def _workflow_memory_decision_summary(workflow_memory: dict[str, Any], cache_hit: bool) -> str:
    decision = "reused" if cache_hit else "regenerated"
    reason = str(workflow_memory.get("reason") or ("hit" if cache_hit else "not_found"))
    score = workflow_memory.get("score")
    threshold = workflow_memory.get("reuse_threshold")
    if reason == "low_quality_score" and score is not None and threshold is not None:
        return (
            f"{decision} because auto-reuse requires a nonnegative score; "
            f"score {float(score):.2f} vs threshold {float(threshold):.2f}"
        )
    if score is not None and threshold is not None:
        return f"{decision} because {reason}; score {float(score):.2f} vs threshold {float(threshold):.2f}"
    return f"{decision} because {reason}"


def _lead_value(lead: dict[str, Any], *keys: str) -> str:
    normalized = {str(key).strip().lower().replace(" ", "_"): value for key, value in lead.items()}
    for key in keys:
        value = normalized.get(key)
        if value:
            return str(value).strip()
    return ""


def _load_leads(automation: dict[str, Any]) -> list[dict[str, Any]]:
    leads = automation.get("leads")
    if isinstance(leads, list):
        return [lead for lead in leads if isinstance(lead, dict)]

    csv_path = automation.get("lead_csv_path")
    if not csv_path:
        return []

    path = Path(str(csv_path)).expanduser()
    if not path.exists():
        raise HTTPException(status_code=400, detail=f"Lead CSV not found: {path}")

    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _personalize_email(base_email: dict[str, Any], lead: dict[str, Any], product: dict[str, Any]) -> dict[str, Any]:
    email = _lead_value(lead, "email", "email_address", "work_email", "person_email")
    first_name = _lead_value(lead, "first_name", "firstname", "name").split(" ")[0] or "there"
    company = _lead_value(lead, "company", "company_name", "organization", "organization_name") or "your team"
    title = _lead_value(lead, "title", "job_title", "headline") or "Founder"
    technographics = _lead_value(lead, "technologies", "technographics", "technology", "keywords") or "your automation stack"

    base_body = str(base_email.get("body", "")).strip()
    product_line = "" if product["payment_url"] in base_body else f"\n\n{product['name']}: {product['payment_url']}"

    body = (
        f"Hi {first_name},\n\n"
        f"I noticed {company} fits the FullStack buyer profile: {title}s already working around "
        f"{technographics}.\n\n"
        f"{base_body}"
        f"{product_line}"
    ).strip()

    return {
        **base_email,
        "to": email,
        "subject": base_email.get("subject") or f"FullStack for {company}",
        "body": body,
        "lead": {
            "first_name": first_name,
            "company": company,
            "title": title,
            "technographics": technographics,
        },
    }


def _send_email(email_payload: dict[str, Any]) -> dict[str, Any]:
    to_address = email_payload.get("to")
    if not to_address:
        return {"action": "email.send", "status": "skipped", "reason": "missing_recipient"}

    if settings.automation_dry_run:
        return {"action": "email.send", "status": "dry_run", "payload": email_payload}

    if not all([settings.smtp_host, settings.smtp_username, settings.smtp_password, settings.email_from]):
        return {"action": "email.send", "status": "blocked_missing_smtp_config", "payload": email_payload}

    message = EmailMessage()
    message["From"] = settings.email_from
    message["To"] = str(to_address)
    message["Subject"] = str(email_payload.get("subject", "FullStack"))
    if settings.email_reply_to:
        message["Reply-To"] = settings.email_reply_to
    message.set_content(str(email_payload.get("body", "")))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
        smtp.starttls()
        smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)

    return {"action": "email.send", "status": "sent", "to": to_address}


def _log_automation(db: object, tenant_id: str, result: dict[str, Any]) -> None:
    record = AutomationLogRecord(
        id=f"auto_{uuid.uuid4().hex}",
        tenant_id=tenant_id,
        action=str(result.get("action", "unknown")),
        status=str(result.get("status", "unknown")),
        payload=result,
        created_at=datetime.utcnow(),
    )
    if hasattr(db, "add"):
        db.add(record)
    if hasattr(db, "commit"):
        db.commit()


def _log_usage(db: object, tenant_id: str, module: str, model: str, cost: float) -> None:
    record = UsageEventRecord(
        id=f"usage_{uuid.uuid4().hex}",
        tenant_id=tenant_id,
        service=f"fullstack.{module}.{model}",
        cost=cost,
        timestamp=datetime.utcnow(),
    )
    if hasattr(db, "add"):
        db.add(record)
    if hasattr(db, "commit"):
        db.commit()


@router.post("/ai", response_model=AiResponse)
async def ai(
    request: AiRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
    db: object = Depends(get_db),
) -> AiResponse:
    start = time.monotonic()
    tenant_id = _resolve_tenant(db, authorization, x_tenant_id)
    config = MODULE_CONFIG[request.module]
    request_id = f"req_{uuid.uuid4().hex}"
    cache_hit = False
    workflow_memory = _workflow_memory_observability(request.module)

    cache_key = _cache_key(request.module, request.inputs, request.context)
    client = _redis_client()
    output: dict[str, Any] | None = None

    if client:
        try:
            cached = client.get(cache_key)
            if cached:
                import json

                output = json.loads(cached)
                cache_hit = True
        except Exception:
            output = None

    if output is None and request.module == "convert":
        workflow_metadata = _convert_workflow_metadata(request, config)
        workflow_context = _convert_workflow_context(request, config)
        reuse_threshold = workflow_reuse_min_score()
        workflow_memory["attempted"] = bool(settings.enable_semantic_cache)
        workflow_memory["task_type"] = build_workflow_memory_task_type(
            workflow_metadata["workflow_name"],
            workflow_metadata["offer_type"],
            workflow_metadata["stage"],
        )
        recalled_output, recalled_envelope = unpack_workflow_memory_envelope(
            await semantic_cache.get(
                tenant_id=tenant_id,
                task_type=workflow_memory["task_type"],
                input_text=build_workflow_memory_input_text(
                    _convert_workflow_input_text(request, config),
                    workflow_context,
                ),
            )
        )
        score, counts = workflow_outcome_stats(db, tenant_id, workflow_memory["task_type"])
        workflow_memory["score"] = score
        workflow_memory["counts"] = counts
        workflow_memory["reuse_threshold"] = reuse_threshold
        if recalled_output is None:
            workflow_memory["status"] = "fallback"
            workflow_memory["reason"] = "not_found"
        else:
            is_valid, reason = _validate_recalled_convert_payload(recalled_output, recalled_envelope, workflow_metadata)
            if is_valid and sum(counts.values()) > 0 and score < reuse_threshold:
                workflow_memory["status"] = "fallback"
                workflow_memory["reason"] = "low_quality_score"
            else:
                workflow_memory["status"] = "hit" if is_valid else "fallback"
                workflow_memory["reason"] = reason
        if recalled_output is not None and workflow_memory["status"] == "hit":
            output = recalled_output
            cache_hit = True
            workflow_memory["estimated_time_saved_ms"] = WORKFLOW_MEMORY_TIME_SAVED_MS.get(request.module, 0)
        if workflow_memory["attempted"]:
            _log_automation(
                db,
                tenant_id,
                {
                    "action": "workflow_memory.recall",
                    "status": str(workflow_memory["status"]),
                    "reason": workflow_memory["reason"],
                    "payload": workflow_memory,
                },
            )

    if output is None:
        output = _build_module_output(request)
        if request.module == "convert":
            workflow_metadata = _convert_workflow_metadata(request, config)
            workflow_context = _convert_workflow_context(request, config)
            if settings.enable_semantic_cache:
                try:
                    await semantic_cache.set(
                        tenant_id=tenant_id,
                        task_type=build_workflow_memory_task_type(
                            workflow_metadata["workflow_name"],
                            workflow_metadata["offer_type"],
                            workflow_metadata["stage"],
                        ),
                        input_text=build_workflow_memory_input_text(
                            _convert_workflow_input_text(request, config),
                            workflow_context,
                        ),
                        output=build_workflow_memory_envelope(
                            workflow_type=workflow_metadata["workflow_name"],
                            offer_type=workflow_metadata["offer_type"],
                            stage=workflow_metadata["stage"],
                            output=output,
                            context=workflow_context,
                            metadata=workflow_metadata,
                        ),
                    )
                    workflow_memory["stored"] = True
                except Exception:
                    pass
            if workflow_memory["attempted"]:
                _log_automation(
                    db,
                    tenant_id,
                    {
                        "action": "workflow_memory.store",
                        "status": "stored" if workflow_memory["stored"] else "skipped",
                        "reason": workflow_memory["reason"],
                        "payload": {
                            **workflow_memory,
                            "workflow_name": workflow_metadata["workflow_name"],
                            "offer_type": workflow_metadata["offer_type"],
                            "stage": workflow_metadata["stage"],
                        },
                    },
                )
        if client:
            try:
                import json

                client.setex(cache_key, config["ttl_seconds"], json.dumps(output))
            except Exception:
                pass

    if request.module == "convert":
        workflow_metadata = _convert_workflow_metadata(request, config)
        decision = "reuse" if workflow_memory.get("status") == "hit" else "regenerate"
        log_workflow_memory_decision(
            db,
            tenant_id=tenant_id,
            request_id=request_id,
            workflow_type=workflow_metadata["workflow_name"],
            offer_type=workflow_metadata["offer_type"],
            offer_version=workflow_metadata["offer_version"],
            stage=workflow_metadata["stage"],
            audience=workflow_metadata["audience"],
            prompt_key=workflow_metadata["prompt_key"],
            prompt_schema_version=workflow_metadata["prompt_schema_version"],
            workflow_memory_schema_version=workflow_metadata["workflow_memory_schema_version"],
            task_type=str(workflow_memory.get("task_type") or build_workflow_memory_task_type(
                workflow_metadata["workflow_name"],
                workflow_metadata["offer_type"],
                workflow_metadata["stage"],
            )),
            cache_attempted=bool(workflow_memory.get("attempted")),
            recalled_score=workflow_memory.get("score"),
            reuse_threshold=workflow_memory.get("reuse_threshold"),
            decision=decision,
            fallback_reason=workflow_memory.get("reason") if decision == "regenerate" else None,
            stored=bool(workflow_memory.get("stored")),
            estimated_time_saved_ms=int(workflow_memory.get("estimated_time_saved_ms") or 0),
            metadata={
                "decision_summary": _workflow_memory_decision_summary(workflow_memory, cache_hit),
                "reason_path": _workflow_memory_reason_path(workflow_memory, cache_hit),
                "validation_reason": workflow_memory.get("reason"),
                "quality_gate_applied": bool(sum((workflow_memory.get("counts") or {}).values()) > 0),
                "quality_gate_triggered": workflow_memory.get("reason") == "low_quality_score",
                "counts": workflow_memory.get("counts", {}),
                "context": workflow_context if 'workflow_context' in locals() else {},
                "module": request.module,
                "cache_hit": cache_hit,
                "decision_output_source": decision,
            },
        )

    automation_results: list[dict[str, Any]] = []
    if request.module == "convert" and request.auto_execute:
        email_payload = output.get("execution", {}).get("email", {})
        leads = _load_leads(request.automation)
        max_leads = int(request.automation.get("max_leads", 5))
        product = output.get("product", FULLSTACK_PRODUCTS["solo"])

        if leads:
            for lead in leads[:max_leads]:
                result = _send_email(_personalize_email(email_payload, lead, product))
                _log_automation(db, tenant_id, result)
                automation_results.append(result)
        else:
            result = _send_email(email_payload)
            _log_automation(db, tenant_id, result)
            automation_results.append(result)

    _log_usage(db, tenant_id, request.module, config["model"], 0.0)

    return AiResponse(
        request_id=request_id,
        tenant_id=tenant_id,
        module=request.module,
        prompt_key=str(config["prompt_key"]),
        model=str(config["model"]),
        cache_hit=cache_hit,
        output=output,
        automation=automation_results,
        usage={
            "latency_ms": int((time.monotonic() - start) * 1000),
            "cost_usd": 0.0,
            "workflow_memory": workflow_memory,
        },
    )
