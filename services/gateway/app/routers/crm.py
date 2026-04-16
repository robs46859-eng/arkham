"""Tenant-scoped CRM endpoints available to all models through the gateway."""

from __future__ import annotations

import smtplib
import uuid
from datetime import datetime
from email.message import EmailMessage
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import Header

from packages.db import get_db
from packages.models import (
    AutomationLogRecord,
    CRMActivityRecord,
    CompanyRecord,
    ContactRecord,
    DealRecord,
    LeadRecord,
    Tenant,
    TenantActorRoleRecord,
    WorkflowMemoryDecisionRecord,
    WorkflowExecutionDeliveryRecord,
    WorkflowExecutionRecord,
    WorkflowReviewQueueRecord,
)
from packages.models.base import Base
from packages.schemas.crm import (
    ActivityCreate,
    ActivityResponse,
    CRMContextResponse,
    CompanyCreate,
    CompanyResponse,
    CompanyUpdate,
    ContactCreate,
    ContactResponse,
    ContactUpdate,
    DealCreate,
    DealResponse,
    DealUpdate,
    LeadCreate,
    LeadResponse,
    LeadUpdate,
    WorkflowMemoryRecallRequest,
    WorkflowMemoryConfigResponse,
    WorkflowMemoryConfigUpdate,
    WorkflowMemoryDecisionResponse,
    WorkflowMemoryMetricsResponse,
    WorkflowMemoryResponse,
    WorkflowMemoryStoreRequest,
    WorkflowOutcomeLogRequest,
    WorkflowOutcomeResponse,
    WorkflowReviewQueueImportRequest,
    WorkflowReviewQueueResponse,
    WorkflowReviewQueueUpdate,
    WorkflowExecutionCreate,
    WorkflowExecutionDeliveryCreate,
    WorkflowExecutionDeliveryResponse,
    WorkflowExecutionResponse,
)
from ..middleware.admin_auth import require_admin
from ..middleware.auth import require_tenant
from ..authz import (
    WORKFLOW_DELIVER,
    WORKFLOW_EXECUTE,
    WORKFLOW_REVIEW,
    WORKFLOW_VIEW,
    ensure_actor_role_table,
    require_actor_permission,
)
from ..providers.cache import semantic_cache
from ..settings import settings

router = APIRouter(prefix="/v1/crm", tags=["crm"])

_CRM_SCHEMA_READY = False
WORKFLOW_MEMORY_SCHEMA_VERSION = "crm-workflow-memory.v1"
DEFAULT_WORKFLOW_OUTCOME_WEIGHTS = {
    "send_approval": 1.0,
    "delivered": 2.0,
    "reply": 5.0,
    "booking": 8.0,
    "rejection": -4.0,
}
DEFAULT_WORKFLOW_REUSE_MIN_SCORE = -0.5
AUTO_REUSE_MIN_SCORE_FLOOR = 0.0
_workflow_outcome_weights = dict(DEFAULT_WORKFLOW_OUTCOME_WEIGHTS)
_workflow_reuse_min_score = DEFAULT_WORKFLOW_REUSE_MIN_SCORE


def _ensure_crm_tables(db: Any) -> None:
    global _CRM_SCHEMA_READY
    if _CRM_SCHEMA_READY:
        return
    bind = getattr(db, "bind", None)
    if bind is None:
        return
    Base.metadata.create_all(
        bind=bind,
        tables=[
            TenantActorRoleRecord.__table__,
            CompanyRecord.__table__,
            ContactRecord.__table__,
            LeadRecord.__table__,
            DealRecord.__table__,
            CRMActivityRecord.__table__,
            WorkflowMemoryDecisionRecord.__table__,
            WorkflowReviewQueueRecord.__table__,
            WorkflowExecutionRecord.__table__,
            WorkflowExecutionDeliveryRecord.__table__,
        ],
    )
    _CRM_SCHEMA_READY = True


def _tenant_exists(db: Any, tenant_id: str) -> bool:
    if hasattr(db, "get"):
        tenant = db.get(Tenant, tenant_id)
        return isinstance(tenant, Tenant)
    if hasattr(db, "query"):
        tenant = db.query(Tenant).filter_by(id=tenant_id).first()
        return isinstance(tenant, Tenant)
    return False


def _get_record(db: Any, model: type[Any], record_id: str, tenant_id: str) -> Any | None:
    if hasattr(db, "get"):
        record = db.get(model, record_id)
        if record is not None and getattr(record, "tenant_id", tenant_id) == tenant_id:
            return record
    if hasattr(db, "query"):
        return db.query(model).filter_by(id=record_id, tenant_id=tenant_id).first()
    return None


def _list_records(db: Any, model: type[Any], tenant_id: str) -> list[Any]:
    if hasattr(db, "_objects"):
        return [
            record
            for record in db._objects.values()
            if isinstance(record, model) and getattr(record, "tenant_id", None) == tenant_id
        ]
    if hasattr(db, "query"):
        return list(db.query(model).filter_by(tenant_id=tenant_id).all())
    raise HTTPException(status_code=500, detail="Database session does not support record listing.")


def _search_records(records: list[Any], query: str | None) -> list[Any]:
    if not query:
        return records
    needle = query.strip().lower()
    if not needle:
        return records
    matched: list[Any] = []
    for record in records:
        haystack = " ".join(str(value) for value in vars(record).values() if value is not None).lower()
        if needle in haystack:
            matched.append(record)
    return matched


def _sort_recent(records: list[Any]) -> list[Any]:
    return sorted(records, key=lambda record: getattr(record, "updated_at", getattr(record, "created_at", datetime.min)), reverse=True)


def _company_response(record: CompanyRecord) -> CompanyResponse:
    return CompanyResponse(
        company_id=record.id,
        tenant_id=record.tenant_id,
        name=record.name,
        website=record.website,
        industry=record.industry,
        notes=record.notes or {},
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _contact_response(record: ContactRecord) -> ContactResponse:
    return ContactResponse(
        contact_id=record.id,
        tenant_id=record.tenant_id,
        company_id=record.company_id,
        first_name=record.first_name,
        last_name=record.last_name,
        email=record.email,
        title=record.title,
        phone=record.phone,
        linkedin_url=record.linkedin_url,
        status=record.status,
        notes=record.notes or {},
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _lead_response(record: LeadRecord) -> LeadResponse:
    return LeadResponse(
        lead_id=record.id,
        tenant_id=record.tenant_id,
        company_id=record.company_id,
        contact_id=record.contact_id,
        source=record.source,
        status=record.status,
        fit_score=record.fit_score,
        notes=record.notes,
        metadata=record.record_metadata or {},
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _deal_response(record: DealRecord) -> DealResponse:
    return DealResponse(
        deal_id=record.id,
        tenant_id=record.tenant_id,
        company_id=record.company_id,
        contact_id=record.contact_id,
        name=record.name,
        stage=record.stage,
        status=record.status,
        amount_cents=record.amount_cents,
        currency=record.currency,
        notes=record.notes,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _activity_response(record: CRMActivityRecord) -> ActivityResponse:
    return ActivityResponse(
        activity_id=record.id,
        tenant_id=record.tenant_id,
        lead_id=record.lead_id,
        deal_id=record.deal_id,
        contact_id=record.contact_id,
        activity_type=record.activity_type,
        subject=record.subject,
        body=record.body,
        metadata=record.record_metadata or {},
        created_at=record.created_at,
    )


def _decision_response(record: WorkflowMemoryDecisionRecord) -> WorkflowMemoryDecisionResponse:
    return WorkflowMemoryDecisionResponse(
        decision_id=record.id,
        tenant_id=record.tenant_id,
        request_id=record.request_id,
        workflow_type=record.workflow_type,
        offer_type=record.offer_type,
        offer_version=record.offer_version,
        stage=record.stage,
        audience=record.audience,
        prompt_key=record.prompt_key,
        prompt_schema_version=record.prompt_schema_version,
        workflow_memory_schema_version=record.workflow_memory_schema_version,
        task_type=record.task_type,
        cache_attempted=record.cache_attempted,
        recalled_score=record.recalled_score,
        reuse_threshold=record.reuse_threshold,
        decision=record.decision,
        fallback_reason=record.fallback_reason,
        stored=record.stored,
        estimated_time_saved_ms=record.estimated_time_saved_ms,
        metadata=record.decision_metadata or {},
        created_at=record.created_at,
    )


def _review_queue_response(record: WorkflowReviewQueueRecord) -> WorkflowReviewQueueResponse:
    return WorkflowReviewQueueResponse(
        review_item_id=record.id,
        tenant_id=record.tenant_id,
        batch_label=record.batch_label,
        source_artifact=record.source_artifact,
        request_id=record.request_id,
        case_name=record.case_name,
        lead_name=record.lead_name,
        company_name=record.company_name,
        contact_email=record.contact_email,
        eligibility_status=record.eligibility_status,
        system_decision=record.system_decision,
        system_reason=record.system_reason,
        review_status=record.review_status,
        reviewer_name=record.reviewer_name,
        reviewer_notes=record.reviewer_notes,
        metadata=record.review_metadata or {},
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _execution_response(record: WorkflowExecutionRecord) -> WorkflowExecutionResponse:
    return WorkflowExecutionResponse(
        execution_id=record.id,
        tenant_id=record.tenant_id,
        review_item_id=record.review_item_id,
        request_id=record.request_id,
        batch_label=record.batch_label,
        workflow_type=record.workflow_type,
        offer_type=record.offer_type,
        stage=record.stage,
        execution_status=record.execution_status,
        metadata=record.execution_metadata or {},
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _execution_delivery_response(record: WorkflowExecutionDeliveryRecord) -> WorkflowExecutionDeliveryResponse:
    return WorkflowExecutionDeliveryResponse(
        delivery_id=record.id,
        tenant_id=record.tenant_id,
        execution_id=record.execution_id,
        review_item_id=record.review_item_id,
        channel=record.channel,
        provider=record.provider,
        delivery_status=record.delivery_status,
        metadata=record.delivery_metadata or {},
        created_at=record.created_at,
    )


def _send_execution_email(email_payload: dict[str, Any], provider_mode: str) -> dict[str, Any]:
    to_address = email_payload.get("to")
    if not to_address:
        return {"status": "skipped", "reason": "missing_recipient", "payload": email_payload}
    if provider_mode == "dry_run" or settings.automation_dry_run:
        return {"status": "dry_run", "payload": email_payload}
    if not all([settings.smtp_host, settings.smtp_username, settings.smtp_password, settings.email_from]):
        return {"status": "blocked_missing_smtp_config", "payload": email_payload}

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

    return {"status": "sent", "to": to_address}


def _require_tenant_record(db: Any, tenant_id: str) -> None:
    _ensure_crm_tables(db)
    if not _tenant_exists(db, tenant_id):
        raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")


def _flow_task_type(workflow_type: str, offer_type: str | None, stage: str | None) -> str:
    offer = (offer_type or "general").strip().lower().replace(" ", "_")
    current_stage = (stage or "any").strip().lower().replace(" ", "_")
    flow = workflow_type.strip().lower().replace(" ", "_")
    return f"crm_flow:{flow}:{offer}:{current_stage}"


def _flow_input_text(input_text: str, context: dict[str, Any]) -> str:
    parts = [input_text.strip()]
    if context:
        parts.append(f"context={context!r}")
    return "\n".join(part for part in parts if part)


def _cache_available() -> bool:
    return bool(settings.enable_semantic_cache)


def workflow_outcome_weights() -> dict[str, float]:
    return dict(_workflow_outcome_weights)


def workflow_reuse_min_score() -> float:
    return max(_workflow_reuse_min_score, AUTO_REUSE_MIN_SCORE_FLOOR)


def update_workflow_memory_config(
    *,
    reuse_min_score: float | None = None,
    outcome_weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    global _workflow_reuse_min_score
    if reuse_min_score is not None:
        _workflow_reuse_min_score = float(reuse_min_score)
    if outcome_weights is not None:
        normalized: dict[str, float] = {}
        for key, value in outcome_weights.items():
            normalized[str(key).strip().lower()] = float(value)
        for required in DEFAULT_WORKFLOW_OUTCOME_WEIGHTS:
            if required not in normalized:
                normalized[required] = _workflow_outcome_weights.get(
                    required, DEFAULT_WORKFLOW_OUTCOME_WEIGHTS[required]
                )
        _workflow_outcome_weights.clear()
        _workflow_outcome_weights.update(normalized)
    return {
        "configured_reuse_min_score": _workflow_reuse_min_score,
        "effective_reuse_min_score": workflow_reuse_min_score(),
        "auto_reuse_score_floor": AUTO_REUSE_MIN_SCORE_FLOOR,
        "outcome_weights": workflow_outcome_weights(),
    }


def workflow_outcome_stats(db: Any, tenant_id: str, task_type: str) -> tuple[float, dict[str, int]]:
    weights = workflow_outcome_weights()
    counts = {key: 0 for key in weights}
    total_score = 0.0
    total_events = 0
    for record in _list_records(db, CRMActivityRecord, tenant_id):
        if getattr(record, "activity_type", "") != "workflow_outcome":
            continue
        metadata = getattr(record, "record_metadata", {}) or {}
        if metadata.get("task_type") != task_type:
            continue
        outcome = str(metadata.get("outcome", "")).strip().lower()
        if outcome not in weights:
            continue
        counts[outcome] += 1
        total_score += weights[outcome]
        total_events += 1
    score = total_score / total_events if total_events else 0.0
    return score, counts


def workflow_memory_metrics(
    db: Any,
    tenant_id: str,
    workflow_type: str | None = None,
    offer_type: str | None = None,
    stage: str | None = None,
) -> WorkflowMemoryMetricsResponse:
    expected_task_type = _flow_task_type(workflow_type, offer_type, stage) if workflow_type else None
    recall_attempts = 0
    recall_hits = 0
    fallback_reasons: dict[str, int] = {}
    total_estimated_time_saved_ms = 0

    for record in _list_records(db, AutomationLogRecord, tenant_id):
        if getattr(record, "action", "") != "workflow_memory.recall":
            continue
        payload = getattr(record, "payload", {}) or {}
        payload_body = payload.get("payload", {}) if isinstance(payload.get("payload"), dict) else payload
        task_type = payload_body.get("task_type")
        if expected_task_type and task_type != expected_task_type:
            continue
        recall_attempts += 1
        status = str(getattr(record, "status", "") or payload.get("status", ""))
        if status == "hit":
            recall_hits += 1
        else:
            reason = str(payload.get("reason") or payload_body.get("reason") or "unknown")
            fallback_reasons[reason] = fallback_reasons.get(reason, 0) + 1
        total_estimated_time_saved_ms += int(payload_body.get("estimated_time_saved_ms") or 0)

    outcome_counts = {key: 0 for key in workflow_outcome_weights()}
    total_score = 0.0
    total_outcomes = 0
    current_weights = workflow_outcome_weights()
    for record in _list_records(db, CRMActivityRecord, tenant_id):
        if getattr(record, "activity_type", "") != "workflow_outcome":
            continue
        metadata = getattr(record, "record_metadata", {}) or {}
        if workflow_type and metadata.get("workflow_type") != workflow_type:
            continue
        if offer_type is not None and metadata.get("offer_type") != offer_type:
            continue
        if stage is not None and metadata.get("stage") != stage:
            continue
        outcome = str(metadata.get("outcome", "")).strip().lower()
        if outcome not in outcome_counts:
            continue
        outcome_counts[outcome] += 1
        total_score += current_weights[outcome]
        total_outcomes += 1

    fallback_count = recall_attempts - recall_hits
    hit_rate = (recall_hits / recall_attempts) if recall_attempts else 0.0
    fallback_rate = (fallback_count / recall_attempts) if recall_attempts else 0.0
    version_mismatch_events = sum(count for reason, count in fallback_reasons.items() if "version" in reason)
    version_mismatch_rate = (version_mismatch_events / recall_attempts) if recall_attempts else 0.0
    average_estimated_time_saved_ms = (total_estimated_time_saved_ms / recall_hits) if recall_hits else 0.0
    outcome_score = (total_score / total_outcomes) if total_outcomes else 0.0

    return WorkflowMemoryMetricsResponse(
        tenant_id=tenant_id,
        workflow_type=workflow_type,
        offer_type=offer_type,
        stage=stage,
        recall_attempts=recall_attempts,
        recall_hits=recall_hits,
        fallback_count=fallback_count,
        fallback_reasons=fallback_reasons,
        hit_rate=hit_rate,
        fallback_rate=fallback_rate,
        version_mismatch_rate=version_mismatch_rate,
        total_estimated_time_saved_ms=total_estimated_time_saved_ms,
        average_estimated_time_saved_ms=average_estimated_time_saved_ms,
        outcome_counts=outcome_counts,
        outcome_score=outcome_score,
    )


def _workflow_memory_config_response() -> WorkflowMemoryConfigResponse:
    return WorkflowMemoryConfigResponse(
        configured_reuse_min_score=_workflow_reuse_min_score,
        effective_reuse_min_score=workflow_reuse_min_score(),
        auto_reuse_score_floor=AUTO_REUSE_MIN_SCORE_FLOOR,
        outcome_weights=workflow_outcome_weights(),
    )


def log_workflow_memory_decision(
    db: Any,
    *,
    tenant_id: str,
    request_id: str,
    workflow_type: str,
    offer_type: str | None,
    offer_version: str | None,
    stage: str | None,
    audience: str | None,
    prompt_key: str | None,
    prompt_schema_version: str | None,
    workflow_memory_schema_version: str | None,
    task_type: str,
    cache_attempted: bool,
    recalled_score: float | None,
    reuse_threshold: float | None,
    decision: str,
    fallback_reason: str | None,
    stored: bool,
    estimated_time_saved_ms: int,
    metadata: dict[str, Any] | None = None,
) -> WorkflowMemoryDecisionRecord:
    record = WorkflowMemoryDecisionRecord(
        id=f"wmd_{uuid.uuid4().hex}",
        tenant_id=tenant_id,
        request_id=request_id,
        workflow_type=workflow_type,
        offer_type=offer_type,
        offer_version=offer_version,
        stage=stage,
        audience=audience,
        prompt_key=prompt_key,
        prompt_schema_version=prompt_schema_version,
        workflow_memory_schema_version=workflow_memory_schema_version,
        task_type=task_type,
        cache_attempted=cache_attempted,
        recalled_score=recalled_score,
        reuse_threshold=reuse_threshold,
        decision=decision,
        fallback_reason=fallback_reason,
        stored=stored,
        estimated_time_saved_ms=estimated_time_saved_ms,
        decision_metadata=metadata or {},
        created_at=datetime.utcnow(),
    )
    db.add(record)
    if hasattr(db, "commit"):
        db.commit()
    return record


def build_workflow_memory_task_type(workflow_type: str, offer_type: str | None, stage: str | None) -> str:
    return _flow_task_type(workflow_type, offer_type, stage)


def build_workflow_memory_input_text(input_text: str, context: dict[str, Any]) -> str:
    return _flow_input_text(input_text, context)


def build_workflow_memory_envelope(
    *,
    workflow_type: str,
    offer_type: str | None,
    stage: str | None,
    output: dict[str, Any],
    context: dict[str, Any],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    return {
        "payload": output,
        "_workflow_memory": {
            "schema_version": WORKFLOW_MEMORY_SCHEMA_VERSION,
            "workflow_type": workflow_type,
            "offer_type": offer_type,
            "stage": stage,
            "context": context,
            "metadata": metadata,
        },
    }


def unpack_workflow_memory_envelope(output: dict[str, Any] | None) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    if not isinstance(output, dict):
        return None, {}
    workflow_memory = output.get("_workflow_memory")
    payload = output.get("payload")
    if isinstance(workflow_memory, dict) and isinstance(payload, dict):
        return payload, workflow_memory
    return output, {}


@router.get("/context", response_model=CRMContextResponse)
def crm_context(
    q: str | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=100),
    auth: tuple[str, str] = Depends(require_tenant),
    db: object = Depends(get_db),
) -> CRMContextResponse:
    tenant_id, _project_id = auth
    _require_tenant_record(db, tenant_id)

    companies = _sort_recent(_search_records(_list_records(db, CompanyRecord, tenant_id), q))[:limit]
    contacts = _sort_recent(_search_records(_list_records(db, ContactRecord, tenant_id), q))[:limit]
    leads = _sort_recent(_search_records(_list_records(db, LeadRecord, tenant_id), q))[:limit]
    deals = _sort_recent(_search_records(_list_records(db, DealRecord, tenant_id), q))[:limit]
    activities = _sort_recent(_search_records(_list_records(db, CRMActivityRecord, tenant_id), q))[:limit]

    return CRMContextResponse(
        tenant_id=tenant_id,
        query=q,
        totals={
            "companies": len(_list_records(db, CompanyRecord, tenant_id)),
            "contacts": len(_list_records(db, ContactRecord, tenant_id)),
            "leads": len(_list_records(db, LeadRecord, tenant_id)),
            "deals": len(_list_records(db, DealRecord, tenant_id)),
            "activities": len(_list_records(db, CRMActivityRecord, tenant_id)),
        },
        companies=[_company_response(record) for record in companies],
        contacts=[_contact_response(record) for record in contacts],
        leads=[_lead_response(record) for record in leads],
        deals=[_deal_response(record) for record in deals],
        activities=[_activity_response(record) for record in activities],
    )


@router.get("/companies", response_model=list[CompanyResponse])
def list_companies(
    q: str | None = Query(default=None),
    auth: tuple[str, str] = Depends(require_tenant),
    db: object = Depends(get_db),
) -> list[CompanyResponse]:
    tenant_id, _project_id = auth
    _require_tenant_record(db, tenant_id)
    records = _sort_recent(_search_records(_list_records(db, CompanyRecord, tenant_id), q))
    return [_company_response(record) for record in records]


@router.post("/companies", response_model=CompanyResponse)
def create_company(
    request: CompanyCreate,
    auth: tuple[str, str] = Depends(require_tenant),
    db: object = Depends(get_db),
) -> CompanyResponse:
    tenant_id, _project_id = auth
    _require_tenant_record(db, tenant_id)
    now = datetime.utcnow()
    record = CompanyRecord(
        id=f"cmp_{uuid.uuid4().hex}",
        tenant_id=tenant_id,
        name=request.name.strip(),
        website=request.website,
        industry=request.industry,
        notes=request.notes,
        created_at=now,
        updated_at=now,
    )
    db.add(record)
    if hasattr(db, "commit"):
        db.commit()
    return _company_response(record)


@router.patch("/companies/{company_id}", response_model=CompanyResponse)
def update_company(
    company_id: str,
    request: CompanyUpdate,
    auth: tuple[str, str] = Depends(require_tenant),
    db: object = Depends(get_db),
) -> CompanyResponse:
    tenant_id, _project_id = auth
    _require_tenant_record(db, tenant_id)
    record = _get_record(db, CompanyRecord, company_id, tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Company {company_id} not found")
    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    record.updated_at = datetime.utcnow()
    if hasattr(db, "commit"):
        db.commit()
    return _company_response(record)


@router.get("/contacts", response_model=list[ContactResponse])
def list_contacts(
    q: str | None = Query(default=None),
    auth: tuple[str, str] = Depends(require_tenant),
    db: object = Depends(get_db),
) -> list[ContactResponse]:
    tenant_id, _project_id = auth
    _require_tenant_record(db, tenant_id)
    records = _sort_recent(_search_records(_list_records(db, ContactRecord, tenant_id), q))
    return [_contact_response(record) for record in records]


@router.post("/contacts", response_model=ContactResponse)
def create_contact(
    request: ContactCreate,
    auth: tuple[str, str] = Depends(require_tenant),
    db: object = Depends(get_db),
) -> ContactResponse:
    tenant_id, _project_id = auth
    _require_tenant_record(db, tenant_id)
    now = datetime.utcnow()
    record = ContactRecord(
        id=f"ctc_{uuid.uuid4().hex}",
        tenant_id=tenant_id,
        company_id=request.company_id,
        first_name=request.first_name,
        last_name=request.last_name,
        email=request.email,
        title=request.title,
        phone=request.phone,
        linkedin_url=request.linkedin_url,
        status=request.status,
        notes=request.notes,
        created_at=now,
        updated_at=now,
    )
    db.add(record)
    if hasattr(db, "commit"):
        db.commit()
    return _contact_response(record)


@router.patch("/contacts/{contact_id}", response_model=ContactResponse)
def update_contact(
    contact_id: str,
    request: ContactUpdate,
    auth: tuple[str, str] = Depends(require_tenant),
    db: object = Depends(get_db),
) -> ContactResponse:
    tenant_id, _project_id = auth
    _require_tenant_record(db, tenant_id)
    record = _get_record(db, ContactRecord, contact_id, tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Contact {contact_id} not found")
    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    record.updated_at = datetime.utcnow()
    if hasattr(db, "commit"):
        db.commit()
    return _contact_response(record)


@router.get("/leads", response_model=list[LeadResponse])
def list_leads(
    q: str | None = Query(default=None),
    auth: tuple[str, str] = Depends(require_tenant),
    db: object = Depends(get_db),
) -> list[LeadResponse]:
    tenant_id, _project_id = auth
    _require_tenant_record(db, tenant_id)
    records = _sort_recent(_search_records(_list_records(db, LeadRecord, tenant_id), q))
    return [_lead_response(record) for record in records]


@router.post("/leads", response_model=LeadResponse)
def create_lead(
    request: LeadCreate,
    auth: tuple[str, str] = Depends(require_tenant),
    db: object = Depends(get_db),
) -> LeadResponse:
    tenant_id, _project_id = auth
    _require_tenant_record(db, tenant_id)
    now = datetime.utcnow()
    record = LeadRecord(
        id=f"lead_{uuid.uuid4().hex}",
        tenant_id=tenant_id,
        company_id=request.company_id,
        contact_id=request.contact_id,
        source=request.source,
        status=request.status,
        fit_score=request.fit_score,
        notes=request.notes,
        record_metadata=request.metadata,
        created_at=now,
        updated_at=now,
    )
    db.add(record)
    if hasattr(db, "commit"):
        db.commit()
    return _lead_response(record)


@router.patch("/leads/{lead_id}", response_model=LeadResponse)
def update_lead(
    lead_id: str,
    request: LeadUpdate,
    auth: tuple[str, str] = Depends(require_tenant),
    db: object = Depends(get_db),
) -> LeadResponse:
    tenant_id, _project_id = auth
    _require_tenant_record(db, tenant_id)
    record = _get_record(db, LeadRecord, lead_id, tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Lead {lead_id} not found")
    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    record.updated_at = datetime.utcnow()
    if hasattr(db, "commit"):
        db.commit()
    return _lead_response(record)


@router.get("/deals", response_model=list[DealResponse])
def list_deals(
    q: str | None = Query(default=None),
    auth: tuple[str, str] = Depends(require_tenant),
    db: object = Depends(get_db),
) -> list[DealResponse]:
    tenant_id, _project_id = auth
    _require_tenant_record(db, tenant_id)
    records = _sort_recent(_search_records(_list_records(db, DealRecord, tenant_id), q))
    return [_deal_response(record) for record in records]


@router.post("/deals", response_model=DealResponse)
def create_deal(
    request: DealCreate,
    auth: tuple[str, str] = Depends(require_tenant),
    db: object = Depends(get_db),
) -> DealResponse:
    tenant_id, _project_id = auth
    _require_tenant_record(db, tenant_id)
    now = datetime.utcnow()
    record = DealRecord(
        id=f"deal_{uuid.uuid4().hex}",
        tenant_id=tenant_id,
        company_id=request.company_id,
        contact_id=request.contact_id,
        name=request.name,
        stage=request.stage,
        status=request.status,
        amount_cents=request.amount_cents,
        currency=request.currency,
        notes=request.notes,
        created_at=now,
        updated_at=now,
    )
    db.add(record)
    if hasattr(db, "commit"):
        db.commit()
    return _deal_response(record)


@router.patch("/deals/{deal_id}", response_model=DealResponse)
def update_deal(
    deal_id: str,
    request: DealUpdate,
    auth: tuple[str, str] = Depends(require_tenant),
    db: object = Depends(get_db),
) -> DealResponse:
    tenant_id, _project_id = auth
    _require_tenant_record(db, tenant_id)
    record = _get_record(db, DealRecord, deal_id, tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Deal {deal_id} not found")
    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    record.updated_at = datetime.utcnow()
    if hasattr(db, "commit"):
        db.commit()
    return _deal_response(record)


@router.get("/activities", response_model=list[ActivityResponse])
def list_activities(
    q: str | None = Query(default=None),
    auth: tuple[str, str] = Depends(require_tenant),
    db: object = Depends(get_db),
) -> list[ActivityResponse]:
    tenant_id, _project_id = auth
    _require_tenant_record(db, tenant_id)
    records = _sort_recent(_search_records(_list_records(db, CRMActivityRecord, tenant_id), q))
    return [_activity_response(record) for record in records]


@router.post("/activities", response_model=ActivityResponse)
def create_activity(
    request: ActivityCreate,
    auth: tuple[str, str] = Depends(require_tenant),
    db: object = Depends(get_db),
) -> ActivityResponse:
    tenant_id, _project_id = auth
    _require_tenant_record(db, tenant_id)
    record = CRMActivityRecord(
        id=f"act_{uuid.uuid4().hex}",
        tenant_id=tenant_id,
        lead_id=request.lead_id,
        deal_id=request.deal_id,
        contact_id=request.contact_id,
        activity_type=request.activity_type,
        subject=request.subject,
        body=request.body,
        record_metadata=request.metadata,
        created_at=datetime.utcnow(),
    )
    db.add(record)
    if hasattr(db, "commit"):
        db.commit()
    return _activity_response(record)


@router.post("/workflow-memory/store", response_model=WorkflowMemoryResponse)
async def store_workflow_memory(
    request: WorkflowMemoryStoreRequest,
    auth: tuple[str, str] = Depends(require_tenant),
    db: object = Depends(get_db),
) -> WorkflowMemoryResponse:
    tenant_id, _project_id = auth
    _require_tenant_record(db, tenant_id)

    task_type = _flow_task_type(request.workflow_type, request.offer_type, request.stage)
    cache_enabled = _cache_available()
    flow_input = _flow_input_text(request.input_text, request.context)

    if cache_enabled:
        await semantic_cache.set(
            tenant_id=tenant_id,
            task_type=task_type,
            input_text=flow_input,
            output=build_workflow_memory_envelope(
                workflow_type=request.workflow_type,
                offer_type=request.offer_type,
                stage=request.stage,
                output=request.output,
                context=request.context,
                metadata=request.metadata,
            ),
        )

    activity = CRMActivityRecord(
        id=f"act_{uuid.uuid4().hex}",
        tenant_id=tenant_id,
        lead_id=None,
        deal_id=None,
        contact_id=None,
        activity_type="workflow_memory_saved",
        subject=f"Saved reusable flow: {request.workflow_type}",
        body=request.input_text[:500],
        metadata={
            "workflow_type": request.workflow_type,
            "offer_type": request.offer_type,
            "stage": request.stage,
            "task_type": task_type,
            "cache_enabled": cache_enabled,
            **request.metadata,
        },
        created_at=datetime.utcnow(),
    )
    db.add(activity)
    if hasattr(db, "commit"):
        db.commit()

    return WorkflowMemoryResponse(
        tenant_id=tenant_id,
        workflow_type=request.workflow_type,
        offer_type=request.offer_type,
        stage=request.stage,
        task_type=task_type,
        cache_enabled=cache_enabled,
        stored=cache_enabled,
        output=request.output,
        metadata={"activity_id": activity.id},
    )


@router.post("/workflow-memory/recall", response_model=WorkflowMemoryResponse)
async def recall_workflow_memory(
    request: WorkflowMemoryRecallRequest,
    auth: tuple[str, str] = Depends(require_tenant),
    db: object = Depends(get_db),
) -> WorkflowMemoryResponse:
    tenant_id, _project_id = auth
    _require_tenant_record(db, tenant_id)

    task_type = _flow_task_type(request.workflow_type, request.offer_type, request.stage)
    cache_enabled = _cache_available()
    output: dict[str, Any] | None = None
    cache_hit = False

    if cache_enabled:
        cached = await semantic_cache.get(
            tenant_id=tenant_id,
            task_type=task_type,
            input_text=_flow_input_text(request.input_text, request.context),
            threshold=request.threshold,
        )
        output, workflow_memory = unpack_workflow_memory_envelope(cached)
        cache_hit = output is not None
    else:
        workflow_memory = {}

    score, counts = workflow_outcome_stats(db, tenant_id, task_type)

    if cache_hit:
        if score < workflow_reuse_min_score() and sum(counts.values()) > 0:
            cache_hit = False
            output = None
            workflow_memory = {}
            metadata = {
                "score": score,
                "counts": counts,
                "quality_gate": "rejected",
            }
            return WorkflowMemoryResponse(
                tenant_id=tenant_id,
                workflow_type=request.workflow_type,
                offer_type=request.offer_type,
                stage=request.stage,
                task_type=task_type,
                cache_enabled=cache_enabled,
                cache_hit=False,
                output=None,
                metadata={**metadata, "reason": "low_quality_score"},
            )
        activity = CRMActivityRecord(
            id=f"act_{uuid.uuid4().hex}",
            tenant_id=tenant_id,
            lead_id=None,
            deal_id=None,
            contact_id=None,
            activity_type="workflow_memory_recalled",
            subject=f"Recalled reusable flow: {request.workflow_type}",
            body=request.input_text[:500],
            metadata={
                "workflow_type": request.workflow_type,
                "offer_type": request.offer_type,
                "stage": request.stage,
                "task_type": task_type,
                "threshold": request.threshold,
            },
            created_at=datetime.utcnow(),
        )
        db.add(activity)
        if hasattr(db, "commit"):
            db.commit()
        metadata = {"activity_id": activity.id, **workflow_memory, "score": score, "counts": counts}
    else:
        metadata = {"score": score, "counts": counts}

    return WorkflowMemoryResponse(
        tenant_id=tenant_id,
        workflow_type=request.workflow_type,
        offer_type=request.offer_type,
        stage=request.stage,
        task_type=task_type,
        cache_enabled=cache_enabled,
        cache_hit=cache_hit,
        output=output,
        metadata=metadata,
    )


@router.post("/workflow-memory/outcome", response_model=WorkflowOutcomeResponse)
def log_workflow_outcome(
    request: WorkflowOutcomeLogRequest,
    auth: tuple[str, str] = Depends(require_tenant),
    db: object = Depends(get_db),
) -> WorkflowOutcomeResponse:
    tenant_id, _project_id = auth
    _require_tenant_record(db, tenant_id)

    task_type = _flow_task_type(request.workflow_type, request.offer_type, request.stage)
    outcome = request.outcome.strip().lower()
    weights = workflow_outcome_weights()
    if outcome not in weights:
        raise HTTPException(status_code=400, detail=f"Unsupported workflow outcome: {request.outcome}")
    source = request.source.strip().lower()
    if source not in {"reused", "regenerated"}:
        raise HTTPException(status_code=400, detail="source must be 'reused' or 'regenerated'")

    activity = CRMActivityRecord(
        id=f"act_{uuid.uuid4().hex}",
        tenant_id=tenant_id,
        lead_id=request.lead_id,
        deal_id=request.deal_id,
        contact_id=request.contact_id,
        activity_type="workflow_outcome",
        subject=f"Workflow outcome: {request.workflow_type}",
        body=None,
        record_metadata={
            "workflow_type": request.workflow_type,
            "offer_type": request.offer_type,
            "stage": request.stage,
            "task_type": task_type,
            "outcome": outcome,
            "source": source,
            **request.metadata,
        },
        created_at=datetime.utcnow(),
    )
    db.add(activity)
    if hasattr(db, "commit"):
        db.commit()

    score, counts = workflow_outcome_stats(db, tenant_id, task_type)
    return WorkflowOutcomeResponse(
        tenant_id=tenant_id,
        workflow_type=request.workflow_type,
        offer_type=request.offer_type,
        stage=request.stage,
        task_type=task_type,
        score=score,
        counts=counts,
        last_outcome=outcome,
        source=source,
        activity_id=activity.id,
    )


@router.get("/workflow-memory/config", response_model=WorkflowMemoryConfigResponse)
def get_workflow_memory_config(_: None = Depends(require_admin)) -> WorkflowMemoryConfigResponse:
    return _workflow_memory_config_response()


@router.patch("/workflow-memory/config", response_model=WorkflowMemoryConfigResponse)
def patch_workflow_memory_config(
    request: WorkflowMemoryConfigUpdate,
    _: None = Depends(require_admin),
) -> WorkflowMemoryConfigResponse:
    update_workflow_memory_config(
        reuse_min_score=request.reuse_min_score,
        outcome_weights=request.outcome_weights,
    )
    return _workflow_memory_config_response()


@router.get("/workflow-memory/metrics/{tenant_id}", response_model=WorkflowMemoryMetricsResponse)
def get_workflow_memory_metrics(
    tenant_id: str,
    workflow_type: str | None = Query(default=None),
    offer_type: str | None = Query(default=None),
    stage: str | None = Query(default=None),
    _: None = Depends(require_admin),
    x_admin_actor: str | None = Header(default=None, alias="X-Admin-Actor"),
    db: object = Depends(get_db),
) -> WorkflowMemoryMetricsResponse:
    _ensure_crm_tables(db)
    _require_tenant_record(db, tenant_id)
    require_actor_permission(db, tenant_id, x_admin_actor, WORKFLOW_VIEW)
    return workflow_memory_metrics(
        db,
        tenant_id,
        workflow_type=workflow_type,
        offer_type=offer_type,
        stage=stage,
    )


@router.get("/workflow-memory/decisions/{tenant_id}", response_model=list[WorkflowMemoryDecisionResponse])
def list_workflow_memory_decisions(
    tenant_id: str,
    workflow_type: str | None = Query(default=None),
    offer_type: str | None = Query(default=None),
    stage: str | None = Query(default=None),
    decision: str | None = Query(default=None),
    fallback_reason: str | None = Query(default=None),
    borderline_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    _: None = Depends(require_admin),
    x_admin_actor: str | None = Header(default=None, alias="X-Admin-Actor"),
    db: object = Depends(get_db),
) -> list[WorkflowMemoryDecisionResponse]:
    _ensure_crm_tables(db)
    _require_tenant_record(db, tenant_id)
    require_actor_permission(db, tenant_id, x_admin_actor, WORKFLOW_VIEW)
    threshold = workflow_reuse_min_score()
    records = _sort_recent(_list_records(db, WorkflowMemoryDecisionRecord, tenant_id))
    filtered: list[WorkflowMemoryDecisionRecord] = []
    for record in records:
        if workflow_type and record.workflow_type != workflow_type:
            continue
        if offer_type is not None and record.offer_type != offer_type:
            continue
        if stage is not None and record.stage != stage:
            continue
        if decision and record.decision != decision:
            continue
        if fallback_reason and record.fallback_reason != fallback_reason:
            continue
        if borderline_only:
            score = record.recalled_score
            if score is None:
                continue
            if abs(score - threshold) > 0.35:
                continue
        filtered.append(record)
        if len(filtered) >= limit:
            break
    return [_decision_response(record) for record in filtered]


@router.post("/workflow-review-queue/import", response_model=list[WorkflowReviewQueueResponse])
def import_workflow_review_queue(
    request: WorkflowReviewQueueImportRequest,
    _: None = Depends(require_admin),
    x_admin_actor: str | None = Header(default=None, alias="X-Admin-Actor"),
    db: object = Depends(get_db),
) -> list[WorkflowReviewQueueResponse]:
    now = datetime.utcnow()
    _ensure_crm_tables(db)
    created: list[WorkflowReviewQueueRecord] = []
    for item in request.items:
        _require_tenant_record(db, item.tenant_id)
        ensure_actor_role_table(db)
        require_actor_permission(db, item.tenant_id, x_admin_actor, WORKFLOW_REVIEW)
        lead = item.lead or {}
        eligibility = item.eligibility or {}
        decision = item.decision or {}
        reviewer = item.reviewer or {}
        review_status = "pending" if eligibility.get("status") == "sendable" else "skipped"
        history_entry = {
            "tenant_id": item.tenant_id,
            "review_status": review_status,
            "reviewer_name": reviewer.get("reviewer_name") or x_admin_actor,
            "reviewer_notes": reviewer.get("notes"),
            "actor": reviewer.get("reviewer_name") or x_admin_actor or "system_import",
            "changed_at": now.isoformat(),
            "source": "import",
        }
        record = WorkflowReviewQueueRecord(
            id=f"wrq_{uuid.uuid4().hex}",
            tenant_id=item.tenant_id,
            batch_label=request.batch_label,
            source_artifact=request.source_artifact,
            request_id=item.request_id,
            case_name=item.case_name,
            lead_name=str(lead.get("name") or "").strip() or None,
            company_name=str(lead.get("company") or "").strip() or None,
            contact_email=str(lead.get("email") or "").strip() or None,
            eligibility_status=str(eligibility.get("status") or "unknown"),
            system_decision=str(decision.get("status") or "unknown"),
            system_reason=str(decision.get("reason") or "") or None,
            review_status=review_status,
            reviewer_name=reviewer.get("reviewer_name") or x_admin_actor,
            reviewer_notes=reviewer.get("notes"),
            review_metadata={
                "tenant_id": item.tenant_id,
                "lead": lead,
                "eligibility": eligibility,
                "decision": decision,
                "output_preview": item.output_preview or {},
                "execution_contract": item.execution_contract or {},
                "workflow_context": item.workflow_context or {},
                "reviewer": reviewer,
                "expectation": item.expectation,
                "queue_state_history": [history_entry],
            },
            created_at=now,
            updated_at=now,
        )
        db.add(record)
        created.append(record)
    if hasattr(db, "commit"):
        db.commit()
    return [_review_queue_response(record) for record in created]


@router.get("/workflow-review-queue/{tenant_id}", response_model=list[WorkflowReviewQueueResponse])
def list_workflow_review_queue(
    tenant_id: str,
    review_status: str | None = Query(default=None),
    batch_label: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    _: None = Depends(require_admin),
    x_admin_actor: str | None = Header(default=None, alias="X-Admin-Actor"),
    db: object = Depends(get_db),
) -> list[WorkflowReviewQueueResponse]:
    _ensure_crm_tables(db)
    _require_tenant_record(db, tenant_id)
    require_actor_permission(db, tenant_id, x_admin_actor, WORKFLOW_VIEW)
    records = _sort_recent(_list_records(db, WorkflowReviewQueueRecord, tenant_id))
    filtered: list[WorkflowReviewQueueRecord] = []
    for record in records:
        if review_status and record.review_status != review_status:
            continue
        if batch_label and record.batch_label != batch_label:
            continue
        filtered.append(record)
        if len(filtered) >= limit:
            break
    return [_review_queue_response(record) for record in filtered]


@router.patch("/workflow-review-queue/items/{review_item_id}", response_model=WorkflowReviewQueueResponse)
def update_workflow_review_queue_item(
    review_item_id: str,
    request: WorkflowReviewQueueUpdate,
    _: None = Depends(require_admin),
    x_admin_actor: str | None = Header(default=None, alias="X-Admin-Actor"),
    db: object = Depends(get_db),
) -> WorkflowReviewQueueResponse:
    _ensure_crm_tables(db)
    if hasattr(db, "get"):
        record = db.get(WorkflowReviewQueueRecord, review_item_id)
    elif hasattr(db, "query"):
        record = db.query(WorkflowReviewQueueRecord).filter_by(id=review_item_id).first()
    else:
        record = None
    if record is None:
        raise HTTPException(status_code=404, detail=f"Review item {review_item_id} not found")
    require_actor_permission(db, record.tenant_id, x_admin_actor, WORKFLOW_REVIEW)
    review_status = request.review_status.strip().lower()
    if review_status not in {"approved", "rejected", "needs_fix", "pending", "skipped"}:
        raise HTTPException(status_code=400, detail="review_status must be approved, rejected, needs_fix, pending, or skipped")
    record.review_status = review_status
    record.reviewer_name = request.reviewer_name
    record.reviewer_notes = request.reviewer_notes
    metadata = record.review_metadata or {}
    history = list(metadata.get("queue_state_history") or [])
    history.append(
        {
            "tenant_id": record.tenant_id,
            "review_status": review_status,
            "reviewer_name": request.reviewer_name,
            "reviewer_notes": request.reviewer_notes,
            "actor": x_admin_actor or request.reviewer_name or "admin",
            "changed_at": datetime.utcnow().isoformat(),
            "source": "manual_review",
        }
    )
    metadata["queue_state_history"] = history
    metadata["reviewer_update"] = {
        "tenant_id": record.tenant_id,
        "review_status": review_status,
        "reviewer_name": request.reviewer_name,
        "reviewer_notes": request.reviewer_notes,
        "actor": x_admin_actor or request.reviewer_name or "admin",
        "updated_at": datetime.utcnow().isoformat(),
    }
    record.review_metadata = metadata
    record.updated_at = datetime.utcnow()
    if hasattr(db, "commit"):
        db.commit()
    return _review_queue_response(record)


@router.post("/workflow-review-queue/items/{review_item_id}/execution", response_model=WorkflowExecutionResponse)
def create_workflow_execution(
    review_item_id: str,
    request: WorkflowExecutionCreate,
    _: None = Depends(require_admin),
    x_admin_actor: str | None = Header(default=None, alias="X-Admin-Actor"),
    db: object = Depends(get_db),
) -> WorkflowExecutionResponse:
    _ensure_crm_tables(db)
    if hasattr(db, "get"):
        review_item = db.get(WorkflowReviewQueueRecord, review_item_id)
    elif hasattr(db, "query"):
        review_item = db.query(WorkflowReviewQueueRecord).filter_by(id=review_item_id).first()
    else:
        review_item = None
    if review_item is None:
        raise HTTPException(status_code=404, detail=f"Review item {review_item_id} not found")
    require_actor_permission(db, review_item.tenant_id, x_admin_actor, WORKFLOW_EXECUTE)
    if review_item.review_status != "approved":
        raise HTTPException(status_code=409, detail="Only approved review items can enter execution")

    execution_status = request.execution_status.strip().lower()
    if execution_status not in {"queued", "ready", "blocked"}:
        raise HTTPException(status_code=400, detail="execution_status must be queued, ready, or blocked")

    now = datetime.utcnow()
    review_metadata = review_item.review_metadata or {}
    decision = review_metadata.get("decision") or {}
    execution = WorkflowExecutionRecord(
        id=f"wexec_{uuid.uuid4().hex}",
        tenant_id=review_item.tenant_id,
        review_item_id=review_item.id,
        request_id=review_item.request_id,
        batch_label=review_item.batch_label,
        workflow_type=(decision.get("workflow_type") or review_metadata.get("workflow_type")),
        offer_type=(decision.get("offer_type") or review_metadata.get("offer_type")),
        stage=(decision.get("stage") or review_metadata.get("stage")),
        execution_status=execution_status,
        execution_metadata={
            "contract_version": "workflow_execution.v1",
            "tenant_id": review_item.tenant_id,
            "actor": x_admin_actor or review_item.reviewer_name or "admin",
            "review_item_snapshot": {
                "review_item_id": review_item.id,
                "tenant_id": review_item.tenant_id,
                "review_status": review_item.review_status,
                "reviewer_name": review_item.reviewer_name,
                "reviewer_notes": review_item.reviewer_notes,
                "eligibility_status": review_item.eligibility_status,
                "system_decision": review_item.system_decision,
                "system_reason": review_item.system_reason,
            },
            "decision": decision,
            "lead": review_metadata.get("lead") or {},
            "output_preview": review_metadata.get("output_preview") or {},
            "workflow_context": review_metadata.get("workflow_context") or {},
            "execution_contract": review_metadata.get("execution_contract") or {},
            "queue_state_history": list(review_metadata.get("queue_state_history") or []),
            "requested_execution": request.metadata or {},
        },
        created_at=now,
        updated_at=now,
    )
    db.add(execution)
    if hasattr(db, "commit"):
        db.commit()
    return _execution_response(execution)


@router.get("/workflow-executions/{execution_id}/deliveries", response_model=list[WorkflowExecutionDeliveryResponse])
def list_workflow_execution_deliveries(
    execution_id: str,
    _: None = Depends(require_admin),
    x_admin_actor: str | None = Header(default=None, alias="X-Admin-Actor"),
    db: object = Depends(get_db),
) -> list[WorkflowExecutionDeliveryResponse]:
    _ensure_crm_tables(db)
    if hasattr(db, "get"):
        execution = db.get(WorkflowExecutionRecord, execution_id)
    elif hasattr(db, "query"):
        execution = db.query(WorkflowExecutionRecord).filter_by(id=execution_id).first()
    else:
        execution = None
    if execution is None:
        raise HTTPException(status_code=404, detail=f"Execution {execution_id} not found")
    require_actor_permission(db, execution.tenant_id, x_admin_actor, WORKFLOW_VIEW)
    records = [
        record
        for record in _sort_recent(_list_records(db, WorkflowExecutionDeliveryRecord, execution.tenant_id))
        if record.execution_id == execution_id
    ]
    return [_execution_delivery_response(record) for record in records]


@router.post("/workflow-executions/{execution_id}/deliver", response_model=WorkflowExecutionDeliveryResponse)
def deliver_workflow_execution(
    execution_id: str,
    request: WorkflowExecutionDeliveryCreate,
    _: None = Depends(require_admin),
    x_admin_actor: str | None = Header(default=None, alias="X-Admin-Actor"),
    db: object = Depends(get_db),
) -> WorkflowExecutionDeliveryResponse:
    _ensure_crm_tables(db)
    if hasattr(db, "get"):
        execution = db.get(WorkflowExecutionRecord, execution_id)
    elif hasattr(db, "query"):
        execution = db.query(WorkflowExecutionRecord).filter_by(id=execution_id).first()
    else:
        execution = None
    if execution is None:
        raise HTTPException(status_code=404, detail=f"Execution {execution_id} not found")
    require_actor_permission(db, execution.tenant_id, x_admin_actor, WORKFLOW_DELIVER)

    if hasattr(db, "get"):
        review_item = db.get(WorkflowReviewQueueRecord, execution.review_item_id)
    elif hasattr(db, "query"):
        review_item = db.query(WorkflowReviewQueueRecord).filter_by(id=execution.review_item_id).first()
    else:
        review_item = None
    if review_item is None:
        raise HTTPException(status_code=404, detail=f"Review item {execution.review_item_id} not found")
    if review_item.review_status != "approved":
        raise HTTPException(status_code=409, detail="Only approved review items can be delivered")

    metadata = execution.execution_metadata or {}
    contract = metadata.get("execution_contract") or {}
    if contract.get("channel") != "email":
        raise HTTPException(status_code=400, detail="Only email execution contracts are supported")
    provider_mode = str(contract.get("provider_mode") or "dry_run").lower()
    if provider_mode not in {"dry_run", "smtp"}:
        raise HTTPException(status_code=400, detail="Only dry_run and smtp provider modes are supported")

    email_payload = {
        "to": contract.get("to"),
        "subject": contract.get("subject"),
        "body": contract.get("body"),
    }
    delivery_result = _send_execution_email(email_payload, provider_mode)
    now = datetime.utcnow()
    delivery = WorkflowExecutionDeliveryRecord(
        id=f"wdeliv_{uuid.uuid4().hex}",
        tenant_id=execution.tenant_id,
        execution_id=execution.id,
        review_item_id=review_item.id,
        channel="email",
        provider=provider_mode,
        delivery_status=str(delivery_result.get("status") or "unknown"),
        delivery_metadata={
            "tenant_id": execution.tenant_id,
            "actor": x_admin_actor or review_item.reviewer_name or "admin",
            "execution_snapshot": {
                "execution_id": execution.id,
                "tenant_id": execution.tenant_id,
                "execution_status": execution.execution_status,
                "review_item_id": execution.review_item_id,
            },
            "review_snapshot": {
                "review_item_id": review_item.id,
                "tenant_id": review_item.tenant_id,
                "review_status": review_item.review_status,
                "reviewer_name": review_item.reviewer_name,
                "reviewer_notes": review_item.reviewer_notes,
            },
            "attempt_contract": contract,
            "attempt_payload": email_payload,
            "requested_delivery": request.metadata or {},
            "result": delivery_result,
        },
        created_at=now,
    )
    db.add(delivery)
    execution.execution_status = "in_progress" if delivery.delivery_status in {"dry_run", "sent"} else execution.execution_status
    execution.updated_at = now
    execution_metadata = execution.execution_metadata or {}
    delivery_history = list(execution_metadata.get("delivery_history") or [])
    delivery_history.append(
        {
            "delivery_id": delivery.id,
            "tenant_id": execution.tenant_id,
            "delivery_status": delivery.delivery_status,
            "channel": "email",
            "provider": provider_mode,
            "actor": x_admin_actor or review_item.reviewer_name or "admin",
            "created_at": now.isoformat(),
        }
    )
    execution_metadata["delivery_history"] = delivery_history
    execution.execution_metadata = execution_metadata
    if hasattr(db, "commit"):
        db.commit()
    return _execution_delivery_response(delivery)
