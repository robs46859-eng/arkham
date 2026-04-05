"""Tenant API key generation and verification."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime

from fastapi import HTTPException

from packages.db import get_record, list_records
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


def list_tenant_api_keys(db: object, tenant_id: str) -> list[TenantAPIKey]:
    return [
        record
        for record in list_records(db, TenantAPIKey)
        if isinstance(record, TenantAPIKey) and record.tenant_id == tenant_id
    ]


def verify_api_key(*, db: object, tenant_id: str, api_key: str) -> TenantAPIKey:
    tenant = get_record(db, Tenant, tenant_id)
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
