"""Internal service client for privacy-core sanitize/restore operations."""

from __future__ import annotations

from typing import Any

import httpx


class PrivacyServiceError(RuntimeError):
    """Raised when the privacy service call fails in fail-closed mode."""


async def _post_json(base_url: str, path: str, payload: dict[str, Any], service_token: str) -> dict[str, Any]:
    async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
        response = await client.post(
            path,
            json=payload,
            headers={"X-Internal-Service-Token": service_token},
        )
        response.raise_for_status()
        return response.json()


async def sanitize_text(
    *,
    base_url: str,
    service_token: str,
    tenant_id: str,
    tier: str,
    request_id: str,
    text: str,
) -> dict[str, Any]:
    return await _post_json(
        base_url,
        "/v1/internal/privacy/sanitize",
        {
            "tenantId": tenant_id,
            "tier": tier,
            "requestId": request_id,
            "text": text,
        },
        service_token,
    )


async def restore_text(
    *,
    base_url: str,
    service_token: str,
    tenant_id: str,
    tier: str,
    request_id: str,
    text: str,
) -> dict[str, Any]:
    return await _post_json(
        base_url,
        "/v1/internal/privacy/restore",
        {
            "tenantId": tenant_id,
            "tier": tier,
            "requestId": request_id,
            "text": text,
        },
        service_token,
    )
