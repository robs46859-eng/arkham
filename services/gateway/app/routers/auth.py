"""
POST /v1/auth/token — JWT token issuance.
Implements: Service Spec §1.2 — stateless tenant authentication.

Request
-------
  { "tenant_id": "tenant_<ulid>", "api_key": "<key>", "project_id": "proj_<ulid>" }

Response
--------
  { "access_token": "eyJ...", "token_type": "bearer", "expires_in": 86400 }

API key validation
------------------
Uses tenant-scoped stored API keys.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from packages.db import get_db
from ..auth.api_keys import verify_api_key
from ..auth.tokens import DEFAULT_TTL_HOURS, issue_token
from ..settings import settings

router = APIRouter(prefix="/v1", tags=["auth"])

_TTL_SECONDS = DEFAULT_TTL_HOURS * 3600


class TokenRequest(BaseModel):
    tenant_id: str      # format: tenant_<ulid>
    api_key: str
    project_id: str = ""  # optional project scope


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int     # seconds


@router.post("/auth/token", response_model=TokenResponse)
def issue_access_token(request: TokenRequest, db: object = Depends(get_db)) -> TokenResponse:
    """
    Issue a JWT access token for a tenant.

    The returned token should be sent as `Authorization: Bearer <token>` on
    all subsequent API calls to the gateway.

    Validates a tenant-scoped API key before issuing a JWT.
    """
    if not request.tenant_id.startswith("tenant_"):
        raise HTTPException(400, "Invalid tenant_id format. Expected: tenant_<ulid>")
    if not request.api_key.strip():
        raise HTTPException(400, "api_key must not be empty")

    if request.project_id and not request.project_id.startswith("proj_"):
        raise HTTPException(400, "Invalid project_id format. Expected: proj_<ulid>")

    verify_api_key(db=db, tenant_id=request.tenant_id, api_key=request.api_key)

    token = issue_token(
        tenant_id=request.tenant_id,
        project_id=request.project_id,
        signing_key=settings.signing_key,
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=_TTL_SECONDS,
    )
