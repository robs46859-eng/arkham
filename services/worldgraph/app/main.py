"""Worldgraph service entrypoint."""

from __future__ import annotations

from fastapi import FastAPI

from packages.healthchecks import check_database, check_redis
from packages.schemas import HealthResponse

from .routers import canon as canon_router
from .routers import ingest as ingest_router
from .routers import search as search_router
from .settings import settings

app = FastAPI(
    title="Arkham Worldgraph",
    version="0.1.0",
    description="Worldgraph canonical entity service and ingest control plane.",
)

app.include_router(ingest_router.router)
app.include_router(canon_router.router)
app.include_router(search_router.router)


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(status="ok", service=settings.service_name, environment=settings.app_env)


@app.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    return HealthResponse(status="ok", service=settings.service_name, environment=settings.app_env)


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

