"""
SQLAlchemy ORM models — shared across all services that need DB access.
Services import from here; they never define their own table models.
Implements: Build Rules §3 — No service depends on another service's internal modules.
"""

from .base import Base
from .access import TenantActorRoleRecord
from .api_key import TenantAPIKey
from .tenant import Tenant
from .project import Project, ProjectFile
from .ingestion import IngestionJob
from .domain import BuildingElementRecord, DocumentChunkRecord, IssueRecord
from .workflow import WorkflowRunRecord, WorkflowStepRecord
from .deliverable import DeliverableRecord
from .memory import MemoryNoteRecord
from .usage import UsageEventRecord
from .automation import AutomationLogRecord
from .crm import (
    CompanyRecord,
    ContactRecord,
    LeadRecord,
    DealRecord,
    CRMActivityRecord,
    WorkflowMemoryDecisionRecord,
    WorkflowReviewQueueRecord,
    WorkflowExecutionRecord,
    WorkflowExecutionDeliveryRecord,
)
from .sidecar import (
    SidecarPersona,
    SidecarScorecard,
    SidecarFingerprint,
    SidecarParoleVerdict,
    SidecarBloodsVault,
    SidecarBenchmarkCache,
    SidecarAuditLog,
)
from .worldgraph import (
    WorldgraphEntityAliasRecord,
    WorldgraphEntityCategoryRecord,
    WorldgraphEntityEmbeddingRecord,
    WorldgraphEntityIdentifierRecord,
    WorldgraphEntityProposalRecord,
    WorldgraphEntityProvenanceRecord,
    WorldgraphEntityRecord,
    WorldgraphEntityRelationshipRecord,
    WorldgraphIngestJobRecord,
    WorldgraphProposalSourceRecord,
    WorldgraphRawObjectRecord,
    WorldgraphRawRecordRecord,
    WorldgraphSearchDocumentRecord,
    WorldgraphTravelRawAirlineRecord,
    WorldgraphTravelRawAirportRecord,
    WorldgraphTravelRawRouteRecord,
)

__all__ = [
    "Base",
    "TenantActorRoleRecord",
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
    "AutomationLogRecord",
    "CompanyRecord",
    "ContactRecord",
    "LeadRecord",
    "DealRecord",
    "CRMActivityRecord",
    "WorkflowMemoryDecisionRecord",
    "WorkflowReviewQueueRecord",
    "WorkflowExecutionRecord",
    "WorkflowExecutionDeliveryRecord",
    "SidecarPersona",
    "SidecarScorecard",
    "SidecarFingerprint",
    "SidecarParoleVerdict",
    "SidecarBloodsVault",
    "SidecarBenchmarkCache",
    "SidecarAuditLog",
    "WorldgraphIngestJobRecord",
    "WorldgraphRawObjectRecord",
    "WorldgraphRawRecordRecord",
    "WorldgraphEntityProposalRecord",
    "WorldgraphProposalSourceRecord",
    "WorldgraphEntityRecord",
    "WorldgraphEntityAliasRecord",
    "WorldgraphEntityIdentifierRecord",
    "WorldgraphEntityCategoryRecord",
    "WorldgraphEntityRelationshipRecord",
    "WorldgraphEntityProvenanceRecord",
    "WorldgraphSearchDocumentRecord",
    "WorldgraphEntityEmbeddingRecord",
    "WorldgraphTravelRawAirportRecord",
    "WorldgraphTravelRawAirlineRecord",
    "WorldgraphTravelRawRouteRecord",
]
