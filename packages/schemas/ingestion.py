"""
Ingestion contract schemas.
Implements: System Contracts Document — Ingestion Contract
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class FileType(str, Enum):
    ifc = "ifc"
    pdf = "pdf"
    schedule = "schedule"
    markup = "markup"


class JobStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    complete = "complete"
    failed = "failed"


class IngestionRequest(BaseModel):
    """File ingestion request submitted to the BIM ingestion service."""

    tenant_id: str  # format: tenant_<ulid>
    project_id: str  # format: proj_<ulid>
    file_id: str  # format: file_<ulid>
    file_type: FileType
    storage_path: str


class IngestionResponse(BaseModel):
    """Initial response after an ingestion job is created."""

    job_id: str  # format: job_<ulid>
    status: JobStatus
    entities_created: int = 0
    errors: list[str] = Field(default_factory=list)
