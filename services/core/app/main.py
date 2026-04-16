"""
Core Service - Central Orchestration Hub
Implements: Dynamic Service Registry, Event Bus, Unified Config
"""

from fastapi import FastAPI

from packages.healthchecks import check_database, check_redis

from .settings import settings
from .routers import registry as registry_router
from .routers import events as events_router
from .routers import config as config_router

app = FastAPI(
    title="Robco Core",
    version="0.1.0",
    description="Central orchestration hub with service registry, event bus, and config management.",
)

app.include_router(registry_router.router, prefix="/registry")
app.include_router(events_router.router, prefix="/events")
app.include_router(config_router.router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": settings.service_name, "environment": settings.app_env}


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "service": settings.service_name, "environment": settings.app_env}


@app.get("/readyz")
async def ready_check():
    db_ok, db_detail = check_database(settings.database_url)
    redis_ok, redis_detail = check_redis(settings.redis_url)
    ready = db_ok and redis_ok
    return {
        "status": "ready" if ready else "not_ready",
        "service": settings.service_name,
        "environment": settings.app_env,
        "dependencies": {
            "database": {"ok": db_ok, "detail": db_detail},
            "redis": {"ok": redis_ok, "detail": redis_detail},
        },
    }
