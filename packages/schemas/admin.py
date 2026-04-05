"""Admin and control-plane schemas used by the dashboard APIs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TenantCreate(BaseModel):
    name: str
    is_active: bool = True
    plan: str = "free"
    enable_premium_escalation: bool = False
    enable_semantic_cache: bool = False

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Robco Staging",
                "is_active": True,
                "plan": "enterprise",
                "enable_premium_escalation": True,
                "enable_semantic_cache": True,
            }
        }
    )


class TenantUpdate(BaseModel):
    name: str | None = None
    plan: str | None = None
    is_active: bool | None = None
    enable_premium_escalation: bool | None = None
    enable_semantic_cache: bool | None = None
    cache_similarity_threshold: float | None = None
    max_requests_per_day: int | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "plan": "enterprise",
                "enable_premium_escalation": True,
                "enable_semantic_cache": True,
                "cache_similarity_threshold": 0.94,
                "max_requests_per_day": 5000,
            }
        }
    )


class TenantResponse(BaseModel):
    tenant_id: str
    name: str
    plan: str = "free"
    is_active: bool
    enable_premium_escalation: bool = False
    enable_semantic_cache: bool = False
    cache_similarity_threshold: float = 0.92
    max_requests_per_day: int | None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tenant_id": "tenant_01hv6n6j6h8x7m4r9k2p1q3s4t",
                "name": "Robco Staging",
                "plan": "enterprise",
                "is_active": True,
                "enable_premium_escalation": True,
                "enable_semantic_cache": True,
                "cache_similarity_threshold": 0.92,
                "max_requests_per_day": 5000,
                "created_at": "2026-04-05T12:00:00Z",
                "updated_at": "2026-04-05T12:30:00Z",
            }
        }
    )


class TenantAPIKeyCreateResponse(BaseModel):
    api_key_id: str
    tenant_id: str
    key_prefix: str
    api_key: str
    created_at: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "api_key_id": "key_01hv6q2t6j8x7m4r9k2p1q3s4t",
                "tenant_id": "tenant_01hv6n6j6h8x7m4r9k2p1q3s4t",
                "key_prefix": "rk_live_01hv",
                "api_key": "rk_live_01hv_example_plaintext_key",
                "created_at": "2026-04-05T12:35:00Z",
            }
        }
    )


class TenantAPIKeyResponse(BaseModel):
    api_key_id: str
    tenant_id: str
    key_prefix: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_used_at: datetime | None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "api_key_id": "key_01hv6q2t6j8x7m4r9k2p1q3s4t",
                "tenant_id": "tenant_01hv6n6j6h8x7m4r9k2p1q3s4t",
                "key_prefix": "rk_live_01hv",
                "is_active": True,
                "created_at": "2026-04-05T12:35:00Z",
                "updated_at": "2026-04-05T12:35:00Z",
                "last_used_at": "2026-04-05T13:10:00Z",
            }
        }
    )


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
