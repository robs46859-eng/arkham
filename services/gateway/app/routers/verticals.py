"""
Dynamic Vertical Proxy
Routes requests to verticals by looking up their endpoint in Core's registry.

Route pattern: /v1/verticals/{vertical_id}/{path}
The gateway proxies the request to the vertical's registered endpoint.
"""

import logging
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from packages.db import get_db
from packages.models import Tenant

from ..middleware.auth import require_tenant
from ..settings import settings

logger = logging.getLogger("gateway.verticals")

router = APIRouter(prefix="/v1/verticals", tags=["verticals"])

# Cache resolved endpoints to avoid hitting Core on every request.
# Cleared on gateway restart; TTL-based eviction could be added later.
_endpoint_cache: dict[str, str] = {}


def _tenant_has_vertical_access(db: Any, tenant_id: str, vertical_id: str) -> bool:
    tenant = None
    if hasattr(db, "get"):
        tenant = db.get(Tenant, tenant_id)
    if tenant is None and hasattr(db, "query"):
        tenant = db.query(Tenant).filter_by(id=tenant_id).first()

    if tenant is None or not isinstance(tenant, Tenant) or not tenant.is_active:
        return False

    entitlements = getattr(tenant, "entitlements", {}) or {}
    verticals = entitlements.get("verticals", [])
    return "*" in verticals or vertical_id in verticals


def _require_vertical_access(db: Any, tenant_id: str, vertical_id: str) -> None:
    if not _tenant_has_vertical_access(db, tenant_id, vertical_id):
        raise HTTPException(
            status_code=403,
            detail=f"Tenant does not have access to vertical '{vertical_id}'",
        )


async def _resolve_endpoint(vertical_id: str) -> str:
    """Look up a vertical's endpoint from Core's service registry."""
    if vertical_id in _endpoint_cache:
        return _endpoint_cache[vertical_id]

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{settings.core_service_url}/services/{vertical_id}"
            )
            if resp.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail=f"Vertical '{vertical_id}' is not registered",
                )
            resp.raise_for_status()
            data = resp.json()
            endpoint = data.get("endpoint", "")
            if not endpoint:
                raise HTTPException(
                    status_code=502,
                    detail=f"Vertical '{vertical_id}' has no endpoint configured",
                )
            _endpoint_cache[vertical_id] = endpoint
            return endpoint
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to resolve vertical %s", vertical_id)
        raise HTTPException(
            status_code=502,
            detail="Unable to reach Core service registry",
        ) from exc


@router.api_route(
    "/{vertical_id}/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def proxy_to_vertical(
    vertical_id: str,
    path: str,
    request: Request,
    auth: tuple[str, str] = Depends(require_tenant),
    db: object = Depends(get_db),
):
    """Proxy any authorized request to the resolved vertical endpoint."""
    tenant_id, _ = auth
    _require_vertical_access(db, tenant_id, vertical_id)
    return await _proxy_to_vertical(vertical_id, path, request, tenant_id)


async def _proxy_to_vertical(vertical_id: str, path: str, request: Request, tenant_id: str | None = None):
    """Proxy any request to the resolved vertical endpoint."""
    endpoint = await _resolve_endpoint(vertical_id)
    target_url = f"{endpoint}/{path}"

    # Forward query params
    if request.url.query:
        target_url = f"{target_url}?{request.url.query}"

    # Read body (empty for GET/DELETE)
    body = await request.body()

    # Forward relevant headers (strip hop-by-hop)
    forward_headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in ("host", "connection", "transfer-encoding")
    }

    # Inject tenant context
    if tenant_id:
        forward_headers["X-Tenant-ID"] = tenant_id

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.request(
                method=request.method,
                url=target_url,
                content=body if body else None,
                headers=forward_headers,
            )
    except httpx.ConnectError as exc:
        # Evict cached endpoint on connection failure
        _endpoint_cache.pop(vertical_id, None)
        raise HTTPException(
            status_code=502,
            detail=f"Vertical '{vertical_id}' is unreachable at {endpoint}",
        ) from exc
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=504,
            detail=f"Vertical '{vertical_id}' timed out",
        ) from exc

    # Return the vertical's response transparently
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=dict(resp.headers),
        media_type=resp.headers.get("content-type"),
    )


@router.get("/{vertical_id}")
async def vertical_root(
    vertical_id: str,
    request: Request,
    auth: tuple[str, str] = Depends(require_tenant),
    db: object = Depends(get_db),
):
    """Proxy root-level requests to a vertical."""
    tenant_id, _ = auth
    _require_vertical_access(db, tenant_id, vertical_id)
    return await _proxy_to_vertical(vertical_id, "", request, tenant_id)


@router.post("/cache/clear")
async def clear_endpoint_cache():
    """Clear the endpoint resolution cache (admin utility)."""
    count = len(_endpoint_cache)
    _endpoint_cache.clear()
    return {"status": "cleared", "evicted": count}
