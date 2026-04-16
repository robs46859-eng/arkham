"""
Admin authentication dependency.
Implements: Build Rules — protect tenant admin routes before broader exposure.

Usage
-----
  from ..middleware.admin_auth import require_admin

  @router.get("/v1/tenants")
  def list_tenants(_: None = Depends(require_admin), ...):
      ...

Token transport
---------------
  Authorization: Bearer <admin_token>   — primary path
  X-Admin-Token: <admin_token>          — fallback (APP_ENV=test only)

Errors
------
  401  Missing credentials
  403  Token present but does not match ADMIN_TOKEN secret
"""

from __future__ import annotations

import hmac
import os
from typing import Optional

from fastapi import Header, HTTPException

from ..settings import settings


def _is_test_env() -> bool:
    return os.environ.get("APP_ENV", "").lower() == "test"


def _constant_time_eq(a: str, b: str) -> bool:
    """Timing-safe string comparison to prevent timing attacks."""
    return hmac.compare_digest(a.encode(), b.encode())


async def require_admin(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
    x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
) -> None:
    """
    Verify the request carries a valid admin token.

    Raises 401 if no credentials are present.
    Raises 403 if credentials are present but invalid.
    """
    expected = settings.effective_admin_token

    # ── Primary path: Authorization: Bearer <admin_token> ─────────────────────
    if authorization and authorization.lower().startswith("bearer "):
        provided = authorization[7:].strip()
        if not _constant_time_eq(provided, expected):
            raise HTTPException(status_code=403, detail="Invalid admin token.")
        return

    # ── Test-mode fallback: X-Admin-Token header ──────────────────────────────
    if _is_test_env() and x_admin_token:
        if not _constant_time_eq(x_admin_token, expected):
            raise HTTPException(status_code=403, detail="Invalid admin token.")
        return

    # ── No credentials ────────────────────────────────────────────────────────
    raise HTTPException(
        status_code=401,
        detail="Admin authentication required. Provide Authorization: Bearer <admin_token>.",
        headers={"WWW-Authenticate": "Bearer"},
    )
