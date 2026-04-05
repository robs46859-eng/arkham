"""
Core Service - Central Orchestration Hub
Implements: Dynamic Service Registry, Event Bus, Unified Config
"""

from fastapi import FastAPI
from .settings import settings
from .routers import registry as registry_router
from .routers import events as events_router
from .routers import config as config_router

app = FastAPI(
    title="Robco Core",
    version="0.1.0",
    description="Central orchestration hub with service registry, event bus, and config management.",
)

app.include_router(registry_router.router)
app.include_router(events_router.router)
app.include_router(config_router.router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": settings.service_name}


@app.get("/readyz")
async def ready_check():
    # TODO: Add Redis and DB connection checks
    return {"status": "ready", "service": settings.service_name}
