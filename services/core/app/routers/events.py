"""
Event Bus Router
Pub/Sub for inter-service communication with webhook-style delivery.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..runtime.store import (
    append_event,
    delete_subscription,
    filter_events,
    list_events,
    list_subscriptions as load_subscriptions,
    notified_subscribers,
    put_subscription,
)

logger = logging.getLogger("core.events")

router = APIRouter()


class Event(BaseModel):
    event_type: str
    source_service: str
    payload: Dict[str, Any]
    timestamp: datetime = None

    def __init__(self, **data):
        super().__init__(**data)
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class Subscription(BaseModel):
    service_id: str
    event_types: List[str]
    callback_url: Optional[str] = None


async def _deliver_to_subscriber(
    callback_url: str, event_data: dict, service_id: str
) -> None:
    """Fire-and-forget delivery of an event to a subscriber's callback."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(callback_url, json=event_data)
            resp.raise_for_status()
            logger.info("Delivered %s to %s", event_data["event_type"], service_id)
    except Exception:
        logger.warning(
            "Failed to deliver event %s to %s at %s",
            event_data["event_type"],
            service_id,
            callback_url,
            exc_info=True,
        )


@router.post("/publish", response_model=dict)
async def publish_event(event: Event):
    """Publish an event to the bus and deliver to subscribers."""
    event_data = event.dict()
    # Serialize datetime for JSON delivery
    if isinstance(event_data.get("timestamp"), datetime):
        event_data["timestamp"] = event_data["timestamp"].isoformat()

    event_id = append_event(event_data)
    subscriptions = load_subscriptions()
    matched = notified_subscribers(event.event_type, subscriptions)

    # Deliver to each subscriber that has a callback_url
    delivery_tasks = []
    for service_id in matched:
        sub_data = subscriptions[service_id]
        # sub_data is now {"event_types": [...], "callback_url": "..."} or legacy list
        if isinstance(sub_data, dict):
            callback = sub_data.get("callback_url")
        else:
            callback = None

        if callback:
            delivery_tasks.append(
                _deliver_to_subscriber(callback, event_data, service_id)
            )

    if delivery_tasks:
        # Fire all deliveries concurrently, don't block the response
        asyncio.gather(*delivery_tasks, return_exceptions=True)

    return {
        "status": "published",
        "event_id": event_id,
        "notified_count": len(matched),
    }


@router.post("/subscribe", response_model=dict)
async def subscribe(subscription: Subscription):
    """Subscribe a service to event types, optionally with a callback URL."""
    put_subscription(
        subscription.service_id,
        subscription.event_types,
        callback_url=subscription.callback_url,
    )
    return {"status": "subscribed", "service_id": subscription.service_id}


@router.delete("/unsubscribe/{service_id}")
async def unsubscribe(service_id: str):
    """Unsubscribe a service from all events."""
    if not delete_subscription(service_id):
        raise HTTPException(status_code=404, detail="Subscription not found")
    return {"status": "unsubscribed", "service_id": service_id}


@router.get("/events", response_model=List[dict])
async def get_events(
    event_type: str = None,
    source_service: str = None,
    limit: int = 100,
):
    """Retrieve events with optional filtering."""
    events = filter_events(
        list_events(), event_type=event_type, source_service=source_service
    )
    return events[-limit:]


@router.get("/subscriptions", response_model=dict)
async def list_subscriptions():
    """List all active subscriptions."""
    return load_subscriptions()
