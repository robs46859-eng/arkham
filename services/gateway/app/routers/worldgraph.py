"""Worldgraph proxy routes mounted on the gateway."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException, Request, Response

from ..middleware.admin_auth import require_admin
from ..middleware.auth import require_tenant
from ..settings import settings

router = APIRouter(prefix="/v1/worldgraph", tags=["worldgraph"])


def _is_admin_path(path: str, method: str) -> bool:
    if method.upper() in {"POST", "PUT", "PATCH", "DELETE"}:
        if "/ingest/jobs" in path:
            return True
        if "/reindex" in path:
            return True
        if "/proposals/" in path:
            return True
        if path.endswith("/entities"):
            return True
    return False


@router.api_route(
    "/{namespace}/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def proxy_worldgraph(namespace: str, path: str, request: Request):
    full_path = f"/{namespace}/{path}" if path else f"/{namespace}"
    if _is_admin_path(full_path, request.method):
        await require_admin(
            authorization=request.headers.get("Authorization"),
            x_admin_token=request.headers.get("X-Admin-Token"),
        )
    else:
        await require_tenant(
            request=request,
            authorization=request.headers.get("Authorization"),
            x_tenant_id=request.headers.get("X-Tenant-Id"),
            x_project_id=request.headers.get("X-Project-Id"),
        )

    target_url = f"{settings.worldgraph_service_url}/v1/worldgraph/{namespace}"
    if path:
        target_url = f"{target_url}/{path}"
    if request.url.query:
        target_url = f"{target_url}?{request.url.query}"
    body = await request.body()
    headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in ("host", "connection", "transfer-encoding")
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            upstream = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body if body else None,
            )
    except httpx.ConnectError as exc:
        raise HTTPException(status_code=502, detail="Worldgraph service is unreachable") from exc
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="Worldgraph service timed out") from exc
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=dict(upstream.headers),
        media_type=upstream.headers.get("content-type"),
    )


@router.get("/{namespace}")
async def proxy_worldgraph_namespace(namespace: str, request: Request):
    return await proxy_worldgraph(namespace=namespace, path="", request=request)

