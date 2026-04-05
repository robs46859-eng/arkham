"""
Orchestration service — initial implementation (contract-aligned skeleton).
Implements: Service Specification §3 — Orchestration Service.
Mounts: /healthz, /readyz, /v1/workflows/start|{id}|{id}/steps|{id}/retry
STUB paths: checkpoint store, step runner, retry manager, dead-letter handler.
"""

from fastapi import FastAPI

from packages.healthchecks import check_database, check_redis
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
    db_ok, db_detail = check_database(settings.database_url)
    redis_ok, redis_detail = check_redis(settings.redis_url)
    ready = db_ok and redis_ok
    return {
        "status": "ready" if ready else "not_ready",
        "service": settings.service_name,
        "dependencies": {
            "database": {"ok": db_ok, "detail": db_detail},
            "redis": {"ok": redis_ok, "detail": redis_detail},
        },
    }
