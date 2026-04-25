"""Tenant admin endpoints used by the admin dashboard."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import Header

from packages.db import get_db
from packages.models import Tenant, TenantAPIKey
from packages.schemas import (
    TenantActorPermissionSummary,
    TenantActorRoleResponse,
    TenantActorRoleUpsert,
    TenantAPIKeyCreateResponse,
    TenantAPIKeyResponse,
    TenantCreate,
    TenantResponse,
    TenantUpdate,
)
from ..auth.api_keys import issue_api_key, list_tenant_api_keys
from ..authz import TENANT_MEMBERS_MANAGE, ensure_actor_role_table, require_actor_permission, resolve_actor_access
from ..middleware.admin_auth import require_admin

router = APIRouter(prefix="/v1/tenants", tags=["tenants"], dependencies=[Depends(require_admin)])

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
        entitlements=getattr(tenant, "entitlements", {}) or {},
        stripe_customer_id=getattr(tenant, "stripe_customer_id", None),
        stripe_subscription_id=getattr(tenant, "stripe_subscription_id", None),
        stripe_price_id=getattr(tenant, "stripe_price_id", None),
        subscription_status=getattr(tenant, "subscription_status", "inactive"),
        subscription_current_period_end=getattr(tenant, "subscription_current_period_end", None),
        subscription_cancel_at_period_end=getattr(tenant, "subscription_cancel_at_period_end", False),
        created_at=tenant.created_at,
        updated_at=getattr(tenant, "updated_at", tenant.created_at),
    )


def _get_record(db: Any, model: type[Any], record_id: str) -> Any | None:
    if hasattr(db, "get"):
        return db.get(model, record_id)
    if hasattr(db, "query"):
        return db.query(model).filter_by(id=record_id).first()
    raise HTTPException(status_code=500, detail="Database session does not support record lookup.")


def _list_records(db: Any, model: type[Any]) -> list[Any]:
    if hasattr(db, "_objects"):
        return [record for record in db._objects.values() if isinstance(record, model)]
    if hasattr(db, "query"):
        return list(db.query(model).all())
    raise HTTPException(status_code=500, detail="Database session does not support record listing.")


def create_tenant_record(request: TenantCreate, db: object) -> TenantResponse:
    now = datetime.utcnow()
    tenant = Tenant(
        id=f"tenant_{uuid.uuid4().hex}",
        name=request.name.strip(),
        is_active=request.is_active,
        created_at=now,
    )
    tenant.updated_at = now
    tenant.plan = getattr(request, "plan", "free")
    tenant.enable_premium_escalation = getattr(request, "enable_premium_escalation", False)
    tenant.enable_semantic_cache = getattr(request, "enable_semantic_cache", False)
    tenant.cache_similarity_threshold = 0.92
    tenant.max_requests_per_day = None
    tenant.entitlements = {}
    tenant.subscription_status = "inactive"
    tenant.subscription_cancel_at_period_end = False
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


def _actor_role_response(record, permissions: set[str], source: str) -> TenantActorRoleResponse:
    return TenantActorRoleResponse(
        membership_id=record.id,
        tenant_id=record.tenant_id,
        actor_id=record.actor_id,
        display_name=record.display_name,
        role=record.role,
        permissions=sorted(permissions),
        granted_permissions=list(record.granted_permissions or []),
        denied_permissions=list(record.denied_permissions or []),
        is_active=record.is_active,
        source=source,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.get("", response_model=list[TenantResponse])
def list_tenants(
    active_only: bool = Query(default=False),
    db: object = Depends(get_db),
) -> list[TenantResponse]:
    tenants = [
        tenant
        for tenant in _list_records(db, Tenant)
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
    tenant = _get_record(db, Tenant, tenant_id)
    if tenant is None or not isinstance(tenant, Tenant):
        raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")
    return _tenant_to_response(tenant)


@router.patch("/{tenant_id}", response_model=TenantResponse)
def update_tenant(
    tenant_id: str,
    request: TenantUpdate,
    db: object = Depends(get_db),
) -> TenantResponse:
    tenant = _get_record(db, Tenant, tenant_id)
    if tenant is None or not isinstance(tenant, Tenant):
        raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")

    updates = request.model_dump(exclude_unset=True)

    for field, value in updates.items():
        setattr(tenant, field, value)

    tenant.updated_at = datetime.utcnow()

    if hasattr(db, "commit"):
        db.commit()
    return _tenant_to_response(tenant)


@router.get("/{tenant_id}/api-keys", response_model=list[TenantAPIKeyResponse])
def list_api_keys(tenant_id: str, db: object = Depends(get_db)) -> list[TenantAPIKeyResponse]:
    tenant = _get_record(db, Tenant, tenant_id)
    if tenant is None or not isinstance(tenant, Tenant):
        raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")
    return [_api_key_to_response(record) for record in list_tenant_api_keys(db, tenant_id)]


@router.post("/{tenant_id}/api-keys", response_model=TenantAPIKeyCreateResponse)
def create_api_key(tenant_id: str, db: object = Depends(get_db)) -> TenantAPIKeyCreateResponse:
    tenant = _get_record(db, Tenant, tenant_id)
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


@router.get("/{tenant_id}/actors", response_model=list[TenantActorRoleResponse])
def list_tenant_actor_roles(
    tenant_id: str,
    _: None = Depends(require_admin),
    x_admin_actor: str | None = Header(default=None, alias="X-Admin-Actor"),
    db: object = Depends(get_db),
) -> list[TenantActorRoleResponse]:
    tenant = _get_record(db, Tenant, tenant_id)
    if tenant is None or not isinstance(tenant, Tenant):
        raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")
    require_actor_permission(db, tenant_id, x_admin_actor, TENANT_MEMBERS_MANAGE)
    ensure_actor_role_table(db)
    from packages.models import TenantActorRoleRecord
    roles = [
        record
        for record in _list_records(db, TenantActorRoleRecord)
        if isinstance(record, TenantActorRoleRecord) and record.tenant_id == tenant_id
    ]
    responses = []
    for record in sorted(roles, key=lambda item: item.created_at, reverse=True):
        access = resolve_actor_access(db, tenant_id, record.actor_id)
        responses.append(_actor_role_response(record, access.permissions, access.source))
    return responses


@router.get("/{tenant_id}/actors/me", response_model=TenantActorPermissionSummary)
def get_current_actor_permissions(
    tenant_id: str,
    _: None = Depends(require_admin),
    x_admin_actor: str | None = Header(default=None, alias="X-Admin-Actor"),
    db: object = Depends(get_db),
) -> TenantActorPermissionSummary:
    tenant = _get_record(db, Tenant, tenant_id)
    if tenant is None or not isinstance(tenant, Tenant):
        raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")
    ensure_actor_role_table(db)
    access = resolve_actor_access(db, tenant_id, x_admin_actor)
    return TenantActorPermissionSummary(
        tenant_id=tenant_id,
        actor_id=access.actor_id,
        role=access.role,
        permissions=sorted(access.permissions),
        source=access.source,
    )


@router.put("/{tenant_id}/actors/{actor_id}", response_model=TenantActorRoleResponse)
def upsert_tenant_actor_role(
    tenant_id: str,
    actor_id: str,
    request: TenantActorRoleUpsert,
    _: None = Depends(require_admin),
    x_admin_actor: str | None = Header(default=None, alias="X-Admin-Actor"),
    db: object = Depends(get_db),
) -> TenantActorRoleResponse:
    tenant = _get_record(db, Tenant, tenant_id)
    if tenant is None or not isinstance(tenant, Tenant):
        raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")
    require_actor_permission(db, tenant_id, x_admin_actor, TENANT_MEMBERS_MANAGE)
    if actor_id.strip().lower() != request.actor_id.strip().lower():
        raise HTTPException(status_code=400, detail="Actor ID in path must match actor_id in body.")
    from ..authz import upsert_actor_role

    record = upsert_actor_role(
        db,
        tenant_id=tenant_id,
        actor_id=request.actor_id,
        display_name=request.display_name,
        role=request.role,
        granted_permissions=request.granted_permissions,
        denied_permissions=request.denied_permissions,
        is_active=request.is_active,
    )
    access = resolve_actor_access(db, tenant_id, record.actor_id)
    return _actor_role_response(record, access.permissions, access.source)
