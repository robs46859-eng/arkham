"""
File registration and ingestion endpoints.
Implements: Service Spec §2.5 core endpoints.
  POST /v1/files/register     — register a project file and create a traceable record
  POST /v1/files/{file_id}/ingest — dispatch an ingestion job for a registered file
  GET  /v1/ingestion/jobs/{job_id} — get job status
  GET  /v1/projects/{project_id}/files — list registered files for a project
  GET  /v1/ingestion/jobs — list jobs filtered by tenant_id (tenant isolation)
STUB: DB persistence, object storage validation, and worker dispatch are next steps.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel

from packages.schemas import IngestionRequest, IngestionResponse
from packages.schemas.ingestion import JobStatus, FileType
from packages.db import get_db

router = APIRouter(prefix="/v1", tags=["ingestion"])


class FileRegisterRequest(BaseModel):
    """Request body for registering a new project file."""

    tenant_id: str  # format: tenant_<ulid>
    project_id: str  # format: proj_<ulid>
    file_type: FileType
    storage_path: str


class FileRegisterResponse(BaseModel):
    """Response after a file is registered."""

    file_id: str  # format: file_<ulid>
    project_id: str
    file_type: FileType
    storage_path: str
    registered_at: datetime


class JobStatusResponse(BaseModel):
    """Job status response."""

    job_id: str
    status: JobStatus
    entities_created: int
    errors: list[str]


class IngestionJobResponse(BaseModel):
    """Response for listing ingestion jobs."""

    job_id: str
    file_id: str
    project_id: str
    tenant_id: str
    status: JobStatus
    entities_created: int
    created_at: datetime


def _get_session(db) -> None:
    """Get database session from dependency injection."""
    return db


@router.post("/files/register", response_model=FileRegisterResponse)
async def register_file(request: FileRegisterRequest, db=Depends(get_db)) -> FileRegisterResponse:  # noqa: B008
    """
    Register a project file and create a traceable project_file record.
    STUB: writes to DB (project_files table) and validates storage path reachability.
    """
    if not request.tenant_id.startswith("tenant_"):
        raise HTTPException(status_code=400, detail="Invalid tenant_id format. Expected: tenant_<ulid>")
    if not request.project_id.startswith("proj_"):
        raise HTTPException(status_code=400, detail="Invalid project_id format. Expected: proj_<ulid>")

    file_id = f"file_{uuid.uuid4().hex}"
    now = datetime.utcnow()

    # STUB: persist to project_files table via SQLAlchemy session
    return FileRegisterResponse(
        file_id=file_id,
        project_id=request.project_id,
        file_type=request.file_type,
        storage_path=request.storage_path,
        registered_at=now,
    )


@router.post("/files/{file_id}/ingest", response_model=IngestionResponse)
async def ingest_file(file_id: str, request: IngestionRequest, db=Depends(get_db)) -> IngestionResponse:  # noqa: B008
    """
    Dispatch an ingestion job for a registered file.
    Routes to the correct worker by file_type (IFC → bim_parser, PDF → pdf_extractor, etc.).
    STUB: creates IngestionJob record and dispatches worker task via queue.
    """
    if not file_id.startswith("file_"):
        raise HTTPException(status_code=400, detail="Invalid file_id format. Expected: file_<ulid>")
    if file_id != request.file_id:
        raise HTTPException(status_code=400, detail="file_id in path does not match request body")

    job_id = f"job_{uuid.uuid4().hex}"

    # STUB: Store job in database session for testing
    from packages.models.ingestion import IngestionJob

    job = IngestionJob(
        id=job_id,
        file_id=file_id,
        project_id=request.project_id,
        tenant_id=request.tenant_id,
        status=JobStatus.queued,
        entities_created=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(job)

    # STUB: create IngestionJob record, dispatch to worker queue by file_type
    return IngestionResponse(
        job_id=job_id,
        status=JobStatus.queued,
        entities_created=0,
        errors=[],
    )


@router.get("/ingestion/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str, db=Depends(get_db)) -> JobStatusResponse:  # noqa: B008
    """
    Retrieve current status of an ingestion job.
    STUB: query ingestion_jobs table.
    """
    if not job_id.startswith("job_"):
        raise HTTPException(status_code=400, detail="Invalid job_id format. Expected: job_<ulid>")

    # STUB: replace with DB lookup
    raise HTTPException(status_code=404, detail=f"Job {job_id} not found (stub — DB lookup not yet wired)")


@router.get("/ingestion/jobs", response_model=List[IngestionJobResponse])
async def list_ingestion_jobs(
    tenant_id: str = Query(...),
    db=Depends(get_db),  # noqa: B008
) -> List[IngestionJobResponse]:
    """
    List ingestion jobs filtered by tenant_id.
    Implements tenant isolation - only returns jobs for the specified tenant.

    STUB: Uses database session. Production must query database with tenant filtering.
    """
    if not tenant_id.startswith("tenant_"):
        raise HTTPException(status_code=400, detail="Invalid tenant_id format. Expected: tenant_<ulid>")

    # Query jobs from database session filtered by tenant_id
    from packages.models.ingestion import IngestionJob

    jobs_query = db.query(IngestionJob).filter_by(tenant_id=tenant_id)
    jobs = jobs_query.all()

    results = []
    for job in jobs:
        results.append(
            IngestionJobResponse(
                job_id=job.id,
                file_id=job.file_id,
                project_id=job.project_id,
                tenant_id=job.tenant_id,
                status=job.status,
                entities_created=job.entities_created,
                created_at=job.created_at,
            )
        )

    return results


@router.get("/projects/{project_id}/files", response_model=list[FileRegisterResponse])
async def list_project_files(project_id: str, db=Depends(get_db)) -> list[FileRegisterResponse]:  # noqa: B008
    """
    List all registered files for a project.
    STUB: query project_files table filtered by project_id.
    """
    if not project_id.startswith("proj_"):
        raise HTTPException(status_code=400, detail="Invalid project_id format. Expected: proj_<ulid>")

    # STUB: replace with DB query
    return []
