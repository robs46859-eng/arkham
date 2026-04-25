"""Admin and control-plane schemas used by the dashboard APIs."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TenantCreate(BaseModel):
    name: str
    is_active: bool = True
    plan: str = "free"
    enable_premium_escalation: bool = False
    enable_semantic_cache: bool = False


class TenantUpdate(BaseModel):
    name: str | None = None
    plan: str | None = None
    is_active: bool | None = None
    enable_premium_escalation: bool | None = None
    enable_semantic_cache: bool | None = None
    cache_similarity_threshold: float | None = None
    max_requests_per_day: int | None = None


class TenantResponse(BaseModel):
    tenant_id: str
    name: str
    plan: str = "free"
    is_active: bool
    enable_premium_escalation: bool = False
    enable_semantic_cache: bool = False
    cache_similarity_threshold: float = 0.92
    max_requests_per_day: int | None
    entitlements: dict[str, Any] = Field(default_factory=dict)
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    stripe_price_id: str | None = None
    subscription_status: str = "inactive"
    subscription_current_period_end: datetime | None = None
    subscription_cancel_at_period_end: bool = False
    created_at: datetime
    updated_at: datetime | None = None


class TenantAPIKeyCreateResponse(BaseModel):
    api_key_id: str
    tenant_id: str
    key_prefix: str
    api_key: str
    created_at: datetime


class TenantAPIKeyResponse(BaseModel):
    api_key_id: str
    tenant_id: str
    key_prefix: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_used_at: datetime | None


class TenantActorRoleUpsert(BaseModel):
    actor_id: str
    display_name: str | None = None
    role: str
    granted_permissions: list[str] = Field(default_factory=list)
    denied_permissions: list[str] = Field(default_factory=list)
    is_active: bool = True


class TenantActorRoleResponse(BaseModel):
    membership_id: str
    tenant_id: str
    actor_id: str
    display_name: str | None = None
    role: str
    permissions: list[str] = Field(default_factory=list)
    granted_permissions: list[str] = Field(default_factory=list)
    denied_permissions: list[str] = Field(default_factory=list)
    is_active: bool
    source: str = "assigned"
    created_at: datetime
    updated_at: datetime


class TenantActorPermissionSummary(BaseModel):
    tenant_id: str
    actor_id: str
    role: str
    permissions: list[str] = Field(default_factory=list)
    source: str


class DailyUsage(BaseModel):
    date: str
    requests: int
    cost_usd: float


class ServiceBreakdown(BaseModel):
    service: str
    requests: int
    cost_usd: float


class UsageRollup(BaseModel):
    tenant_id: str
    period_days: int
    total_requests: int
    total_cost_usd: float
    daily_breakdown: list[DailyUsage] = Field(default_factory=list)
    by_service: list[ServiceBreakdown] = Field(default_factory=list)


class AdminAlert(BaseModel):
    id: str
    severity: str
    title: str
    detail: str
    related_id: str | None = None


class WorkflowHealth(BaseModel):
    running: int
    failed: int
    complete: int
    queued_jobs: int


class GovernanceScorecardResponse(BaseModel):
    scorecard_id: str
    battery: str
    passed: bool
    total_tokens: int
    latency_ms: int
    cost_usd: float
    scores: dict = Field(default_factory=dict)
    created_at: datetime


class GovernanceVerdictResponse(BaseModel):
    verdict_id: str
    persona_id: str
    persona_display_name: str | None = None
    persona_state: str | None = None
    tenant_id: str
    request_id: str | None = None
    checkpoint: str
    verdict: str
    shadow_mode: bool
    reasoning: str | None = None
    drift_score: float | None = None
    yard_match_score: float | None = None
    yard_match_id: str | None = None
    battery_scores: dict = Field(default_factory=dict)
    scorecards: list[GovernanceScorecardResponse] = Field(default_factory=list)
    created_at: datetime


class GovernanceSummaryResponse(BaseModel):
    total_verdicts: int
    shadow_mode_count: int
    enforced_count: int
    tenant_count: int
    verdict_counts: dict[str, int] = Field(default_factory=dict)
    checkpoint_counts: dict[str, int] = Field(default_factory=dict)
    latest_verdict_at: datetime | None = None
    daily_verdicts: list[dict] = Field(default_factory=list)
    recent_alerts: list[AdminAlert] = Field(default_factory=list)


class QueueStatus(BaseModel):
    service: str
    queued: int
    processing: int
    failed: int


class OutreachPerformance(BaseModel):
    sent: int
    positive_replies: int
    objections: int
    unsubscribes: int
    follow_up_queue: int


class SanitizerPolicy(BaseModel):
    policy_id: str
    tenant_id: str
    product_module: str
    mode: str
    detector_classes: list[str] = Field(default_factory=list)
    mask_rules: list[str] = Field(default_factory=list)
    block_rules: list[str] = Field(default_factory=list)
    rehydrate_rules: list[str] = Field(default_factory=list)
    payload: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class SanitizerPolicyUpdate(BaseModel):
    product_module: str = "enterprise_zero_trust_llm_sanitization"
    mode: str = "shadow"
    detector_classes: list[str] = Field(default_factory=list)
    mask_rules: list[str] = Field(default_factory=list)
    block_rules: list[str] = Field(default_factory=list)
    rehydrate_rules: list[str] = Field(default_factory=list)
    payload: dict = Field(default_factory=dict)


class SanitizerEvent(BaseModel):
    event_id: str
    tenant_id: str
    policy_id: str | None = None
    detector_class: str
    action: str
    mode: str
    request_ref: str
    summary: str
    payload: dict = Field(default_factory=dict)
    created_at: datetime


class SanitizerSummary(BaseModel):
    findings: int
    blocked: int
    redacted: int
    shadow_mode_events: int
    enforce_mode_events: int


class AdminDashboardResponse(BaseModel):
    tenants_total: int
    active_tenants: int
    outreach: OutreachPerformance
    workflow_health: WorkflowHealth
    queue_status: list[QueueStatus] = Field(default_factory=list)
    sanitizer_summary: SanitizerSummary
    recent_alerts: list[AdminAlert] = Field(default_factory=list)


class PredictabilityFactor(BaseModel):
    key: str
    label: str
    score: float
    impact: str
    detail: str


class PredictabilityScale(BaseModel):
    score: float
    band: str
    confidence: float
    factors: list[PredictabilityFactor] = Field(default_factory=list)
    summary: str


class DigitalTwinProjectSummary(BaseModel):
    project_id: str
    tenant_id: str
    tenant_name: str
    project_name: str
    twin_status: str
    twin_version: str
    readiness_score: float
    file_counts: dict[str, int] = Field(default_factory=dict)
    building_element_count: int = 0
    document_chunk_count: int = 0
    issue_count: int = 0
    high_severity_issue_count: int = 0
    workflow_run_count: int = 0
    latest_ingestion_status: str | None = None
    latest_activity_at: datetime | None = None
    alerts: list[str] = Field(default_factory=list)
    operational_predictability: PredictabilityScale
    environmental_predictability: PredictabilityScale
