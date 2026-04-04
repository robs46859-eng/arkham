"""Health check response schema. Used by all services."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str
