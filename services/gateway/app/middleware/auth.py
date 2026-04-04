"""
Tenant auth middleware — JWT Bearer verification.
Implements: Service Spec §1.2 — authenticate tenant requests.
             Master Architecture §3.2 — stateless token auth.

Primary path: Authorization: Bearer <JWT>
  → decode token → extract (tenant_id, project_id) → return to handler

Test/dev fallback: X-Tenant-Id + X-Project-Id headers (APP_ENV=test only)
  → validates format → returns (tenant_id, project_id)
  This fallback keeps all existing test fixtures working without modification.

Errors
------
  401  Missing credentials (no Bearer + no fallback headers in non-test env)
  401  Invalid or expired JWT
  401  JWT tenant_id / project_id format invalid
"""

from __future__ import annotations

import os
from typing import Optional

from fastapi import Header, HTTPException, Request

from ..auth.tokens import TokenError, verify_token
from ..settings import settings


def _is_test_env() -> bool:
    return os.environ.get("APP_ENV", "").lower() == "test"


async def require_tenant(
    request: Request,
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
    x_tenant_id: Optional[str] = Header(default=None, alias="X-Tenant-Id"),
    x_project_id: Optional[str] = Header(default=None, alias="X-Project-Id"),
) -> tuple[str, str]:
    """
    Authenticate the request and return (tenant_id, project_id).

    Accepts:
      1. Authorization: Bearer <JWT>   — primary path (all environments)
      2. X-Tenant-Id + X-Project-Id   — fallback (APP_ENV=test only)

    Raises HTTPException 401 on any auth failure.
    """
    # ── Primary path: JWT Bearer ──────────────────────────────────────────────
    if authorization and authorization.lower().startswith("bearer "):
        raw_token = authorization[7:].strip()
        try:
            payload = verify_token(raw_token, signing_key=settings.signing_key)
        except TokenError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc

        tenant_id = payload.get("sub", "")
        project_id = payload.get("proj", "")

        if not tenant_id.startswith("tenant_"):
            raise HTTPException(401, "Token sub claim is not a valid tenant_id.")

        return tenant_id, project_id

    # ── Test-mode fallback: plain headers ─────────────────────────────────────
    if _is_test_env() and x_tenant_id and x_project_id:
        if not x_tenant_id.startswith("tenant_"):
            raise HTTPException(401, "Invalid tenant_id format. Expected: tenant_<ulid>")
        if not x_project_id.startswith("proj_"):
            raise HTTPException(401, "Invalid project_id format. Expected: proj_<ulid>")
        return x_tenant_id, x_project_id

    # ── No valid credentials ──────────────────────────────────────────────────
    raise HTTPException(
        status_code=401,
        detail="Authentication required. Provide Authorization: Bearer <token>.",
        headers={"WWW-Authenticate": "Bearer"},
    )
