import asyncio
import sys
from pathlib import Path

from fastapi.testclient import TestClient

SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from app.agents.deal_flow import DealFlowAgent
from app.main import app


def test_route_lead_staffing_high_confidence():
    agent = DealFlowAgent()

    result = asyncio.run(
        agent.route_lead(
            tenant_id="tenant-123",
            lead_id="lead-123",
            intent_signals=[
                "Need nurse staffing support",
                "Fill shifts urgently",
                "Credentialing backlog",
                "Request pricing",
            ],
        )
    )

    assert result["routed_vertical"] == "staffing"
    assert result["requires_review"] is False
    assert result["lead_stage"] == "sql"
    assert result["confidence"] >= 0.8
    assert "staffing" in result["matched_signals"]["staffing"]
    assert "pricing" in result["normalized_signals"][3]


def test_route_lead_ambiguous_requires_review():
    agent = DealFlowAgent()

    result = asyncio.run(
        agent.route_lead(
            tenant_id="tenant-123",
            lead_id="lead-ambiguous",
            intent_signals=[
                "Need help with growth",
                "Looking for better automation",
            ],
        )
    )

    assert result["requires_review"] is True
    assert result["lead_stage"] == "review"
    assert result["next_action"] == "human_review"
    assert "baseline vertical priority" in result["rationale"]


def test_route_lead_endpoint_returns_explainable_vertical_decision():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/leads/route",
            json={
                "tenant_id": "tenant-456",
                "lead_id": "lead-ecom",
                "intent_signals": [
                    "Shopify checkout is leaking conversions",
                    "Need help with abandoned cart flows",
                    "Product feed cleanup",
                ],
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["routed_vertical"] == "ecom"
    assert payload["requires_review"] is False
    assert payload["matched_signals"]["ecom"] == [
        "abandoned cart",
        "cart",
        "checkout",
        "product feed",
        "shopify",
    ]
    assert payload["scores_by_vertical"]["ecom"] > payload["scores_by_vertical"]["saas"]


def test_route_lead_endpoint_rejects_blank_signals():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/leads/route",
            json={
                "tenant_id": "tenant-789",
                "lead_id": "lead-invalid",
                "intent_signals": ["   ", ""],
            },
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "intent_signals must include at least one non-empty signal"
