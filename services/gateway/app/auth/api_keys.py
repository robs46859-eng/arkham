"""Tenant API key generation and verification."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from fastapi import HTTPException

from packages.models import Tenant, TenantAPIKey


@dataclass
class IssuedAPIKey:
    record: TenantAPIKey
    plaintext: str


def _hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def issue_api_key(*, tenant_id: str) -> IssuedAPIKey:
    now = datetime.utcnow()
    key_prefix = f"rk_{secrets.token_hex(6)}"
    secret = secrets.token_urlsafe(24)
    record = TenantAPIKey(
        id=f"key_{uuid.uuid4().hex}",
        tenant_id=tenant_id,
        key_prefix=key_prefix,
        secret_hash=_hash_secret(secret),
        is_active=True,
        created_at=now,
        updated_at=now,
        last_used_at=None,
    )
    return IssuedAPIKey(record=record, plaintext=f"{key_prefix}.{secret}")


def _split_api_key(api_key: str) -> tuple[str, str]:
    prefix, separator, secret = api_key.partition(".")
    if not separator or not prefix or not secret:
        raise HTTPException(status_code=401, detail="Invalid API key format.")
    return prefix, secret


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


def list_tenant_api_keys(db: object, tenant_id: str) -> list[TenantAPIKey]:
    return [
        record
        for record in _list_records(db, TenantAPIKey)
        if isinstance(record, TenantAPIKey) and record.tenant_id == tenant_id
    ]


def verify_api_key(*, db: object, tenant_id: str, api_key: str) -> TenantAPIKey:
    tenant = _get_record(db, Tenant, tenant_id)
    if tenant is None or not isinstance(tenant, Tenant) or not tenant.is_active:
        raise HTTPException(status_code=403, detail="Tenant is inactive or missing.")

    key_prefix, secret = _split_api_key(api_key.strip())
    for record in list_tenant_api_keys(db, tenant_id):
        if record.key_prefix != key_prefix or not record.is_active:
            continue
        if hmac.compare_digest(record.secret_hash, _hash_secret(secret)):
            record.last_used_at = datetime.utcnow()
            record.updated_at = record.last_used_at
            if hasattr(db, "commit"):
                db.commit()
            return record

    raise HTTPException(status_code=401, detail="Invalid API key.")
