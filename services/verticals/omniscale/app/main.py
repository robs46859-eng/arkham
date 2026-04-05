from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any

app = FastAPI(title="Omniscale Dashboard", version="0.1.0")


class DashboardMetric(BaseModel):
    metric_name: str
    value: float
    unit: str
    timestamp: str


# In-memory metrics store
metrics_store: Dict[str, Any] = {
    "system_health": {"status": "healthy", "uptime": 0},
    "active_services": 0,
    "active_workflows": 0,
    "total_requests": 0,
}


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


@app.get("/services/status")
async def services_status():
    """Get status of all registered services."""
    # Will integrate with Core registry
    return {"services": []}


@app.get("/workflows/active")
async def active_workflows():
    """Get currently active workflows."""
    # Will integrate with Orchestration service
    return {"workflows": []}


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "omniscale-dashboard"}
