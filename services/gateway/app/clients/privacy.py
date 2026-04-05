"""
Privacy service client for text sanitization and restoration.

Implements PII redaction before sending to LLMs and restoration of
original values in responses. Supports multi-tier privacy levels.
"""

from __future__ import annotations

import httpx


async def sanitize_text(
    *,
    base_url: str,
    service_token: str,
    tenant_id: str,
    tier: str,
    request_id: str,
    text: str,
) -> dict:
    """
    Send text to privacy service for PII sanitization.

    Args:
        base_url: Privacy service base URL
        service_token: Internal service authentication token
        tenant_id: Tenant identifier for isolation
        tier: Privacy tier (dev, growth, pro)
        request_id: Unique request identifier for tracking
        text: Raw text to sanitize

    Returns:
        Dict with 'redactedText' and 'requestId' keys

    Raises:
        httpx.HTTPError: If privacy service is unavailable
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{base_url}/v1/sanitize",
            headers={
                "Authorization": f"Bearer {service_token}",
                "Content-Type": "application/json",
                "X-Tenant-Id": tenant_id,
                "X-Request-Id": request_id,
            },
            json={
                "text": text,
                "tier": tier,
            },
        )
        response.raise_for_status()
        return response.json()


async def restore_text(
    *,
    base_url: str,
    service_token: str,
    tenant_id: str,
    tier: str,
    request_id: str,
    text: str,
) -> dict:
    """
    Restore original PII values in sanitized text.

    Args:
        base_url: Privacy service base URL
        service_token: Internal service authentication token
        tenant_id: Tenant identifier for isolation
        tier: Privacy tier (dev, growth, pro)
        request_id: Original request identifier from sanitization
        text: Sanitized text to restore

    Returns:
        Dict with 'restoredText' key

    Raises:
        httpx.HTTPError: If privacy service is unavailable
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{base_url}/v1/restore",
            headers={
                "Authorization": f"Bearer {service_token}",
                "Content-Type": "application/json",
                "X-Tenant-Id": tenant_id,
                "X-Request-Id": request_id,
            },
            json={
                "text": text,
                "tier": tier,
            },
        )
        response.raise_for_status()
        return response.json()
