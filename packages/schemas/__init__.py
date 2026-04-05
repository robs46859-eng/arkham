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
from .tenant import TenantCreate, TenantUpdate, TenantResponse

__all__ = [
    "BuildingElement",
    "Deliverable",
    "DocumentChunk",
    "HealthResponse",
    "InferenceRequest",
    "InferenceResponse",
    "IngestionRequest",
    "IngestionResponse",
    "Issue",
    "MarkupRecord",
    "MemoryNote",
    "ScheduleRow",
    "TenantCreate",
    "TenantResponse",
    "TenantUpdate",
    "UsageEvent",
    "WorkflowRun",
    "WorkflowStatus",
    "WorkflowStep",
]
