"""
Orchestration service — initial implementation (contract-aligned skeleton).
Implements: Service Specification §3 — Orchestration Service.
Mounts: /healthz, /readyz, /v1/workflows/start|{id}|{id}/steps|{id}/retry
STUB paths: checkpoint store, step runner, retry manager, dead-letter handler.
"""

from fastapi import FastAPI

from packages.schemas import HealthResponse
from .settings import settings
from .routers.workflows import router as workflows_router

app = FastAPI(
    title="Robco Orchestration",
    version="0.1.0",
    description="Multi-step workflow coordination with checkpoint and retry support.",
)

app.include_router(workflows_router)


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
    # STUB: add DB ping, Redis/queue ping before marking ready
    return {"status": "ready", "service": settings.service_name}
