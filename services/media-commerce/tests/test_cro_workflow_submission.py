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
            "workflow_id": "wf-cro-123",
            "status": "running",
            "current_step": "analyze_page",
            "message": "Workflow page_cro_optimization started",
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


def test_submit_page_cro_workflow_proxies_to_orchestration(monkeypatch):
    """Test that page CRO workflow submission proxies to orchestration service."""
    monkeypatch.setattr(media_main.httpx, "AsyncClient", DummyAsyncClient)
    monkeypatch.setattr(settings, "orchestration_url", "http://orchestration:8083")

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/cro/optimize-page/workflow",
            json={
                "tenant_id": "tenant-123",
                "page_id": "page-456",
                "page_type": "landing_page",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["submitted"] is True
    assert payload["workflow_type"] == "page_cro_optimization"
    assert payload["workflow"]["workflow_id"] == "wf-cro-123"
    assert DummyAsyncClient.last_request["url"] == "http://orchestration:8083/api/v1/workflows"
    
    workflow_json = DummyAsyncClient.last_request["json"]
    assert workflow_json["input_data"]["page_id"] == "page-456"
    assert workflow_json["metadata"]["source_service"] == "media-commerce"


def test_submit_ab_test_workflow_proxies_to_orchestration(monkeypatch):
    """Test that A/B test workflow submission proxies to orchestration service."""
    DummyAsyncClient.response = DummyResponse(
        200,
        {
            "workflow_id": "wf-ab-456",
            "status": "running",
            "current_step": "setup_test",
            "message": "Workflow ab_test_lifecycle started",
        },
    )
    monkeypatch.setattr(media_main.httpx, "AsyncClient", DummyAsyncClient)
    monkeypatch.setattr(settings, "orchestration_url", "http://orchestration:8083")

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/cro/ab-test/workflow",
            json={
                "tenant_id": "tenant-123",
                "page_id": "page-789",
                "variant_config": {
                    "variant_a": {"headline": "Original"},
                    "variant_b": {"headline": "New Headline"},
                },
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["submitted"] is True
    assert payload["workflow_type"] == "ab_test_lifecycle"
    assert payload["workflow"]["workflow_id"] == "wf-ab-456"
    assert DummyAsyncClient.last_request["url"] == "http://orchestration:8083/api/v1/workflows"


def test_submit_analytics_tracking_workflow_proxies_to_orchestration(monkeypatch):
    """Test that analytics tracking workflow submission proxies to orchestration service."""
    DummyAsyncClient.response = DummyResponse(
        200,
        {
            "workflow_id": "wf-analytics-789",
            "status": "running",
            "current_step": "define_event_schema",
            "message": "Workflow analytics_tracking_setup started",
        },
    )
    monkeypatch.setattr(media_main.httpx, "AsyncClient", DummyAsyncClient)
    monkeypatch.setattr(settings, "orchestration_url", "http://orchestration:8083")

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/analytics/track/workflow",
            json={
                "tenant_id": "tenant-123",
                "event_type": "signup_completed",
                "tracking_config": {},
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["submitted"] is True
    assert payload["workflow_type"] == "analytics_tracking_setup"
    assert payload["workflow"]["workflow_id"] == "wf-analytics-789"
    assert DummyAsyncClient.last_request["url"] == "http://orchestration:8083/api/v1/workflows"


def test_submit_cro_workflow_surfaces_upstream_errors(monkeypatch):
    """Test that upstream orchestration errors are surfaced correctly."""
    DummyAsyncClient.response = DummyResponse(
        400,
        {"detail": "Unknown workflow type: page_cro_optimization"},
    )
    monkeypatch.setattr(media_main.httpx, "AsyncClient", DummyAsyncClient)
    monkeypatch.setattr(settings, "orchestration_url", "http://orchestration:8083")

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/cro/optimize-page/workflow",
            json={
                "tenant_id": "tenant-123",
                "page_id": "page-error",
                "page_type": "landing_page",
            },
        )

    assert response.status_code == 502
    detail = response.json()["detail"]
    assert detail["message"] == "Orchestration service rejected workflow submission"
    assert detail["upstream_status"] == 400
