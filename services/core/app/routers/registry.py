"""
Dynamic Service Registry
Tracks active services, their endpoints, and health status.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime

router = APIRouter()

# In-memory registry (will be replaced with Redis in production)
service_registry: Dict[str, dict] = {}


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
    service_registry[registration.service_id] = {
        **registration.dict(),
        "registered_at": datetime.utcnow(),
        "last_heartbeat": datetime.utcnow(),
        "status": "healthy"
    }
    return {"status": "registered", "service_id": registration.service_id}


@router.post("/heartbeat/{service_id}")
async def service_heartbeat(service_id: str):
    """Update service heartbeat timestamp."""
    if service_id not in service_registry:
        raise HTTPException(status_code=404, detail="Service not found")
    
    service_registry[service_id]["last_heartbeat"] = datetime.utcnow()
    service_registry[service_id]["status"] = "healthy"
    return {"status": "ok", "service_id": service_id}


@router.get("/services", response_model=List[dict])
async def list_services(service_type: Optional[str] = None):
    """List all registered services, optionally filtered by type."""
    services = list(service_registry.values())
    if service_type:
        services = [s for s in services if s.get("service_type") == service_type]
    return services


@router.get("/services/{service_id}", response_model=dict)
async def get_service(service_id: str):
    """Get details for a specific service."""
    if service_id not in service_registry:
        raise HTTPException(status_code=404, detail="Service not found")
    return service_registry[service_id]


@router.delete("/services/{service_id}")
async def unregister_service(service_id: str):
    """Remove a service from the registry."""
    if service_id not in service_registry:
        raise HTTPException(status_code=404, detail="Service not found")
    
    del service_registry[service_id]
    return {"status": "unregistered", "service_id": service_id}


@router.post("/discover", response_model=List[dict])
async def discover_services(capability: Optional[str] = None):
    """Discover services by capability."""
    services = list(service_registry.values())
    if capability:
        services = [s for s in services if capability in s.get("capabilities", [])]
    return services
