"""
Tenant auth middleware — initial implementation (contract-aligned stub).
Implements: Service Spec §1.2 — authenticate tenant requests.
STUB: currently validates header presence only. Full JWT/API-key verification
is the next auth implementation step.
"""

from fastapi import Header, HTTPException


def require_tenant(
    x_tenant_id: str = Header(..., alias="X-Tenant-Id"),
    x_project_id: str = Header(..., alias="X-Project-Id"),
) -> tuple[str, str]:
    """
    Extract and validate tenant and project IDs from request headers.
    Returns (tenant_id, project_id).
    STUB: add signature verification against signing_key from settings.
    """
    if not x_tenant_id.startswith("tenant_"):
        raise HTTPException(status_code=401, detail="Invalid tenant_id format. Expected: tenant_<ulid>")
    if not x_project_id.startswith("proj_"):
        raise HTTPException(status_code=401, detail="Invalid project_id format. Expected: proj_<ulid>")
    return x_tenant_id, x_project_id
