import asyncio
import importlib.util
import sys
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]

MODULE_PATH = SERVICE_ROOT / "app" / "agents" / "content_engine.py"
SPEC = importlib.util.spec_from_file_location("content_engine", MODULE_PATH)
assert SPEC and SPEC.loader
content_engine = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(content_engine)

ContentEngineAgent = content_engine.ContentEngineAgent


def test_create_content_strategy_is_vertical_specific_and_dedupes_goals(monkeypatch):
    agent = ContentEngineAgent()

    async def fake_context(tenant_id):
        return {
            "tenant_id": tenant_id,
            "product_name": "Checkout Studio",
            "target_audience": ["store operators", "growth leads"],
            "value_propositions": ["faster cart recovery", "less manual follow-up"],
            "brand_voice": "direct",
        }

    monkeypatch.setattr(agent, "_load_marketing_context", fake_context)

    result = asyncio.run(
        agent.create_content_strategy(
            tenant_id="tenant-123",
            vertical="ecom",
            topic="abandoned cart recovery",
            goals=["Awareness", "Leads", "leads"],
        )
    )

    assert result["goals"] == ["awareness", "leads"]
    assert result["primary_goal"] == "awareness"
    assert result["content_types"] == ["article", "product page", "email", "social", "ad"]
    assert result["distribution_channels"] == ["seo", "email", "paid social", "marketplace"]
    assert result["context_snapshot"]["product_name"] == "Checkout Studio"
    assert result["keywords"][0] == "abandoned cart recovery"
    assert result["content_brief"]["primary_keyword"] == "abandoned cart recovery"
    assert any(action["goal"] == "leads" for action in result["recommended_actions"])
    assert result["angles"][0] == "How Checkout Studio solves abandoned cart recovery"


def test_optimize_for_ai_search_flags_low_depth_and_missing_keywords(monkeypatch):
    agent = ContentEngineAgent()

    async def fake_content(content_id):
        return {
            "id": content_id,
            "title": "Checkout Conversion Notes",
            "topic": "checkout conversion",
            "type": "article",
            "body": (
                "This article explains why checkout matters for ecommerce "
                "brands and goes on long enough that the first sentence is not "
                "a short summary and there are no headings or explicit calls to action"
            ),
            "keywords": [],
            "metadata": {"author": "Alex"},
        }

    monkeypatch.setattr(agent, "_load_content_asset", fake_content)

    result = asyncio.run(agent.optimize_for_ai_search("tenant-123", "content-456"))

    assert result["content_id"] == "content-456"
    assert result["title"] == "Checkout Conversion Notes"
    assert result["keywords"] == []
    assert result["structured_data"]["headline"] == "Checkout Conversion Notes"
    assert result["structured_data"]["keywords"] == []
    assert result["citation_signals"]["has_summary"] is False
    assert any(item["type"] == "depth" for item in result["recommendations"])
    assert any(item["type"] == "keywords" for item in result["recommendations"])
    assert result["llm_citation_potential"] < 0.5


def test_auto_optimize_retires_weak_content(monkeypatch):
    agent = ContentEngineAgent()
    retire_calls = []

    async def fake_content(content_id):
        return {
            "id": content_id,
            "type": "article",
            "performance": {
                "epc": 1.75,
                "days_published": 9,
                "views": 900,
                "clicks": 12,
                "conversions": 1,
            },
        }

    async def fake_retire(content_id):
        retire_calls.append(content_id)

    monkeypatch.setattr(agent, "_load_content_asset", fake_content)
    monkeypatch.setattr(agent, "_retire_content", fake_retire)

    result = asyncio.run(agent.auto_optimize("tenant-123", "content-low"))

    assert result["decision"] == "retire"
    assert result["status_after"] == "retired"
    assert result["actions_taken"][0]["action"] == "retire"
    assert retire_calls == ["content-low"]


def test_auto_optimize_scales_winning_content(monkeypatch):
    agent = ContentEngineAgent()
    variation_calls = []

    async def fake_content(content_id):
        return {
            "id": content_id,
            "type": "social",
            "performance": {
                "epc": 12.0,
                "days_published": 14,
                "views": 1500,
                "clicks": 240,
                "conversions": 32,
            },
        }

    async def fake_variations(content_id):
        variation_calls.append(content_id)
        return [f"{content_id}-a", f"{content_id}-b"]

    monkeypatch.setattr(agent, "_load_content_asset", fake_content)
    monkeypatch.setattr(agent, "_create_variations", fake_variations)

    result = asyncio.run(agent.auto_optimize("tenant-123", "content-win"))

    assert result["decision"] == "scale"
    assert result["status_after"] == "scaling"
    assert result["actions_taken"][0]["action"] == "create_variations"
    assert result["actions_taken"][0]["count"] == 2
    assert variation_calls == ["content-win"]
