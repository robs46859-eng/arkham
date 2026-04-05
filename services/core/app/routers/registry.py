"""
Dynamic Service Registry
Tracks active services, their endpoints, and health status.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime

from ..runtime.store import delete_registry, get_registry, list_registry, put_registry

router = APIRouter()


class ServiceRegistration(BaseModel):
    service_id: str
    service_type: str  # e.g., "vertical", "core", "infrastructure"
    endpoint: str
    port: int
    version: str
    capabilities: List[str] = []
    metadata: dict = {}


class ServiceStatus(BaseModel):
    service_id: str
    status: str  # "healthy", "unhealthy", "unknown"
    last_seen: datetime
    uptime_seconds: Optional[int] = None


@router.post("/register", response_model=dict)
async def register_service(registration: ServiceRegistration):
    """Register a new service or update existing one."""
    put_registry(registration.service_id, {
        **registration.dict(),
        "registered_at": datetime.utcnow(),
        "last_heartbeat": datetime.utcnow(),
        "status": "healthy"
    })
    return {"status": "registered", "service_id": registration.service_id}


@router.post("/heartbeat/{service_id}")
async def service_heartbeat(service_id: str):
    """Update service heartbeat timestamp."""
    service = get_registry(service_id)
    if service is None:
        raise HTTPException(status_code=404, detail="Service not found")

    service["last_heartbeat"] = datetime.utcnow()
    service["status"] = "healthy"
    put_registry(service_id, service)
    return {"status": "ok", "service_id": service_id}


@router.get("/services", response_model=List[dict])
async def list_services(service_type: Optional[str] = None):
    """List all registered services, optionally filtered by type."""
    services = list_registry()
    if service_type:
        services = [s for s in services if s.get("service_type") == service_type]
    return services


@router.get("/services/{service_id}", response_model=dict)
async def get_service(service_id: str):
    """Get details for a specific service."""
    service = get_registry(service_id)
    if service is None:
        raise HTTPException(status_code=404, detail="Service not found")
    return service


@router.delete("/services/{service_id}")
async def unregister_service(service_id: str):
    """Remove a service from the registry."""
    if not delete_registry(service_id):
        raise HTTPException(status_code=404, detail="Service not found")
    return {"status": "unregistered", "service_id": service_id}


@router.post("/discover", response_model=List[dict])
async def discover_services(capability: Optional[str] = None):
    """Discover services by capability."""
    services = list_registry()
    if capability:
        services = [s for s in services if capability in s.get("capabilities", [])]
    return services
