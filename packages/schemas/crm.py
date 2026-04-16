"""Shared CRM schemas for model-agnostic gateway access."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CompanyCreate(BaseModel):
    name: str
    website: str | None = None
    industry: str | None = None
    notes: dict = Field(default_factory=dict)


class CompanyUpdate(BaseModel):
    name: str | None = None
    website: str | None = None
    industry: str | None = None
    notes: dict | None = None


class CompanyResponse(BaseModel):
    company_id: str
    tenant_id: str
    name: str
    website: str | None = None
    industry: str | None = None
    notes: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class ContactCreate(BaseModel):
    company_id: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    title: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None
    status: str = "lead"
    notes: dict = Field(default_factory=dict)


class ContactUpdate(BaseModel):
    company_id: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    title: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None
    status: str | None = None
    notes: dict | None = None


class ContactResponse(BaseModel):
    contact_id: str
    tenant_id: str
    company_id: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    title: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None
    status: str
    notes: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class LeadCreate(BaseModel):
    company_id: str | None = None
    contact_id: str | None = None
    source: str = "manual"
    status: str = "new"
    fit_score: float | None = None
    notes: str | None = None
    metadata: dict = Field(default_factory=dict)


class LeadUpdate(BaseModel):
    company_id: str | None = None
    contact_id: str | None = None
    source: str | None = None
    status: str | None = None
    fit_score: float | None = None
    notes: str | None = None
    metadata: dict | None = None


class LeadResponse(BaseModel):
    lead_id: str
    tenant_id: str
    company_id: str | None = None
    contact_id: str | None = None
    source: str
    status: str
    fit_score: float | None = None
    notes: str | None = None
    metadata: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class DealCreate(BaseModel):
    company_id: str | None = None
    contact_id: str | None = None
    name: str
    stage: str = "new"
    status: str = "open"
    amount_cents: int | None = None
    currency: str = "USD"
    notes: str | None = None


class DealUpdate(BaseModel):
    company_id: str | None = None
    contact_id: str | None = None
    name: str | None = None
    stage: str | None = None
    status: str | None = None
    amount_cents: int | None = None
    currency: str | None = None
    notes: str | None = None


class DealResponse(BaseModel):
    deal_id: str
    tenant_id: str
    company_id: str | None = None
    contact_id: str | None = None
    name: str
    stage: str
    status: str
    amount_cents: int | None = None
    currency: str
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class ActivityCreate(BaseModel):
    lead_id: str | None = None
    deal_id: str | None = None
    contact_id: str | None = None
    activity_type: str
    subject: str | None = None
    body: str | None = None
    metadata: dict = Field(default_factory=dict)


class ActivityResponse(BaseModel):
    activity_id: str
    tenant_id: str
    lead_id: str | None = None
    deal_id: str | None = None
    contact_id: str | None = None
    activity_type: str
    subject: str | None = None
    body: str | None = None
    metadata: dict = Field(default_factory=dict)
    created_at: datetime


class CRMContextResponse(BaseModel):
    tenant_id: str
    query: str | None = None
    totals: dict[str, int] = Field(default_factory=dict)
    companies: list[CompanyResponse] = Field(default_factory=list)
    contacts: list[ContactResponse] = Field(default_factory=list)
    leads: list[LeadResponse] = Field(default_factory=list)
    deals: list[DealResponse] = Field(default_factory=list)
    activities: list[ActivityResponse] = Field(default_factory=list)


class WorkflowMemoryStoreRequest(BaseModel):
    workflow_type: str
    offer_type: str | None = None
    stage: str | None = None
    input_text: str
    output: dict = Field(default_factory=dict)
    context: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)


class WorkflowMemoryRecallRequest(BaseModel):
    workflow_type: str
    offer_type: str | None = None
    stage: str | None = None
    input_text: str
    context: dict = Field(default_factory=dict)
    threshold: float | None = None


class WorkflowMemoryResponse(BaseModel):
    tenant_id: str
    workflow_type: str
    offer_type: str | None = None
    stage: str | None = None
    task_type: str
    cache_enabled: bool
    cache_hit: bool = False
    stored: bool = False
    output: dict | None = None
    metadata: dict = Field(default_factory=dict)


class WorkflowOutcomeLogRequest(BaseModel):
    workflow_type: str
    offer_type: str | None = None
    stage: str | None = None
    outcome: str
    source: str
    lead_id: str | None = None
    deal_id: str | None = None
    contact_id: str | None = None
    metadata: dict = Field(default_factory=dict)


class WorkflowOutcomeResponse(BaseModel):
    tenant_id: str
    workflow_type: str
    offer_type: str | None = None
    stage: str | None = None
    task_type: str
    score: float
    counts: dict[str, int] = Field(default_factory=dict)
    last_outcome: str
    source: str
    activity_id: str


class WorkflowMemoryConfigResponse(BaseModel):
    configured_reuse_min_score: float
    effective_reuse_min_score: float
    auto_reuse_score_floor: float
    outcome_weights: dict[str, float] = Field(default_factory=dict)


class WorkflowMemoryConfigUpdate(BaseModel):
    reuse_min_score: float | None = None
    outcome_weights: dict[str, float] | None = None


class WorkflowMemoryMetricsResponse(BaseModel):
    tenant_id: str
    workflow_type: str | None = None
    offer_type: str | None = None
    stage: str | None = None
    recall_attempts: int = 0
    recall_hits: int = 0
    fallback_count: int = 0
    fallback_reasons: dict[str, int] = Field(default_factory=dict)
    hit_rate: float = 0.0
    fallback_rate: float = 0.0
    version_mismatch_rate: float = 0.0
    total_estimated_time_saved_ms: int = 0
    average_estimated_time_saved_ms: float = 0.0
    outcome_counts: dict[str, int] = Field(default_factory=dict)
    outcome_score: float = 0.0


class WorkflowMemoryDecisionResponse(BaseModel):
    decision_id: str
    tenant_id: str
    request_id: str
    workflow_type: str
    offer_type: str | None = None
    offer_version: str | None = None
    stage: str | None = None
    audience: str | None = None
    prompt_key: str | None = None
    prompt_schema_version: str | None = None
    workflow_memory_schema_version: str | None = None
    task_type: str
    cache_attempted: bool
    recalled_score: float | None = None
    reuse_threshold: float | None = None
    decision: str
    fallback_reason: str | None = None
    stored: bool
    estimated_time_saved_ms: int = 0
    metadata: dict = Field(default_factory=dict)
    created_at: datetime


class WorkflowReviewQueueImportItem(BaseModel):
    tenant_id: str
    case_name: str
    request_id: str | None = None
    lead: dict = Field(default_factory=dict)
    eligibility: dict = Field(default_factory=dict)
    decision: dict = Field(default_factory=dict)
    output_preview: dict = Field(default_factory=dict)
    execution_contract: dict = Field(default_factory=dict)
    workflow_context: dict = Field(default_factory=dict)
    reviewer: dict = Field(default_factory=dict)
    expectation: str | None = None


class WorkflowReviewQueueImportRequest(BaseModel):
    batch_label: str
    source_artifact: str | None = None
    items: list[WorkflowReviewQueueImportItem] = Field(default_factory=list)


class WorkflowReviewQueueUpdate(BaseModel):
    review_status: str
    reviewer_name: str | None = None
    reviewer_notes: str | None = None


class WorkflowReviewQueueResponse(BaseModel):
    review_item_id: str
    tenant_id: str
    batch_label: str
    source_artifact: str | None = None
    request_id: str | None = None
    case_name: str
    lead_name: str | None = None
    company_name: str | None = None
    contact_email: str | None = None
    eligibility_status: str
    system_decision: str
    system_reason: str | None = None
    review_status: str
    reviewer_name: str | None = None
    reviewer_notes: str | None = None
    metadata: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    outcome_counts: dict[str, int] = Field(default_factory=dict)
    outcome_score: float = 0.0


class WorkflowExecutionCreate(BaseModel):
    execution_status: str = "queued"
    metadata: dict = Field(default_factory=dict)


class WorkflowExecutionResponse(BaseModel):
    execution_id: str
    tenant_id: str
    review_item_id: str
    request_id: str | None = None
    batch_label: str | None = None
    workflow_type: str | None = None
    offer_type: str | None = None
    stage: str | None = None
    execution_status: str
    metadata: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class WorkflowExecutionDeliveryCreate(BaseModel):
    metadata: dict = Field(default_factory=dict)


class WorkflowExecutionDeliveryResponse(BaseModel):
    delivery_id: str
    tenant_id: str
    execution_id: str
    review_item_id: str
    channel: str
    provider: str
    delivery_status: str
    metadata: dict = Field(default_factory=dict)
    created_at: datetime
