"""
Tenant management router.

STUB - NOT PRODUCTION READY
This implementation uses in-memory storage for testing purposes only.
Production implementation must use persistent database storage with proper transactions.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List
from datetime import datetime
import uuid

from packages.schemas.tenant import TenantCreate, TenantUpdate, TenantResponse
from tests.conftest import MockSession

router = APIRouter(prefix="/v1/tenants", tags=["tenants"])

# In-memory storage for testing - STUB
_tenants: dict[str, dict] = {}


def _get_session(request) -> MockSession:
    """Get mock session from request state."""
    return getattr(request.state, "db_session", None)


@router.post("", response_model=TenantResponse, status_code=201)
async def create_tenant(payload: TenantCreate):
    """
    Create a new tenant.

    STUB: Uses in-memory storage. Production must use database.
    """
    tenant_id = f"tenant_{uuid.uuid4().hex[:12]}"

    tenant_data = {
        "id": tenant_id,
        "tenant_id": tenant_id,
        "name": payload.name,
        "is_active": payload.is_active,
        "created_at": datetime.utcnow(),
    }

    _tenants[tenant_id] = tenant_data

    return TenantResponse(**tenant_data)


@router.get("", response_model=List[TenantResponse])
async def list_tenants(active_only: bool = Query(False)):
    """
    List all tenants.

    STUB: Returns from in-memory storage. Production must query database.
    """
    results = list(_tenants.values())

    if active_only:
        results = [t for t in results if t.get("is_active", True)]

    return [TenantResponse(**t) for t in results]


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(tenant_id: str):
    """
    Get a specific tenant by ID.

    STUB: Uses in-memory storage. Production must query database.
    """
    if tenant_id not in _tenants:
        raise HTTPException(status_code=404, detail="Tenant not found")

    return TenantResponse(**_tenants[tenant_id])


@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(tenant_id: str, payload: TenantUpdate):
    """
    Update a tenant.

    STUB: Uses in-memory storage. Production must use database transactions.
    """
    if tenant_id not in _tenants:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant_data = _tenants[tenant_id].copy()

    if payload.name is not None:
        tenant_data["name"] = payload.name
    if payload.is_active is not None:
        tenant_data["is_active"] = payload.is_active

    _tenants[tenant_id] = tenant_data

    return TenantResponse(**tenant_data)
