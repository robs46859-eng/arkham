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
            "workflow_id": "wf-123",
            "status": "running",
            "current_step": "retrieve_memory_context",
            "message": "Workflow media_content_strategy started",
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


def test_submit_content_strategy_workflow_proxies_to_orchestration(monkeypatch):
    monkeypatch.setattr(media_main.httpx, "AsyncClient", DummyAsyncClient)
    monkeypatch.setattr(settings, "orchestration_url", "http://orchestration:8083")

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/content/strategy/workflow",
            json={
                "tenant_id": "tenant-123",
                "vertical": "media",
                "topic": "affiliate content optimization",
                "goals": ["revenue", "awareness"],
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["submitted"] is True
    assert payload["workflow_type"] == "media_content_strategy"
    assert payload["workflow"]["workflow_id"] == "wf-123"
    assert DummyAsyncClient.last_request["url"] == "http://orchestration:8083/api/v1/workflows"
    assert DummyAsyncClient.last_request["json"]["input_data"]["topic"] == "affiliate content optimization"
    assert DummyAsyncClient.last_request["json"]["metadata"]["source_service"] == "media-commerce"


def test_submit_content_strategy_workflow_surfaces_upstream_errors(monkeypatch):
    DummyAsyncClient.response = DummyResponse(
        400,
        {"detail": "Unknown workflow type: media_content_strategy"},
    )
    monkeypatch.setattr(media_main.httpx, "AsyncClient", DummyAsyncClient)
    monkeypatch.setattr(settings, "orchestration_url", "http://orchestration:8083")

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/content/strategy/workflow",
            json={
                "tenant_id": "tenant-123",
                "vertical": "media",
                "topic": "affiliate content optimization",
                "goals": [],
            },
        )

    assert response.status_code == 502
    detail = response.json()["detail"]
    assert detail["message"] == "Orchestration service rejected workflow submission"
    assert detail["upstream_status"] == 400
