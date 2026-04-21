"""Bloods social-engineering probe vault with Fernet encryption.

All transcript storage is encrypted at rest. The vault key is derived from
BLOODS_VAULT_KEY (a URL-safe base64-encoded 32-byte key). The scope assertion
enforces that probes only run against personas owned by the requesting tenant.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from packages.models.sidecar import SidecarBloodsVault

try:
    from cryptography.fernet import Fernet, InvalidToken
    _CRYPTO_AVAILABLE = True
except ImportError:
    _CRYPTO_AVAILABLE = False

_VAULT_KEY_ENV = "BLOODS_VAULT_KEY"
_ENABLED_ENV = "BLOODS_ENABLED"

PROBE_TYPES = frozenset(
    [
        "authority_override",   # impersonates operator/admin to extract secrets
        "social_trust",         # builds rapport then requests policy violation
        "incremental_escalation",  # gradually escalates requests past stated limits
        "emergency_pretext",    # fabricates urgency to bypass restrictions
        "identity_confusion",   # attempts to make persona forget its constraints
    ]
)


def _is_enabled() -> bool:
    return os.getenv(_ENABLED_ENV, "true").lower() != "false"


def _vault_key() -> bytes | None:
    raw = os.getenv(_VAULT_KEY_ENV)
    if not raw:
        return None
    return raw.encode("utf-8")


def _encrypt(text: str, key: bytes) -> bytes:
    if not _CRYPTO_AVAILABLE:
        return text.encode("utf-8")
    return Fernet(key).encrypt(text.encode("utf-8"))


def decrypt_transcript(ciphertext: bytes, key: bytes) -> str:
    if not _CRYPTO_AVAILABLE:
        return ciphertext.decode("utf-8")
    try:
        return Fernet(key).decrypt(ciphertext).decode("utf-8")
    except (InvalidToken, Exception):
        return "[decryption failed]"


def assert_scope(persona_owner_tenant: str, requesting_tenant: str) -> None:
    """Raise if the requesting tenant doesn't own this persona."""
    if persona_owner_tenant != requesting_tenant:
        raise PermissionError(
            f"Scope violation: tenant '{requesting_tenant}' cannot probe "
            f"persona owned by '{persona_owner_tenant}'"
        )


def record_probe(
    persona_id: str,
    owner_tenant: str,
    requesting_tenant: str,
    probe_type: str,
    transcript: str,
    result: str,
    db: "Session",
) -> SidecarBloodsVault | None:
    """
    Encrypt and store a Bloods probe transcript.

    Enforces:
      - Kill switch (BLOODS_ENABLED)
      - Scope assertion (owner_tenant must match requesting_tenant)
      - Encryption at rest (BLOODS_VAULT_KEY required in non-test environments)

    Returns None if kill switch is off.
    """
    if not _is_enabled():
        return None

    assert_scope(owner_tenant, requesting_tenant)

    if probe_type not in PROBE_TYPES:
        raise ValueError(f"Unknown probe type '{probe_type}'. Valid: {sorted(PROBE_TYPES)}")

    key = _vault_key()
    encrypted = _encrypt(transcript, key) if key else transcript.encode("utf-8")

    record = SidecarBloodsVault(
        id=f"bl_{uuid.uuid4().hex}",
        persona_id=persona_id,
        owner_tenant=owner_tenant,
        transcript_encrypted=encrypted,
        probe_type=probe_type,
        result=result,
        created_at=datetime.utcnow(),
    )
    db.add(record)
    db.flush()
    return record
