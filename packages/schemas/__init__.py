"""
Shared schema package for the Robco BIM platform.
All services import contract types from here — never redefine locally.
Implements: System Contracts Document (all entity contracts)
"""

from .health import HealthResponse
from .gateway import InferenceRequest, InferenceResponse
from .ingestion import IngestionRequest, IngestionResponse
from .domain import (
    BuildingElement,
    DocumentChunk,
    Issue,
    ScheduleRow,
    MarkupRecord,
)
from .workflow import WorkflowRun, WorkflowStep, WorkflowStatus
from .deliverable import Deliverable
from .memory import MemoryNote
from .usage import UsageEvent
from .admin import (
    AdminAlert,
    AdminDashboardResponse,
    DailyUsage,
    OutreachPerformance,
    QueueStatus,
    SanitizerEvent,
    SanitizerPolicy,
    SanitizerPolicyUpdate,
    SanitizerSummary,
    ServiceBreakdown,
    TenantCreate,
    TenantAPIKeyCreateResponse,
    TenantAPIKeyResponse,
    TenantResponse,
    TenantUpdate,
    UsageRollup,
    WorkflowHealth,
)

__all__ = [
    "HealthResponse",
    "InferenceRequest",
    "InferenceResponse",
    "IngestionRequest",
    "IngestionResponse",
    "BuildingElement",
    "DocumentChunk",
    "Issue",
    "ScheduleRow",
    "MarkupRecord",
    "WorkflowRun",
    "WorkflowStep",
    "WorkflowStatus",
    "Deliverable",
    "MemoryNote",
    "UsageEvent",
    "AdminAlert",
    "AdminDashboardResponse",
    "DailyUsage",
    "OutreachPerformance",
    "QueueStatus",
    "SanitizerEvent",
    "SanitizerPolicy",
    "SanitizerPolicyUpdate",
    "SanitizerSummary",
    "ServiceBreakdown",
    "TenantCreate",
    "TenantAPIKeyCreateResponse",
    "TenantAPIKeyResponse",
    "TenantResponse",
    "TenantUpdate",
    "UsageRollup",
    "WorkflowHealth",
]
