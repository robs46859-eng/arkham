"""
Billing Service
Handles Stripe checkout sessions, customer portal, and webhook events.
"""

from fastapi import FastAPI

from packages.healthchecks import check_database, check_redis

from .settings import settings
from .routers import checkout as checkout_router
from .routers import webhooks as webhooks_router

app = FastAPI(
    title="Robco Billing",
    version="0.1.0",
    description="Stripe checkout, customer portal, and webhook processing.",
)

app.include_router(checkout_router.router)
app.include_router(webhooks_router.router)


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
