"""
SQLAlchemy ORM models — shared across all services that need DB access.
Services import from here; they never define their own table models.
Implements: Build Rules §3 — No service depends on another service's internal modules.
"""

from .base import Base
from .tenant import Tenant
from .project import Project, ProjectFile
from .ingestion import IngestionJob
from .domain import BuildingElementRecord, DocumentChunkRecord, IssueRecord
from .workflow import WorkflowRunRecord, WorkflowStepRecord
from .deliverable import DeliverableRecord
from .memory import MemoryNoteRecord
from .usage import UsageEventRecord

__all__ = [
    "Base",
    "Tenant",
    "Project",
    "ProjectFile",
    "IngestionJob",
    "BuildingElementRecord",
    "DocumentChunkRecord",
    "IssueRecord",
    "WorkflowRunRecord",
    "WorkflowStepRecord",
    "DeliverableRecord",
    "MemoryNoteRecord",
    "UsageEventRecord",
]
