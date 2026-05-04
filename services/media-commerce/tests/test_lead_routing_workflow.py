import sys
import importlib
from pathlib import Path

from fastapi.testclient import TestClient

SERVICE_ROOT = Path(__file__).resolve().parents[1]


def _load_media_main():
    if str(SERVICE_ROOT) in sys.path:
        sys.path.remove(str(SERVICE_ROOT))
    sys.path.insert(0, str(SERVICE_ROOT))
    for key in list(sys.modules):
        if key == "app" or key.startswith("app."):
            sys.modules.pop(key)
    return importlib.import_module("app.main")


media_main = _load_media_main()

app = media_main.app
settings = media_main.settings


class DummyResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


class DummyAsyncClient:
    last_request = None
    response = DummyResponse(
        200,
        {
            "workflow_id": "wf-lead-456",
            "status": "running",
            "current_step": "route_lead",
            "message": "Workflow dealflow_lead_routing started",
        },
    )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, json, timeout):
        DummyAsyncClient.last_request = {
            "url": url,
            "json": json,
            "timeout": timeout,
        }
        return DummyAsyncClient.response


def test_submit_lead_routing_workflow_proxies_to_orchestration(monkeypatch):
    """Test that lead routing workflow submission proxies to orchestration service."""
    monkeypatch.setattr(media_main.httpx, "AsyncClient", DummyAsyncClient)
    monkeypatch.setattr(settings, "orchestration_url", "http://orchestration:8083")

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/leads/route/workflow",
            json={
                "tenant_id": "tenant-123",
                "lead_id": "lead-789",
                "intent_signals": [
                    "Shopify checkout optimization",
                    "Abandoned cart recovery",
                ],
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["submitted"] is True
    assert payload["workflow_type"] == "dealflow_lead_routing"
    assert payload["workflow"]["workflow_id"] == "wf-lead-456"
    assert DummyAsyncClient.last_request["url"] == "http://orchestration:8083/api/v1/workflows"
    
    # Verify workflow payload structure
    workflow_json = DummyAsyncClient.last_request["json"]
    assert workflow_json["workflow_type"] == "dealflow_lead_routing"
    assert workflow_json["input_data"]["lead_id"] == "lead-789"
    assert workflow_json["input_data"]["intent_signals"] == [
        "Shopify checkout optimization",
        "Abandoned cart recovery",
    ]
    assert workflow_json["metadata"]["source_service"] == "media-commerce"


def test_submit_lead_routing_workflow_surfaces_upstream_errors(monkeypatch):
    """Test that upstream orchestration errors are surfaced correctly."""
    DummyAsyncClient.response = DummyResponse(
        400,
        {"detail": "Unknown workflow type: dealflow_lead_routing"},
    )
    monkeypatch.setattr(media_main.httpx, "AsyncClient", DummyAsyncClient)
    monkeypatch.setattr(settings, "orchestration_url", "http://orchestration:8083")

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/leads/route/workflow",
            json={
                "tenant_id": "tenant-123",
                "lead_id": "lead-error",
                "intent_signals": ["test signal"],
            },
        )

    assert response.status_code == 502
    detail = response.json()["detail"]
    assert detail["message"] == "Orchestration service rejected workflow submission"
    assert detail["upstream_status"] == 400
    assert "Unknown workflow type" in detail["upstream_detail"]["detail"]
