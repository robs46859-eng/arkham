"""
SQLAlchemy ORM models — shared across all services that need DB access.
Services import from here; they never define their own table models.
Implements: Build Rules §3 — No service depends on another service's internal modules.
"""

from .base import Base
from .api_key import TenantAPIKey
from .tenant import Tenant
from .project import Project, ProjectFile
from .ingestion import IngestionJob
from .domain import BuildingElementRecord, DocumentChunkRecord, IssueRecord
from .workflow import WorkflowRunRecord, WorkflowStepRecord
from .deliverable import DeliverableRecord
from .memory import MemoryNoteRecord
from .usage import UsageEventRecord
from .billing import BillingCheckoutRecord
from .maternal import MaternalCheckinRecord, MaternalProfileRecord, MaternalResourceRecord
from .gtm import (
    GTMCampaignRecord,
    GTMConversionRecord,
    GTMOfferDecisionRecord,
    GTMProofAssetRecord,
    GTMReplyRecord,
    GTMSalesActionRecord,
    GTMSuppressionRecord,
    GTMTargetRecord,
    GTMTargetScoreRecord,
)
from .sanitizer import SanitizerEventRecord, SanitizerPolicyRecord

__all__ = [
    "Base",
    "TenantAPIKey",
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
    "BillingCheckoutRecord",
    "MaternalProfileRecord",
    "MaternalCheckinRecord",
    "MaternalResourceRecord",
    "GTMTargetRecord",
    "GTMTargetScoreRecord",
    "GTMOfferDecisionRecord",
    "GTMProofAssetRecord",
    "GTMSalesActionRecord",
    "GTMConversionRecord",
    "GTMCampaignRecord",
    "GTMReplyRecord",
    "GTMSuppressionRecord",
    "SanitizerPolicyRecord",
    "SanitizerEventRecord",
]
