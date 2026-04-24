"""Core event publishing for worldgraph state transitions."""

from __future__ import annotations

from typing import Any

import httpx

from ..settings import settings


async def publish_event(event_type: str, payload: dict[str, Any]) -> None:
    body = {
        "event_type": event_type,
        "source_service": settings.service_name,
        "payload": payload,
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(f"{settings.core_service_url}/events/publish", json=body)
    except Exception:
        # Event publishing should not block the primary control path.
        return

