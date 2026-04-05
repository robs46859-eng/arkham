"""
Gateway service — initial implementation (contract-aligned skeleton).
Implements: Service Specification §1 — Gateway Service.
Mounts: /health, /healthz, /readyz, /v1/infer, /v1/workflows/start|{id}
STUB paths: semantic cache lookup, usage metering, JWT auth, orchestration client.
"""

from fastapi import FastAPI

from packages.healthchecks import check_database, check_redis
from packages.schemas import HealthResponse
from .settings import settings
from .routers import infer as infer_router
from .routers import workflows as workflows_router
from .routers import auth as auth_router
from .routers import tenants as tenants_router

app = FastAPI(
    title="Robco Gateway",
    version="0.1.0",
    description=(
        "Centralized inference control plane and policy engine for tenant-scoped "
        "authentication, normalized inference, workflow entry, and control-plane "
        "tenant administration."
    ),
    contact={
        "name": "Robco Platform",
        "email": "robcofamily@gmail.com",
    },
    tags_metadata=[
        {
            "name": "auth",
            "description": "Exchange a tenant API key for a bearer token.",
        },
        {
            "name": "inference",
            "description": "Submit normalized AI inference requests through the gateway.",
        },
        {
            "name": "tenants",
            "description": "Create and manage tenants plus tenant-scoped API keys.",
        },
        {
            "name": "workflows",
            "description": "Start and inspect workflow runs routed through the orchestration layer.",
        },
    ],
)

app.include_router(auth_router.router)
app.include_router(infer_router.router)
app.include_router(workflows_router.router)
app.include_router(tenants_router.router)


@app.get("/health", response_model=HealthResponse, tags=["system"], summary="Liveness check")
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.service_name,
        environment=settings.app_env,
    )


@app.get("/healthz", response_model=HealthResponse, tags=["system"], summary="Health check")
async def healthz() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.service_name,
        environment=settings.app_env,
    )


@app.get("/readyz", tags=["system"], summary="Readiness check")
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


@app.get("/metrics", tags=["system"], summary="Metrics scaffold status")
async def metrics() -> dict:
    # STUB: expose Prometheus-compatible metrics in next observability step
    return {"status": "metrics endpoint scaffolded — not yet implemented"}
