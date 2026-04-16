"""
Gateway service — initial implementation (contract-aligned skeleton).
Implements: Service Specification §1 — Gateway Service.
Mounts: /health, /healthz, /readyz, /v1/infer, /v1/workflows/start|{id}
STUB paths: semantic cache lookup, usage metering, JWT auth, orchestration client.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from packages.healthchecks import check_database, check_redis
from packages.schemas import HealthResponse
from .settings import settings
from .routers import infer as infer_router
from .routers import workflows as workflows_router
from .routers import auth as auth_router
from .routers import tenants as tenants_router
from .routers import verticals as verticals_router
from .routers import billing as billing_router
from .routers import ai as ai_router
from .routers import crm as crm_router

app = FastAPI(
    title="Stelar Gateway",
    version="0.1.0",
    description="Centralized inference control plane and policy engine.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(infer_router.router)
app.include_router(workflows_router.router)
app.include_router(tenants_router.router)
app.include_router(verticals_router.router)
app.include_router(billing_router.router)
app.include_router(ai_router.router)
app.include_router(crm_router.router)


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


@app.get("/metrics")
async def metrics() -> dict:
    # STUB: expose Prometheus-compatible metrics in next observability step
    return {"status": "metrics endpoint scaffolded — not yet implemented"}
