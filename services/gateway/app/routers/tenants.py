"""Tenant admin endpoints used by the admin dashboard."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from packages.db import get_db, get_record, list_records
from packages.models import Tenant, TenantAPIKey
from packages.schemas import (
    TenantAPIKeyCreateResponse,
    TenantAPIKeyResponse,
    TenantCreate,
    TenantResponse,
    TenantUpdate,
)
from ..auth.api_keys import issue_api_key, list_tenant_api_keys

router = APIRouter(prefix="/v1/tenants", tags=["tenants"])

_PLAN_LIMITS: dict[str, int | None] = {
    "free": 1000,
    "pro": 10000,
    "enterprise": None,
}


def _tenant_to_response(tenant: Tenant) -> TenantResponse:
    return TenantResponse(
        tenant_id=tenant.id,
        name=tenant.name,
        plan=getattr(tenant, "plan", "free"),
        is_active=tenant.is_active,
        enable_premium_escalation=getattr(tenant, "enable_premium_escalation", False),
        enable_semantic_cache=getattr(tenant, "enable_semantic_cache", False),
        cache_similarity_threshold=getattr(tenant, "cache_similarity_threshold", 0.92),
        max_requests_per_day=getattr(tenant, "max_requests_per_day", None),
        created_at=tenant.created_at,
        updated_at=getattr(tenant, "updated_at", tenant.created_at),
    )


def create_tenant_record(request: TenantCreate, db: object) -> TenantResponse:
    if request.plan not in _PLAN_LIMITS:
        raise HTTPException(status_code=400, detail="Invalid plan. Expected free, pro, or enterprise.")

    now = datetime.utcnow()
    tenant = Tenant(
        id=f"tenant_{uuid.uuid4().hex}",
        name=request.name.strip(),
        plan=request.plan,
        is_active=True,
        enable_premium_escalation=request.enable_premium_escalation,
        enable_semantic_cache=request.enable_semantic_cache,
        cache_similarity_threshold=0.92,
        max_requests_per_day=_PLAN_LIMITS[request.plan],
        created_at=now,
        updated_at=now,
    )
    db.add(tenant)
    if hasattr(db, "commit"):
        db.commit()
    return _tenant_to_response(tenant)


def _api_key_to_response(record: TenantAPIKey) -> TenantAPIKeyResponse:
    return TenantAPIKeyResponse(
        api_key_id=record.id,
        tenant_id=record.tenant_id,
        key_prefix=record.key_prefix,
        is_active=record.is_active,
        created_at=record.created_at,
        updated_at=record.updated_at,
        last_used_at=record.last_used_at,
    )


@router.get("", response_model=list[TenantResponse])
def list_tenants(
    active_only: bool = Query(default=False),
    db: object = Depends(get_db),
) -> list[TenantResponse]:
    tenants = [
        tenant
        for tenant in list_records(db, Tenant)
        if isinstance(tenant, Tenant) and (tenant.is_active or not active_only)
    ]
    tenants.sort(key=lambda tenant: tenant.created_at, reverse=True)
    return [_tenant_to_response(tenant) for tenant in tenants]


@router.post("", response_model=TenantResponse)
def create_tenant(
    request: TenantCreate,
    db: object = Depends(get_db),
) -> TenantResponse:
    return create_tenant_record(request, db)


@router.get("/{tenant_id}", response_model=TenantResponse)
def get_tenant(tenant_id: str, db: object = Depends(get_db)) -> TenantResponse:
    tenant = get_record(db, Tenant, tenant_id)
    if tenant is None or not isinstance(tenant, Tenant):
        raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")
    return _tenant_to_response(tenant)


@router.patch("/{tenant_id}", response_model=TenantResponse)
def update_tenant(
    tenant_id: str,
    request: TenantUpdate,
    db: object = Depends(get_db),
) -> TenantResponse:
    tenant = get_record(db, Tenant, tenant_id)
    if tenant is None or not isinstance(tenant, Tenant):
        raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")

    updates = request.model_dump(exclude_unset=True)
    if "plan" in updates and updates["plan"] not in _PLAN_LIMITS:
        raise HTTPException(status_code=400, detail="Invalid plan. Expected free, pro, or enterprise.")

    for field, value in updates.items():
        setattr(tenant, field, value)

    if "plan" in updates and "max_requests_per_day" not in updates:
        tenant.max_requests_per_day = _PLAN_LIMITS[tenant.plan]
    tenant.updated_at = datetime.utcnow()

    if hasattr(db, "commit"):
        db.commit()
    return _tenant_to_response(tenant)


@router.get("/{tenant_id}/api-keys", response_model=list[TenantAPIKeyResponse])
def list_api_keys(tenant_id: str, db: object = Depends(get_db)) -> list[TenantAPIKeyResponse]:
    tenant = get_record(db, Tenant, tenant_id)
    if tenant is None or not isinstance(tenant, Tenant):
        raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")
    return [_api_key_to_response(record) for record in list_tenant_api_keys(db, tenant_id)]


@router.post("/{tenant_id}/api-keys", response_model=TenantAPIKeyCreateResponse)
def create_api_key(tenant_id: str, db: object = Depends(get_db)) -> TenantAPIKeyCreateResponse:
    tenant = get_record(db, Tenant, tenant_id)
    if tenant is None or not isinstance(tenant, Tenant):
        raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")

    issued = issue_api_key(tenant_id=tenant_id)
    db.add(issued.record)
    if hasattr(db, "commit"):
        db.commit()

    return TenantAPIKeyCreateResponse(
        api_key_id=issued.record.id,
        tenant_id=issued.record.tenant_id,
        key_prefix=issued.record.key_prefix,
        api_key=issued.plaintext,
        created_at=issued.record.created_at,
    )
