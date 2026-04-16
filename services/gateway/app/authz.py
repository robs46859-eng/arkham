"""Tenant-scoped actor roles and permission resolution."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from fastapi import HTTPException

from packages.models import TenantActorRoleRecord

ROLE_OWNER = "owner"
ROLE_ADMIN = "admin"
ROLE_REVIEWER = "reviewer"
ROLE_OPERATOR = "operator"
ROLE_VIEWER = "viewer"

WORKFLOW_VIEW = "workflow.view"
WORKFLOW_REVIEW = "workflow.review"
WORKFLOW_EXECUTE = "workflow.execute"
WORKFLOW_DELIVER = "workflow.deliver"
WORKFLOW_POLICY = "workflow.policy"
TENANT_MEMBERS_MANAGE = "tenant.members.manage"

ROLE_PERMISSION_MAP: dict[str, set[str]] = {
    ROLE_OWNER: {
        WORKFLOW_VIEW,
        WORKFLOW_REVIEW,
        WORKFLOW_EXECUTE,
        WORKFLOW_DELIVER,
        WORKFLOW_POLICY,
        TENANT_MEMBERS_MANAGE,
    },
    ROLE_ADMIN: {
        WORKFLOW_VIEW,
        WORKFLOW_REVIEW,
        WORKFLOW_EXECUTE,
        WORKFLOW_DELIVER,
        WORKFLOW_POLICY,
        TENANT_MEMBERS_MANAGE,
    },
    ROLE_REVIEWER: {WORKFLOW_VIEW, WORKFLOW_REVIEW},
    ROLE_OPERATOR: {WORKFLOW_VIEW, WORKFLOW_EXECUTE, WORKFLOW_DELIVER},
    ROLE_VIEWER: {WORKFLOW_VIEW},
}


@dataclass
class ActorAccess:
    tenant_id: str
    actor_id: str
    role: str
    permissions: set[str]
    source: str
    membership: TenantActorRoleRecord | None = None


def normalize_actor_id(actor_id: str | None) -> str:
    return (actor_id or "").strip().lower()


def _list_actor_roles(db: Any, tenant_id: str) -> list[TenantActorRoleRecord]:
    if hasattr(db, "_objects"):
        return [
            record
            for record in db._objects.values()
            if isinstance(record, TenantActorRoleRecord) and record.tenant_id == tenant_id
        ]
    if hasattr(db, "query"):
        return list(db.query(TenantActorRoleRecord).filter_by(tenant_id=tenant_id).all())
    raise HTTPException(status_code=500, detail="Database session does not support actor role listing.")


def ensure_actor_role_table(db: Any) -> None:
    bind = getattr(db, "bind", None)
    if bind is None:
        return
    TenantActorRoleRecord.__table__.create(bind=bind, checkfirst=True)


def resolve_actor_access(db: Any, tenant_id: str, actor_id: str | None) -> ActorAccess:
    assignments = [record for record in _list_actor_roles(db, tenant_id) if record.is_active]
    normalized_actor = normalize_actor_id(actor_id)

    if not assignments:
        bootstrap_actor = normalized_actor or "admin"
        return ActorAccess(
            tenant_id=tenant_id,
            actor_id=bootstrap_actor,
            role=ROLE_OWNER,
            permissions=set(ROLE_PERMISSION_MAP[ROLE_OWNER]),
            source="bootstrap",
        )

    if not normalized_actor:
        raise HTTPException(status_code=400, detail="X-Admin-Actor is required when tenant roles are configured.")

    membership = next((record for record in assignments if normalize_actor_id(record.actor_id) == normalized_actor), None)
    if membership is None:
        raise HTTPException(status_code=403, detail=f"Actor {normalized_actor} does not have tenant access.")

    role = membership.role.strip().lower()
    if role not in ROLE_PERMISSION_MAP:
        raise HTTPException(status_code=500, detail=f"Unknown role configured for actor {normalized_actor}: {role}")

    permissions = set(ROLE_PERMISSION_MAP[role])
    permissions.update(permission.strip() for permission in (membership.granted_permissions or []) if permission)
    permissions.difference_update(permission.strip() for permission in (membership.denied_permissions or []) if permission)
    return ActorAccess(
        tenant_id=tenant_id,
        actor_id=normalized_actor,
        role=role,
        permissions=permissions,
        source="assigned",
        membership=membership,
    )


def require_actor_permission(db: Any, tenant_id: str, actor_id: str | None, permission: str) -> ActorAccess:
    access = resolve_actor_access(db, tenant_id, actor_id)
    if permission not in access.permissions:
        raise HTTPException(
            status_code=403,
            detail=f"Actor {access.actor_id} does not have permission {permission} for tenant {tenant_id}.",
        )
    return access


def upsert_actor_role(
    db: Any,
    *,
    tenant_id: str,
    actor_id: str,
    display_name: str | None,
    role: str,
    granted_permissions: list[str],
    denied_permissions: list[str],
    is_active: bool,
) -> TenantActorRoleRecord:
    ensure_actor_role_table(db)
    normalized_actor = normalize_actor_id(actor_id)
    normalized_role = role.strip().lower()
    if normalized_role not in ROLE_PERMISSION_MAP:
        raise HTTPException(status_code=400, detail=f"Unknown role: {role}")

    now = datetime.utcnow()
    existing = next(
        (record for record in _list_actor_roles(db, tenant_id) if normalize_actor_id(record.actor_id) == normalized_actor),
        None,
    )
    if existing is None:
        existing = TenantActorRoleRecord(
            id=f"trole_{uuid.uuid4().hex}",
            tenant_id=tenant_id,
            actor_id=normalized_actor,
            display_name=display_name,
            role=normalized_role,
            granted_permissions=list(dict.fromkeys(granted_permissions)),
            denied_permissions=list(dict.fromkeys(denied_permissions)),
            is_active=is_active,
            created_at=now,
            updated_at=now,
        )
        db.add(existing)
    else:
        existing.display_name = display_name
        existing.role = normalized_role
        existing.granted_permissions = list(dict.fromkeys(granted_permissions))
        existing.denied_permissions = list(dict.fromkeys(denied_permissions))
        existing.is_active = is_active
        existing.updated_at = now
    if hasattr(db, "commit"):
        db.commit()
    return existing
