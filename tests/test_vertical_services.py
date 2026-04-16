"""Vertical service contract tests."""

import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
VERTICALS = {
    "ai-consistency": {
        "dir": ROOT / "services" / "verticals" / "ai_consistency",
        "probe": "/tests",
    },
    "autopitch": {
        "dir": ROOT / "services" / "verticals" / "autopitch",
        "probe": "/ideas",
    },
    "cyberscribe": {
        "dir": ROOT / "services" / "verticals" / "cyberscribe",
        "probe": "/code",
    },
    "digital-it-girl": {
        "dir": ROOT / "services" / "verticals" / "digital_it_girl",
        "probe": "/trends",
    },
    "omniscale": {
        "dir": ROOT / "services" / "verticals" / "omniscale",
        "probe": "/metrics",
    },
    "public-beta": {
        "dir": ROOT / "services" / "verticals" / "public_beta",
        "probe": "/features/previews",
    },
    "workflow-architect": {
        "dir": ROOT / "services" / "verticals" / "workflow_architect",
        "probe": "/workflows",
    },
}


def _load_vertical_app(vertical_dir: Path):
    sys.path.insert(0, str(vertical_dir))
    for module_name in list(sys.modules):
        if module_name == "app" or module_name.startswith("app."):
            sys.modules.pop(module_name)
    return importlib.import_module("app.main").app


def test_verticals_expose_health_and_primary_route(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql://robco:password@localhost:5432/robco_db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("CORE_SERVICE_URL", "http://core:8000")

    for service_id, spec in VERTICALS.items():
        app = _load_vertical_app(spec["dir"])
        client = TestClient(app)

        health = client.get("/health")
        assert health.status_code == 200
        assert health.json() == {"status": "ok", "service": service_id}

        probe = client.get(spec["probe"])
        assert probe.status_code == 200

        sys.path.remove(str(spec["dir"]))


def test_workflow_architect_exposes_sales_to_cash_template(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql://robco:password@localhost:5432/robco_db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("CORE_SERVICE_URL", "http://core:3000")

    app = _load_vertical_app(VERTICALS["workflow-architect"]["dir"])
    client = TestClient(app)

    response = client.post(
        "/workflows/templates/sales-to-cash",
        json={
            "customer_name": "Acme Mechanical",
            "offer_name": "BIM pilot",
            "amount_usd": 2500,
            "target_customer_profile": "Mechanical contractors that need BIM coordination help",
            "lead_source": "https://example.com/leads.csv",
            "outreach_channel": "email",
            "outreach_provider": "resend",
            "product_url": "https://example.com/bim-pilot",
            "payment_url": "https://buy.stripe.com/test_123",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "designed"
    assert body["workflow"]["metadata"]["template"] == "sales-to-cash"
    assert body["workflow"]["metadata"]["automation_ready"] is True
    assert body["workflow"]["metadata"]["payment_url"] == "https://buy.stripe.com/test_123"
    assert body["workflow"]["steps"][3]["action"] == "send_outreach_via_provider"
    assert body["workflow"]["steps"][-1]["step_id"] == "onboarding"

    sys.path.remove(str(VERTICALS["workflow-architect"]["dir"]))
