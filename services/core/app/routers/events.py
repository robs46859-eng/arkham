"""
Event Bus Router
Redis Pub/Sub for inter-service communication.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Any
from datetime import datetime

router = APIRouter()

# In-memory event store (will be replaced with Redis Pub/Sub)
event_store: List[dict] = []
subscribers: Dict[str, List[str]] = {}


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
    event_store.append(event_data)
    
    # Notify subscribers (stub - will use Redis Pub/Sub in production)
    notified = []
    for sub_service, sub_events in subscribers.items():
        if event.event_type in sub_events or "*" in sub_events:
            notified.append(sub_service)
    
    return {"status": "published", "event_id": len(event_store) - 1, "notified_count": len(notified)}


@router.post("/subscribe", response_model=dict)
async def subscribe(subscription: Subscription):
    """Subscribe a service to event types."""
    subscribers[subscription.service_id] = subscription.event_types
    return {"status": "subscribed", "service_id": subscription.service_id}


@router.delete("/unsubscribe/{service_id}")
async def unsubscribe(service_id: str):
    """Unsubscribe a service from all events."""
    if service_id not in subscribers:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    del subscribers[service_id]
    return {"status": "unsubscribed", "service_id": service_id}


@router.get("/events", response_model=List[dict])
async def get_events(
    event_type: str = None,
    source_service: str = None,
    limit: int = 100
):
    """Retrieve events with optional filtering."""
    events = event_store.copy()
    
    if event_type:
        events = [e for e in events if e["event_type"] == event_type]
    if source_service:
        events = [e for e in events if e["source_service"] == source_service]
    
    return events[-limit:]


@router.get("/subscriptions", response_model=Dict[str, List[str]])
async def list_subscriptions():
    """List all active subscriptions."""
    return subscribers
