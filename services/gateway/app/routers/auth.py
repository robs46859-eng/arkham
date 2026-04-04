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
STUB: currently accepts any non-empty api_key string.
Real implementation: look up hashed api_key in a tenant_api_keys table,
verify bcrypt hash, enforce key rotation policy.

Rate limiting
-------------
STUB: add Redis-backed rate limiter (e.g. 10 token requests/minute/tenant_id).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..auth.tokens import DEFAULT_TTL_HOURS, issue_token
from ..settings import settings

router = APIRouter(prefix="/v1", tags=["auth"])

_TTL_SECONDS = DEFAULT_TTL_HOURS * 3600


class TokenRequest(BaseModel):
    tenant_id: str      # format: tenant_<ulid>
    api_key: str        # STUB: any non-empty value accepted
    project_id: str = ""  # optional project scope


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int     # seconds


@router.post("/auth/token", response_model=TokenResponse)
def issue_access_token(request: TokenRequest) -> TokenResponse:
    """
    Issue a JWT access token for a tenant.

    The returned token should be sent as `Authorization: Bearer <token>` on
    all subsequent API calls to the gateway.

    STUB: api_key validation is bypassed — real key lookup is next sprint.
    """
    if not request.tenant_id.startswith("tenant_"):
        raise HTTPException(400, "Invalid tenant_id format. Expected: tenant_<ulid>")
    if not request.api_key.strip():
        raise HTTPException(400, "api_key must not be empty")

    if request.project_id and not request.project_id.startswith("proj_"):
        raise HTTPException(400, "Invalid project_id format. Expected: proj_<ulid>")

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
