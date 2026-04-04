"""
Gateway service — initial implementation (contract-aligned skeleton).
Implements: Service Specification §1 — Gateway Service.
Mounts: /health, /healthz, /readyz, /v1/infer, /v1/workflows/start|{id}
STUB paths: semantic cache lookup, usage metering, JWT auth, orchestration client.
"""

from fastapi import FastAPI

from packages.schemas import HealthResponse
from .settings import settings
from .routers import infer as infer_router
from .routers import workflows as workflows_router

app = FastAPI(
    title="Robco Gateway",
    version="0.1.0",
    description="Centralized inference control plane and policy engine.",
)

app.include_router(infer_router.router)
app.include_router(workflows_router.router)


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
    # STUB: add Redis ping, DB connection check before marking ready
    return {"status": "ready", "service": settings.service_name}


@app.get("/metrics")
async def metrics() -> dict:
    # STUB: expose Prometheus-compatible metrics in next observability step
    return {"status": "metrics endpoint scaffolded — not yet implemented"}
