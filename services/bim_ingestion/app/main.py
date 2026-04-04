"""
BIM Ingestion service — initial implementation (contract-aligned stub).
Implements: Service Specification §2 — BIM Ingestion Service.
Full v1 endpoints (/v1/files/register, /v1/files/{id}/ingest, etc.) added in next layer.
"""

from fastapi import FastAPI

from packages.schemas import HealthResponse
from .settings import settings

app = FastAPI(title="Robco BIM Ingestion")


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    config = settings
    return HealthResponse(
        status="ok",
        service=config.service_name,
        environment=config.app_env,
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
    # STUB: add real dependency checks (db, redis, storage) before marking ready
    return {"status": "ready", "service": settings.service_name}
