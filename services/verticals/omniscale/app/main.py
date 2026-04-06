"""
Omniscale Dashboard — central metrics and service overview.
Uses VerticalBase for automatic Core registration and event handling.
"""

from typing import Any, Dict

from packages.vertical_base import EventPayload, VerticalBase

vertical = VerticalBase(
    service_id="omniscale",
    title="Omniscale Dashboard",
    port=8000,
    capabilities=["dashboard", "metrics", "service_overview"],
    event_subscriptions=[
        "service.registered",
        "service.unregistered",
        "workflow.started",
        "workflow.completed",
        "metric.updated",
    ],
)

app = vertical.app

# ── In-memory metrics store ──────────────────────────────────────────────────

metrics_store: Dict[str, Any] = {
    "system_health": {"status": "healthy", "uptime": 0},
    "active_services": 0,
    "active_workflows": 0,
    "total_requests": 0,
    "recent_events": [],
}


# ── Event Handlers ───────────────────────────────────────────────────────────

@vertical.on_event("service.registered")
async def on_service_registered(event: EventPayload):
    metrics_store["active_services"] += 1
    _append_recent_event(event)


@vertical.on_event("service.unregistered")
async def on_service_unregistered(event: EventPayload):
    metrics_store["active_services"] = max(0, metrics_store["active_services"] - 1)
    _append_recent_event(event)


@vertical.on_event("workflow.started")
async def on_workflow_started(event: EventPayload):
    metrics_store["active_workflows"] += 1
    _append_recent_event(event)


@vertical.on_event("workflow.completed")
async def on_workflow_completed(event: EventPayload):
    metrics_store["active_workflows"] = max(0, metrics_store["active_workflows"] - 1)
    _append_recent_event(event)


@vertical.on_event("metric.updated")
async def on_metric_updated(event: EventPayload):
    name = event.payload.get("metric_name")
    if name:
        metrics_store[name] = event.payload.get("value")
    _append_recent_event(event)


def _append_recent_event(event: EventPayload, max_events: int = 50):
    metrics_store["recent_events"].append(
        {
            "event_type": event.event_type,
            "source": event.source_service,
            "timestamp": event.timestamp,
        }
    )
    metrics_store["recent_events"] = metrics_store["recent_events"][-max_events:]


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/")
async def dashboard_overview():
    """Main dashboard overview."""
    return {
        "status": "operational",
        "active_services": metrics_store["active_services"],
        "active_workflows": metrics_store["active_workflows"],
        "total_requests": metrics_store["total_requests"],
    }


@app.get("/metrics")
async def get_metrics():
    """Get all system metrics."""
    return metrics_store


@app.post("/metrics/{metric_name}")
async def update_metric(metric_name: str, value: Dict[str, Any]):
    """Update a specific metric."""
    metrics_store[metric_name] = value
    return {"status": "updated", "metric": metric_name}


@app.get("/recent-events")
async def recent_events():
    """Get recent events received from Core."""
    return {"events": metrics_store["recent_events"]}
