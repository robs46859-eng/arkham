"""
Dynamic Vertical Proxy
Routes requests to verticals by looking up their endpoint in Core's registry.

Route pattern: /v1/verticals/{vertical_id}/{path}
The gateway proxies the request to the vertical's registered endpoint.
"""

import logging
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request, Response
from ..settings import settings

logger = logging.getLogger("gateway.verticals")

router = APIRouter(prefix="/v1/verticals", tags=["verticals"])

# Core service URL for registry lookups
CORE_SERVICE_URL = getattr(settings, "core_service_url", None) or "http://core:8000"

# Cache resolved endpoints to avoid hitting Core on every request.
# Cleared on gateway restart; TTL-based eviction could be added later.
_endpoint_cache: dict[str, str] = {}


async def _resolve_endpoint(vertical_id: str) -> str:
    """Look up a vertical's endpoint from Core's service registry."""
    if vertical_id in _endpoint_cache:
        return _endpoint_cache[vertical_id]

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{CORE_SERVICE_URL}/registry/services/{vertical_id}"
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
    except Exception:
        logger.error("Failed to resolve vertical %s", vertical_id, exc_info=True)
        raise HTTPException(
            status_code=502,
            detail="Unable to reach Core service registry",
        )


@router.api_route(
    "/{vertical_id}/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def proxy_to_vertical(vertical_id: str, path: str, request: Request):
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

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.request(
                method=request.method,
                url=target_url,
                content=body if body else None,
                headers=forward_headers,
            )
    except httpx.ConnectError:
        # Evict cached endpoint on connection failure
        _endpoint_cache.pop(vertical_id, None)
        raise HTTPException(
            status_code=502,
            detail=f"Vertical '{vertical_id}' is unreachable at {endpoint}",
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail=f"Vertical '{vertical_id}' timed out",
        )

    # Return the vertical's response transparently
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=dict(resp.headers),
        media_type=resp.headers.get("content-type"),
    )


@router.get("/{vertical_id}")
async def vertical_root(vertical_id: str, request: Request):
    """Proxy root-level requests to a vertical."""
    return await proxy_to_vertical(vertical_id, "", request)


@router.post("/cache/clear")
async def clear_endpoint_cache():
    """Clear the endpoint resolution cache (admin utility)."""
    count = len(_endpoint_cache)
    _endpoint_cache.clear()
    return {"status": "cleared", "evicted": count}
