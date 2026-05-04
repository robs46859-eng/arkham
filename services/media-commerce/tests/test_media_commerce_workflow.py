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
            "workflow_id": "wf-epc-123",
            "status": "running",
            "current_step": "calculate_epc",
            "message": "Workflow epc_monitoring_loop started",
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


def test_submit_epc_monitoring_workflow_proxies_to_orchestration(monkeypatch):
    """Test that EPC monitoring workflow submission proxies to orchestration."""
    monkeypatch.setattr(media_main.httpx, "AsyncClient", DummyAsyncClient)
    monkeypatch.setattr(settings, "orchestration_url", "http://orchestration:8083")

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/epc/monitor/workflow",
            json={
                "tenant_id": "tenant-123",
                "content_id": "content-456",
                "vertical": "media",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["submitted"] is True
    assert payload["workflow_type"] == "epc_monitoring_loop"
    assert payload["workflow"]["workflow_id"] == "wf-epc-123"
    assert DummyAsyncClient.last_request["url"] == "http://orchestration:8083/api/v1/workflows"
    
    workflow_json = DummyAsyncClient.last_request["json"]
    assert workflow_json["input_data"]["content_id"] == "content-456"
    assert workflow_json["metadata"]["source_service"] == "media-commerce"


def test_submit_content_optimization_workflow_proxies_to_orchestration(monkeypatch):
    """Test that content optimization workflow submission proxies to orchestration."""
    DummyAsyncClient.response = DummyResponse(
        200,
        {
            "workflow_id": "wf-opt-456",
            "status": "running",
            "current_step": "take_action",
            "message": "Workflow epc_monitoring_loop started",
        },
    )
    monkeypatch.setattr(media_main.httpx, "AsyncClient", DummyAsyncClient)
    monkeypatch.setattr(settings, "orchestration_url", "http://orchestration:8083")

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/epc/auto-optimize/workflow",
            json={
                "tenant_id": "tenant-123",
                "content_id": "content-789",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["submitted"] is True
    assert payload["workflow_type"] == "epc_monitoring_loop"
    assert payload["workflow"]["workflow_id"] == "wf-opt-456"


def test_submit_affiliate_optimization_workflow_proxies_to_orchestration(monkeypatch):
    """Test that affiliate optimization workflow submission proxies to orchestration."""
    DummyAsyncClient.response = DummyResponse(
        200,
        {
            "workflow_id": "wf-aff-789",
            "status": "running",
            "current_step": "swap_placements",
            "message": "Workflow affiliate_optimization started",
        },
    )
    monkeypatch.setattr(media_main.httpx, "AsyncClient", DummyAsyncClient)
    monkeypatch.setattr(settings, "orchestration_url", "http://orchestration:8083")

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/affiliate/optimize/workflow",
            json={
                "tenant_id": "tenant-123",
                "content_id": "content-123",
                "new_placement": {
                    "network": "amazon",
                    "offer_id": "B08XYZ123",
                },
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["submitted"] is True
    assert payload["workflow_type"] == "affiliate_optimization"
    assert payload["workflow"]["workflow_id"] == "wf-aff-789"


def test_submit_content_repurpose_workflow_proxies_to_orchestration(monkeypatch):
    """Test that content repurposing workflow submission proxies to orchestration."""
    DummyAsyncClient.response = DummyResponse(
        200,
        {
            "workflow_id": "wf-repurpose-123",
            "status": "running",
            "current_step": "generate_variations",
            "message": "Workflow content_repurposing started",
        },
    )
    monkeypatch.setattr(media_main.httpx, "AsyncClient", DummyAsyncClient)
    monkeypatch.setattr(settings, "orchestration_url", "http://orchestration:8083")

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/content/repurpose/workflow",
            json={
                "tenant_id": "tenant-123",
                "content_id": "content-456",
                "target_formats": ["social", "email", "video"],
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["submitted"] is True
    assert payload["workflow_type"] == "content_repurposing"
    assert payload["workflow"]["workflow_id"] == "wf-repurpose-123"


def test_submit_media_commerce_workflow_surfaces_upstream_errors(monkeypatch):
    """Test that upstream orchestration errors are surfaced correctly."""
    DummyAsyncClient.response = DummyResponse(
        400,
        {"detail": "Unknown workflow type: epc_monitoring_loop"},
    )
    monkeypatch.setattr(media_main.httpx, "AsyncClient", DummyAsyncClient)
    monkeypatch.setattr(settings, "orchestration_url", "http://orchestration:8083")

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/epc/monitor/workflow",
            json={
                "tenant_id": "tenant-123",
                "content_id": "content-error",
            },
        )

    assert response.status_code == 502
    detail = response.json()["detail"]
    assert detail["message"] == "Orchestration service rejected workflow submission"
    assert detail["upstream_status"] == 400
