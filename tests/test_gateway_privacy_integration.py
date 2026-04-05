"""Gateway integration tests for internal privacy-core service calls."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
GW_DIR = ROOT / "services" / "gateway"


def _make_gw_app(monkeypatch, *, enable_privacy_proxy: bool, privacy_fail_closed: bool = False):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("SIGNING_KEY", "test-secret-key")
    monkeypatch.setenv("ENABLE_PRIVACY_PROXY", "true" if enable_privacy_proxy else "false")
    monkeypatch.setenv("PRIVACY_FAIL_CLOSED", "true" if privacy_fail_closed else "false")
    monkeypatch.setenv("PRIVACY_SERVICE_URL", "http://privacy-core.internal")
    monkeypatch.setenv("PRIVACY_SERVICE_TOKEN", "privacy-core-internal-token")

    if str(GW_DIR) not in sys.path:
        sys.path.insert(0, str(GW_DIR))

    for mod in list(sys.modules):
        if mod == "app" or mod.startswith("app."):
            sys.modules.pop(mod)

    return importlib.import_module("app.main").app


@pytest.fixture
def privacy_gw(monkeypatch):
    app = _make_gw_app(monkeypatch, enable_privacy_proxy=True)
    with TestClient(app) as tc:
        yield tc
    if str(GW_DIR) in sys.path:
        sys.path.remove(str(GW_DIR))


def _headers() -> dict[str, str]:
    return {
        "X-Tenant-Id": "tenant_privacy",
        "X-Project-Id": "proj_privacy",
    }


def _body() -> dict:
    return {
        "tenant_id": "tenant_privacy",
        "project_id": "proj_privacy",
        "task_type": "summary",
        "input": {
            "text": "Contact jane@example.com",
            "context": {"privacy_tier": "growth"},
        },
    }


def test_gateway_sanitizes_before_provider_and_restores_after(privacy_gw, monkeypatch):
    import app.routers.infer as infer_module

    captured: dict[str, str] = {}

    async def fake_sanitize_text(**kwargs):
        return {
            "requestId": kwargs["request_id"],
            "redactedText": "Contact {{EMAIL_0}}",
            "matches": [{"label": "EMAIL"}],
        }

    async def fake_restore_text(**kwargs):
        return {
            "requestId": kwargs["request_id"],
            "restoredText": kwargs["text"].replace("{{EMAIL_0}}", "jane@example.com"),
            "restored": True,
        }

    async def fake_infer(*, tier, task_type, input_text, context):
        captured["input_text"] = input_text
        return {
            "model_tier": tier.value,
            "model_name": "stub",
            "result": f"processed {input_text}",
            "cost_estimate": 0.0,
        }

    monkeypatch.setattr(infer_module.privacy_client, "sanitize_text", fake_sanitize_text)
    monkeypatch.setattr(infer_module.privacy_client, "restore_text", fake_restore_text)
    monkeypatch.setattr(infer_module.registry, "infer", fake_infer)

    response = privacy_gw.post("/v1/infer", json=_body(), headers=_headers())

    assert response.status_code == 200
    assert captured["input_text"] == "Contact {{EMAIL_0}}"
    assert response.headers["x-privacy-request-id"].startswith("req_")
    assert response.json()["output"]["result"] == "processed Contact jane@example.com"


def test_gateway_fails_open_when_privacy_service_errors(monkeypatch):
    app = _make_gw_app(monkeypatch, enable_privacy_proxy=True, privacy_fail_closed=False)
    with TestClient(app) as client:
        import app.routers.infer as infer_module

        captured: dict[str, str] = {}

        async def broken_sanitize_text(**_kwargs):
            raise RuntimeError("privacy down")

        async def fake_infer(*, tier, task_type, input_text, context):
            captured["input_text"] = input_text
            return {
                "model_tier": tier.value,
                "model_name": "stub",
                "result": input_text,
                "cost_estimate": 0.0,
            }

        monkeypatch.setattr(infer_module.privacy_client, "sanitize_text", broken_sanitize_text)
        monkeypatch.setattr(infer_module.registry, "infer", fake_infer)

        response = client.post("/v1/infer", json=_body(), headers=_headers())

    if str(GW_DIR) in sys.path:
        sys.path.remove(str(GW_DIR))

    assert response.status_code == 200
    assert captured["input_text"] == "Contact jane@example.com"


def test_gateway_fails_closed_when_configured(monkeypatch):
    app = _make_gw_app(monkeypatch, enable_privacy_proxy=True, privacy_fail_closed=True)
    with TestClient(app) as client:
        import app.routers.infer as infer_module

        async def broken_sanitize_text(**_kwargs):
            raise RuntimeError("privacy down")

        monkeypatch.setattr(infer_module.privacy_client, "sanitize_text", broken_sanitize_text)
        response = client.post("/v1/infer", json=_body(), headers=_headers())

    if str(GW_DIR) in sys.path:
        sys.path.remove(str(GW_DIR))

    assert response.status_code == 502
    assert response.json()["detail"] == "Privacy service unavailable"
