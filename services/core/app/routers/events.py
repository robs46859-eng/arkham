"""
Event Bus Router
Redis Pub/Sub for inter-service communication.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Any
from datetime import datetime

from ..runtime.store import (
    append_event,
    delete_subscription,
    filter_events,
    list_events,
    list_subscriptions as load_subscriptions,
    notified_subscribers,
    put_subscription,
)

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


@router.post("/publish", response_model=dict)
async def publish_event(event: Event):
    """Publish an event to the bus."""
    event_data = event.dict()
    event_id = append_event(event_data)
    subscribers = load_subscriptions()
    notified = notified_subscribers(event.event_type, subscribers)

    return {"status": "published", "event_id": event_id, "notified_count": len(notified)}


@router.post("/subscribe", response_model=dict)
async def subscribe(subscription: Subscription):
    """Subscribe a service to event types."""
    put_subscription(subscription.service_id, subscription.event_types)
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
    limit: int = 100
):
    """Retrieve events with optional filtering."""
    events = filter_events(list_events(), event_type=event_type, source_service=source_service)
    return events[-limit:]


@router.get("/subscriptions", response_model=Dict[str, List[str]])
async def list_subscriptions():
    """List all active subscriptions."""
    return load_subscriptions()
