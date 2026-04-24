"""Ingest job control routes for worldgraph."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from packages.db import get_db
from packages.schemas.worldgraph import WorldgraphIngestJob, WorldgraphIngestRequest

from ..services import queue
from ..services import store

router = APIRouter(prefix="/v1/worldgraph", tags=["worldgraph-ingest"])


@router.post("/{namespace}/ingest/jobs", response_model=WorldgraphIngestJob)
def create_ingest_job(
    namespace: str,
    request: WorldgraphIngestRequest,
    db: Session = Depends(get_db),
) -> WorldgraphIngestJob:
    if namespace != "travel":
        raise HTTPException(status_code=400, detail="v1 only supports namespace=travel")
    if request.source_name != "openflights":
        raise HTTPException(status_code=400, detail="v1 only supports source_name=openflights")

    job = store.create_ingest_job(db, namespace=namespace, source_name=request.source_name)
    queue.enqueue_job(
        "ingest_openflights",
        {"job_id": job.job_id, "namespace": namespace, "source_name": request.source_name},
    )
    return WorldgraphIngestJob(
        job_id=job.job_id,
        namespace=job.namespace,  # type: ignore[arg-type]
        source_name=job.source_name,
        status=job.status,  # type: ignore[arg-type]
        manifest_uri=job.manifest_uri,
        stats_json=job.stats_json or {},
        error_json=job.error_json or {},
        started_at=job.started_at,
        finished_at=job.finished_at,
    )


@router.get("/{namespace}/ingest/jobs", response_model=list[WorldgraphIngestJob])
def get_ingest_jobs(
    namespace: str,
    source_name: Annotated[str | None, Query()] = None,
    db: Session = Depends(get_db),
) -> list[WorldgraphIngestJob]:
    return store.list_ingest_jobs(db, namespace=namespace, source_name=source_name)

