"""
Tenant JWT auth dependency for the billing service.
Mirrors gateway/app/middleware/auth.py — same token format, same signing key.
"""

from __future__ import annotations

import os
from typing import Optional

import jwt
from fastapi import Header, HTTPException

from .settings import settings

_ALGORITHM = "HS256"


def _is_test_env() -> bool:
    return os.environ.get("APP_ENV", "").lower() == "test"


async def require_tenant(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
    x_tenant_id: Optional[str] = Header(default=None, alias="X-Tenant-Id"),
    x_project_id: Optional[str] = Header(default=None, alias="X-Project-Id"),
) -> tuple[str, str]:
    """Return (tenant_id, project_id) from a verified JWT or test headers."""

    if authorization and authorization.lower().startswith("bearer "):
        raw_token = authorization[7:].strip()
        try:
            payload = jwt.decode(
                raw_token,
                settings.signing_key,
                algorithms=[_ALGORITHM],
                options={"require": ["sub", "exp", "iat", "jti"]},
            )
        except jwt.ExpiredSignatureError as exc:
            raise HTTPException(status_code=401, detail="Token has expired.") from exc
        except jwt.InvalidTokenError as exc:
            raise HTTPException(status_code=401, detail=f"Invalid token: {exc}") from exc

        tenant_id = payload.get("sub", "")
        if not tenant_id.startswith("tenant_"):
            raise HTTPException(401, "Token sub claim is not a valid tenant_id.")
        return tenant_id, payload.get("proj", "")

    if _is_test_env() and x_tenant_id and x_project_id:
        if not x_tenant_id.startswith("tenant_"):
            raise HTTPException(401, "Invalid tenant_id format.")
        return x_tenant_id, x_project_id

    raise HTTPException(
        status_code=401,
        detail="Authentication required. Provide Authorization: Bearer <token>.",
        headers={"WWW-Authenticate": "Bearer"},
    )
