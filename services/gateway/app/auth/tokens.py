"""
JWT token issuance and verification.
Implements: Service Spec §1.2 — tenant authentication.
             Master Architecture §3.2 — stateless token auth.

Token format (HS256)
--------------------
{
  "sub":  "tenant_<ulid>",       # tenant_id
  "proj": "proj_<ulid>",         # project_id (empty string if omitted)
  "iat":  <unix_timestamp>,
  "exp":  <unix_timestamp>,      # iat + TTL
  "jti":  "<uuid>",              # nonce — unique per token
}

Design note
-----------
No module-level settings import — signing_key is passed explicitly by callers
(router and middleware read it from their local settings object). This keeps
the token library importable in isolation for unit testing without needing
a full settings environment.

Revocation
----------
STUB: jti-based revocation list (Redis SET with TTL) is the upgrade path.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import jwt

_ALGORITHM = "HS256"
DEFAULT_TTL_HOURS = 24


class TokenError(Exception):
    """Raised when a token cannot be decoded or fails validation."""


def issue_token(
    *,
    tenant_id: str,
    signing_key: str,
    project_id: str = "",
    ttl_hours: int = DEFAULT_TTL_HOURS,
) -> str:
    """
    Issue a signed JWT for the given tenant.

    Parameters
    ----------
    tenant_id:   Must start with "tenant_".
    signing_key: HMAC secret from service settings.
    project_id:  Optional project scope.
    ttl_hours:   Token lifetime. Default 24h.
    """
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": tenant_id,
        "proj": project_id,
        "iat": now,
        "exp": now + timedelta(hours=ttl_hours),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, signing_key, algorithm=_ALGORITHM)


def verify_token(token: str, *, signing_key: str) -> dict:
    """
    Decode and verify a JWT token.

    Returns the decoded payload dict on success.
    Raises TokenError for any failure (expired, tampered, wrong key, etc.).
    """
    try:
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=[_ALGORITHM],
            options={"require": ["sub", "exp", "iat", "jti"]},
        )
        return payload
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Token has expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError(f"Invalid token: {exc}") from exc
