"""
BIM Ingestion service — initial implementation (contract-aligned skeleton).
Implements: Service Specification §2 — BIM Ingestion Service.
Mounts: /healthz, /readyz, /v1/files/register, /v1/files/{id}/ingest,
        /v1/ingestion/jobs/{id}, /v1/projects/{id}/files
STUB paths: DB session, object storage validation, worker queue dispatch.
"""

from fastapi import FastAPI

from packages.schemas import HealthResponse
from .settings import settings
from .routers.files import router as files_router

app = FastAPI(
    title="Robco BIM Ingestion",
    version="0.1.0",
    description="File intake, validation, normalization, and parse job coordination.",
)

app.include_router(files_router)


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.service_name,
        environment=settings.app_env,
    )


@app.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.service_name,
        environment=settings.app_env,
    )


@app.get("/readyz")
async def readyz() -> dict:
    # STUB: add DB ping, Redis ping, object storage reachability check
    return {"status": "ready", "service": settings.service_name}
