"""Privacy service main application."""

from fastapi import FastAPI

from .settings import settings
from .routers import redaction_router

app = FastAPI(
    title="Privacy Core",
    description="PII detection and redaction service for the Robco platform",
    version="0.1.0",
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": settings.service_name}


app.include_router(redaction_router)
