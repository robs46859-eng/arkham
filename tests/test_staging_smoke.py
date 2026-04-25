"""Smoke coverage for deployable service contracts."""

from __future__ import annotations

import importlib
import sys

import pytest
from fastapi.testclient import TestClient

from packages.db import get_db
from tests.conftest import MockSession
from tests.test_auth import _seed_tenant_api_key

SERVICE_MODULES = {
    "gateway": "services.gateway.app.main",
    "core": "services.core.app.main",
    "orchestration": "services.orchestration.app.main",
    "bim-ingestion": "services.bim_ingestion.app.main",
    "omniscale": "services.verticals.omniscale.app.main",
}


def _load_service_app(service_name: str):
    module_path = SERVICE_MODULES[service_name]
    module_prefix = module_path.rsplit(".", 1)[0]
    for module_name in list(sys.modules):
        if module_name == module_prefix or module_name.startswith(f"{module_prefix}."):
            sys.modules.pop(module_name)
    module = importlib.import_module(module_path)
    return module.app, module


@pytest.mark.smoke
def test_services_health_and_readyz(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("SIGNING_KEY", "smoke-test-signing-key-0123456789")

    for service_name in SERVICE_MODULES:
        app, module = _load_service_app(service_name)
        if hasattr(module, "check_database"):
            monkeypatch.setattr(module, "check_database", lambda _: (True, "ok"))
        if hasattr(module, "check_redis"):
            monkeypatch.setattr(module, "check_redis", lambda _: (True, "ok"))

        client = TestClient(app)
        health = client.get("/health")
        ready = client.get("/readyz")

        assert health.status_code == 200
        assert ready.status_code == 200
        assert ready.json()["status"] == "ready"


@pytest.mark.smoke
def test_gateway_auth_roundtrip(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("SIGNING_KEY", "smoke-test-signing-key-0123456789")

    app, module = _load_service_app("gateway")
    monkeypatch.setattr(module, "check_database", lambda _: (True, "ok"))
    monkeypatch.setattr(module, "check_redis", lambda _: (True, "ok"))

    shared_db = MockSession()

    def override_db():
        yield shared_db

    app.dependency_overrides[get_db] = override_db
    api_key = _seed_tenant_api_key(shared_db, "tenant_smoke", name="Smoke Tenant")

    client = TestClient(app)
    token_response = client.post(
        "/v1/auth/token",
        json={"tenant_id": "tenant_smoke", "api_key": api_key, "project_id": "proj_smoke"},
    )
    assert token_response.status_code == 200

    infer_response = client.post(
        "/v1/infer",
        json={
            "tenant_id": "tenant_smoke",
            "project_id": "proj_smoke",
            "task_type": "summary",
            "input": {"text": "smoke test"},
        },
        headers={"Authorization": f"Bearer {token_response.json()['access_token']}"},
    )
    assert infer_response.status_code == 200


@pytest.mark.smoke
def test_gateway_ai_convert_auto_execute_logs_email(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("SIGNING_KEY", "smoke-test-signing-key-0123456789")
    monkeypatch.setenv("AUTOMATION_DRY_RUN", "true")

    app, module = _load_service_app("gateway")
    monkeypatch.setattr(module, "check_database", lambda _: (True, "ok"))
    monkeypatch.setattr(module, "check_redis", lambda _: (True, "ok"))

    shared_db = MockSession()

    def override_db():
        yield shared_db

    app.dependency_overrides[get_db] = override_db
    api_key = _seed_tenant_api_key(shared_db, "tenant_fullstack", name="FullStack Tenant")

    client = TestClient(app)
    response = client.post(
        "/v1/ai",
        json={
            "module": "convert",
            "inputs": {
                "industry": "BIM",
                "pain_point": "manual coordination reporting",
            },
            "auto_execute": True,
            "automation": {
                "to": "buyer@example.com",
                "product": "agency",
                "payment_url": "https://buy.stripe.com/test_123",
                "leads": [
                    {
                        "First Name": "Ada",
                        "Company": "Apollo Agency",
                        "Email": "ada@example.com",
                        "Title": "Founder",
                        "Technographics": "Make.com, HubSpot",
                    }
                ],
            },
        },
        headers={"Authorization": f"Bearer {api_key}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["module"] == "convert"
    assert body["model"] == "claude-sonnet"
    assert body["automation"][0]["action"] == "email.send"
    assert body["automation"][0]["status"] == "dry_run"
    assert body["automation"][0]["payload"]["to"] == "ada@example.com"
    assert "Apollo Agency" in body["automation"][0]["payload"]["body"]
    assert "https://buy.stripe.com/test_123" in body["automation"][0]["payload"]["body"]
    assert any(getattr(record, "action", "") == "email.send" for record in shared_db._objects.values())


@pytest.mark.smoke
def test_gateway_ai_convert_recalls_valid_workflow_memory(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("SIGNING_KEY", "smoke-test-signing-key-0123456789")

    app, module = _load_service_app("gateway")
    monkeypatch.setattr(module, "check_database", lambda _: (True, "ok"))
    monkeypatch.setattr(module, "check_redis", lambda _: (True, "ok"))

    from services.gateway.app.routers import ai as ai_router

    monkeypatch.setattr(ai_router.settings, "enable_semantic_cache", True)

    workflow_cache: dict[tuple[str, str], dict] = {}

    async def fake_set(*, tenant_id: str, task_type: str, input_text: str, output: dict) -> None:
        workflow_cache[(tenant_id, task_type)] = {"input_text": input_text, "output": output}

    async def fake_get(*, tenant_id: str, task_type: str, input_text: str, threshold=None):
        record = workflow_cache.get((tenant_id, task_type))
        if record and record["input_text"] == input_text:
            return record["output"]
        return None

    monkeypatch.setattr(ai_router.semantic_cache, "set", fake_set)
    monkeypatch.setattr(ai_router.semantic_cache, "get", fake_get)

    shared_db = MockSession()

    def override_db():
        yield shared_db

    app.dependency_overrides[get_db] = override_db
    api_key = _seed_tenant_api_key(shared_db, "tenant_fullstack", name="FullStack Tenant")

    cached_output = {
        "pitch": {
            "headline": "Cached offer",
            "body": "Cached body",
            "time_saved": "5-10 hours per week",
            "cost_equiv": "$500-$1,500/month",
            "roi_days": 30,
            "cta": "Want to try Agency for $30/mo?",
        },
        "template_id": "autopitch_v1",
        "product": {
            "name": "Agency",
            "product_id": "prod_UICyBy4ItoEBsW",
            "payment_url": "https://buy.stripe.com/bJefZaeRR4V20iRfh5fnO02",
            "price": "$30/mo",
        },
        "execution": {
            "email": {
                "to": None,
                "subject": "Cached offer",
                "body": "Cached body",
            },
            "crm_payload": {
                "industry": "Marketing",
                "pain_point": "manual prospecting and follow-up",
                "payment_url": "https://buy.stripe.com/bJefZaeRR4V20iRfh5fnO02",
            },
            "follow_up_sequence": [2, 5, 10],
        },
    }

    workflow_metadata = ai_router._convert_workflow_metadata(
        ai_router.AiRequest(
            module="convert",
            inputs={"industry": "Marketing", "target_buyer": ai_router.DEFAULT_TARGET_BUYER},
            automation={"product": "agency"},
        ),
        ai_router.MODULE_CONFIG["convert"],
    )
    workflow_context = ai_router._convert_workflow_context(
        ai_router.AiRequest(
            module="convert",
            inputs={"industry": "Marketing", "target_buyer": ai_router.DEFAULT_TARGET_BUYER},
            automation={"product": "agency"},
        ),
        ai_router.MODULE_CONFIG["convert"],
    )
    task_type = ai_router.build_workflow_memory_task_type(
        workflow_metadata["workflow_name"],
        workflow_metadata["offer_type"],
        workflow_metadata["stage"],
    )
    input_text = ai_router.build_workflow_memory_input_text(
        ai_router._convert_workflow_input_text(
            ai_router.AiRequest(
                module="convert",
                inputs={"industry": "Marketing", "target_buyer": ai_router.DEFAULT_TARGET_BUYER},
                automation={"product": "agency"},
            ),
            ai_router.MODULE_CONFIG["convert"],
        ),
        workflow_context,
    )
    workflow_cache[("tenant_fullstack", task_type)] = {
        "input_text": input_text,
        "output": ai_router.build_workflow_memory_envelope(
            workflow_type=workflow_metadata["workflow_name"],
            offer_type=workflow_metadata["offer_type"],
            stage=workflow_metadata["stage"],
            output=cached_output,
            context=workflow_context,
            metadata=workflow_metadata,
        ),
    }

    client = TestClient(app)
    response = client.post(
        "/v1/ai",
        json={
            "module": "convert",
            "inputs": {
                "industry": "Marketing",
                "target_buyer": ai_router.DEFAULT_TARGET_BUYER,
            },
            "automation": {
                "product": "agency",
            },
        },
        headers={"Authorization": f"Bearer {api_key}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["cache_hit"] is True
    assert body["output"]["pitch"]["headline"] == "Cached offer"
    assert body["usage"]["workflow_memory"]["status"] == "hit"
    assert body["usage"]["workflow_memory"]["reason"] == "hit"
    assert body["usage"]["workflow_memory"]["estimated_time_saved_ms"] == 1800
    assert any(
        getattr(record, "action", "") == "workflow_memory.recall" and getattr(record, "status", "") == "hit"
        for record in shared_db._objects.values()
    )
    decision_records = [
        record for record in shared_db._objects.values()
        if getattr(record, "__tablename__", "") == "workflow_memory_decisions"
    ]
    assert len(decision_records) == 1
    assert decision_records[0].decision == "reuse"
    assert "reused because hit" in decision_records[0].decision_metadata["decision_summary"]
    assert decision_records[0].decision_metadata["reason_path"][-1] == "decision:reuse"


@pytest.mark.smoke
def test_gateway_ai_convert_ignores_stale_workflow_memory(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("SIGNING_KEY", "smoke-test-signing-key-0123456789")

    app, module = _load_service_app("gateway")
    monkeypatch.setattr(module, "check_database", lambda _: (True, "ok"))
    monkeypatch.setattr(module, "check_redis", lambda _: (True, "ok"))

    from services.gateway.app.routers import ai as ai_router

    monkeypatch.setattr(ai_router.settings, "enable_semantic_cache", True)

    workflow_cache: dict[tuple[str, str], dict] = {}

    async def fake_set(*, tenant_id: str, task_type: str, input_text: str, output: dict) -> None:
        workflow_cache[(tenant_id, task_type)] = {"input_text": input_text, "output": output}

    async def fake_get(*, tenant_id: str, task_type: str, input_text: str, threshold=None):
        record = workflow_cache.get((tenant_id, task_type))
        if record and record["input_text"] == input_text:
            return record["output"]
        return None

    monkeypatch.setattr(ai_router.semantic_cache, "set", fake_set)
    monkeypatch.setattr(ai_router.semantic_cache, "get", fake_get)

    shared_db = MockSession()

    def override_db():
        yield shared_db

    app.dependency_overrides[get_db] = override_db
    api_key = _seed_tenant_api_key(shared_db, "tenant_fullstack", name="FullStack Tenant")

    request_obj = ai_router.AiRequest(
        module="convert",
        inputs={"industry": "Marketing", "target_buyer": ai_router.DEFAULT_TARGET_BUYER},
        automation={"product": "agency"},
    )
    workflow_metadata = ai_router._convert_workflow_metadata(request_obj, ai_router.MODULE_CONFIG["convert"])
    stale_metadata = {**workflow_metadata, "offer_version": "stale-offer.v0"}
    workflow_context = ai_router._convert_workflow_context(request_obj, ai_router.MODULE_CONFIG["convert"])
    task_type = ai_router.build_workflow_memory_task_type(
        workflow_metadata["workflow_name"],
        workflow_metadata["offer_type"],
        workflow_metadata["stage"],
    )
    input_text = ai_router.build_workflow_memory_input_text(
        ai_router._convert_workflow_input_text(request_obj, ai_router.MODULE_CONFIG["convert"]),
        workflow_context,
    )
    workflow_cache[("tenant_fullstack", task_type)] = {
        "input_text": input_text,
        "output": ai_router.build_workflow_memory_envelope(
            workflow_type=workflow_metadata["workflow_name"],
            offer_type=workflow_metadata["offer_type"],
            stage=workflow_metadata["stage"],
            output={"pitch": {"headline": "Stale cached offer"}},
            context=workflow_context,
            metadata=stale_metadata,
        ),
    }

    client = TestClient(app)
    response = client.post(
        "/v1/ai",
        json={
            "module": "convert",
            "inputs": {
                "industry": "Marketing",
                "target_buyer": ai_router.DEFAULT_TARGET_BUYER,
            },
            "automation": {
                "product": "agency",
            },
        },
        headers={"Authorization": f"Bearer {api_key}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["output"]["pitch"]["headline"] != "Stale cached offer"
    assert body["usage"]["workflow_memory"]["status"] == "fallback"
    assert body["usage"]["workflow_memory"]["reason"] == "offer_version_mismatch"
    assert body["usage"]["workflow_memory"]["stored"] is True
    assert any(
        getattr(record, "action", "") == "workflow_memory.recall"
        and getattr(record, "payload", {}).get("reason") == "offer_version_mismatch"
        for record in shared_db._objects.values()
    )
    decision_records = [
        record for record in shared_db._objects.values()
        if getattr(record, "__tablename__", "") == "workflow_memory_decisions"
    ]
    assert len(decision_records) == 1
    assert decision_records[0].decision == "regenerate"
    assert decision_records[0].fallback_reason == "offer_version_mismatch"
    assert "offer_version_mismatch" in decision_records[0].decision_metadata["decision_summary"]


@pytest.mark.smoke
def test_gateway_ai_convert_rejects_partial_cached_payload(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("SIGNING_KEY", "smoke-test-signing-key-0123456789")

    app, module = _load_service_app("gateway")
    monkeypatch.setattr(module, "check_database", lambda _: (True, "ok"))
    monkeypatch.setattr(module, "check_redis", lambda _: (True, "ok"))

    from services.gateway.app.routers import ai as ai_router

    monkeypatch.setattr(ai_router.settings, "enable_semantic_cache", True)

    workflow_cache: dict[tuple[str, str], dict] = {}

    async def fake_set(*, tenant_id: str, task_type: str, input_text: str, output: dict) -> None:
        workflow_cache[(tenant_id, task_type)] = {"input_text": input_text, "output": output}

    async def fake_get(*, tenant_id: str, task_type: str, input_text: str, threshold=None):
        record = workflow_cache.get((tenant_id, task_type))
        if record and record["input_text"] == input_text:
            return record["output"]
        return None

    monkeypatch.setattr(ai_router.semantic_cache, "set", fake_set)
    monkeypatch.setattr(ai_router.semantic_cache, "get", fake_get)

    shared_db = MockSession()

    def override_db():
        yield shared_db

    app.dependency_overrides[get_db] = override_db
    api_key = _seed_tenant_api_key(shared_db, "tenant_fullstack", name="FullStack Tenant")

    request_obj = ai_router.AiRequest(
        module="convert",
        inputs={"industry": "Marketing", "target_buyer": ai_router.DEFAULT_TARGET_BUYER},
        automation={"product": "agency"},
    )
    workflow_metadata = ai_router._convert_workflow_metadata(request_obj, ai_router.MODULE_CONFIG["convert"])
    workflow_context = ai_router._convert_workflow_context(request_obj, ai_router.MODULE_CONFIG["convert"])
    task_type = ai_router.build_workflow_memory_task_type(
        workflow_metadata["workflow_name"],
        workflow_metadata["offer_type"],
        workflow_metadata["stage"],
    )
    input_text = ai_router.build_workflow_memory_input_text(
        ai_router._convert_workflow_input_text(request_obj, ai_router.MODULE_CONFIG["convert"]),
        workflow_context,
    )
    workflow_cache[("tenant_fullstack", task_type)] = {
        "input_text": input_text,
        "output": ai_router.build_workflow_memory_envelope(
            workflow_type=workflow_metadata["workflow_name"],
            offer_type=workflow_metadata["offer_type"],
            stage=workflow_metadata["stage"],
            output={"pitch": {"headline": "Partial cached offer"}},
            context=workflow_context,
            metadata=workflow_metadata,
        ),
    }

    client = TestClient(app)
    response = client.post(
        "/v1/ai",
        json={
            "module": "convert",
            "inputs": {
                "industry": "Marketing",
                "target_buyer": ai_router.DEFAULT_TARGET_BUYER,
            },
            "automation": {
                "product": "agency",
            },
        },
        headers={"Authorization": f"Bearer {api_key}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["output"]["pitch"]["headline"] != "Partial cached offer"
    assert body["usage"]["workflow_memory"]["status"] == "fallback"
    assert body["usage"]["workflow_memory"]["reason"] == "partial_payload"
    assert any(
        getattr(record, "action", "") == "workflow_memory.recall"
        and getattr(record, "payload", {}).get("reason") == "partial_payload"
        for record in shared_db._objects.values()
    )


@pytest.mark.smoke
def test_gateway_ai_convert_rejects_negative_score_recalled_flow(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("SIGNING_KEY", "smoke-test-signing-key-0123456789")

    app, module = _load_service_app("gateway")
    monkeypatch.setattr(module, "check_database", lambda _: (True, "ok"))
    monkeypatch.setattr(module, "check_redis", lambda _: (True, "ok"))

    from services.gateway.app.routers import ai as ai_router
    from services.gateway.app.routers import crm as crm_router
    from packages.models import CRMActivityRecord
    from datetime import datetime

    monkeypatch.setattr(ai_router.settings, "enable_semantic_cache", True)

    workflow_cache: dict[tuple[str, str], dict] = {}

    async def fake_set(*, tenant_id: str, task_type: str, input_text: str, output: dict) -> None:
        workflow_cache[(tenant_id, task_type)] = {"input_text": input_text, "output": output}

    async def fake_get(*, tenant_id: str, task_type: str, input_text: str, threshold=None):
        record = workflow_cache.get((tenant_id, task_type))
        if record and record["input_text"] == input_text:
            return record["output"]
        return None

    monkeypatch.setattr(ai_router.semantic_cache, "set", fake_set)
    monkeypatch.setattr(ai_router.semantic_cache, "get", fake_get)

    shared_db = MockSession()

    def override_db():
        yield shared_db

    app.dependency_overrides[get_db] = override_db
    api_key = _seed_tenant_api_key(shared_db, "tenant_fullstack", name="FullStack Tenant")

    request_obj = ai_router.AiRequest(
        module="convert",
        inputs={"industry": "Marketing", "target_buyer": ai_router.DEFAULT_TARGET_BUYER},
        automation={"product": "agency"},
    )
    workflow_metadata = ai_router._convert_workflow_metadata(request_obj, ai_router.MODULE_CONFIG["convert"])
    workflow_context = ai_router._convert_workflow_context(request_obj, ai_router.MODULE_CONFIG["convert"])
    task_type = ai_router.build_workflow_memory_task_type(
        workflow_metadata["workflow_name"],
        workflow_metadata["offer_type"],
        workflow_metadata["stage"],
    )
    input_text = ai_router.build_workflow_memory_input_text(
        ai_router._convert_workflow_input_text(request_obj, ai_router.MODULE_CONFIG["convert"]),
        workflow_context,
    )
    workflow_cache[("tenant_fullstack", task_type)] = {
        "input_text": input_text,
        "output": ai_router.build_workflow_memory_envelope(
            workflow_type=workflow_metadata["workflow_name"],
            offer_type=workflow_metadata["offer_type"],
            stage=workflow_metadata["stage"],
            output={
                "pitch": {
                    "headline": "Low quality cached offer",
                    "body": "Cached body",
                    "time_saved": "5-10 hours per week",
                    "cost_equiv": "$500-$1,500/month",
                    "roi_days": 30,
                    "cta": "Want to try Agency for $30/mo?",
                },
                "template_id": "autopitch_v1",
                "product": {
                    "name": "Agency",
                    "product_id": "prod_UICyBy4ItoEBsW",
                    "payment_url": "https://buy.stripe.com/bJefZaeRR4V20iRfh5fnO02",
                    "price": "$30/mo",
                },
                "execution": {
                    "email": {"to": None, "subject": "Low quality cached offer", "body": "Cached body"},
                    "crm_payload": {},
                    "follow_up_sequence": [2, 5, 10],
                },
            },
            context=workflow_context,
            metadata=workflow_metadata,
        ),
    }

    shared_db.add(
        CRMActivityRecord(
            id="act_negative_score",
            tenant_id="tenant_fullstack",
            lead_id=None,
            deal_id=None,
            contact_id=None,
            activity_type="workflow_outcome",
            subject="Negative outcome",
            body=None,
            record_metadata={
                "task_type": task_type,
                "outcome": "rejection",
                "source": "reused",
            },
            created_at=datetime.utcnow(),
        )
    )

    client = TestClient(app)
    response = client.post(
        "/v1/ai",
        json={
            "module": "convert",
            "inputs": {
                "industry": "Marketing",
                "target_buyer": ai_router.DEFAULT_TARGET_BUYER,
            },
            "automation": {
                "product": "agency",
            },
        },
        headers={"Authorization": f"Bearer {api_key}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["output"]["pitch"]["headline"] != "Low quality cached offer"
    assert body["usage"]["workflow_memory"]["status"] == "fallback"
    assert body["usage"]["workflow_memory"]["reason"] == "low_quality_score"
    assert body["usage"]["workflow_memory"]["reuse_threshold"] == 0.0


@pytest.mark.smoke
def test_gateway_ai_convert_rejects_borderline_negative_recalled_flow(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("SIGNING_KEY", "smoke-test-signing-key-0123456789")

    app, module = _load_service_app("gateway")
    monkeypatch.setattr(module, "check_database", lambda _: (True, "ok"))
    monkeypatch.setattr(module, "check_redis", lambda _: (True, "ok"))

    from services.gateway.app.routers import ai as ai_router
    from packages.models import CRMActivityRecord
    from datetime import datetime

    monkeypatch.setattr(ai_router.settings, "enable_semantic_cache", True)

    workflow_cache: dict[tuple[str, str], dict] = {}

    async def fake_set(*, tenant_id: str, task_type: str, input_text: str, output: dict) -> None:
        workflow_cache[(tenant_id, task_type)] = {"input_text": input_text, "output": output}

    async def fake_get(*, tenant_id: str, task_type: str, input_text: str, threshold=None):
        record = workflow_cache.get((tenant_id, task_type))
        if record and record["input_text"] == input_text:
            return record["output"]
        return None

    monkeypatch.setattr(ai_router.semantic_cache, "set", fake_set)
    monkeypatch.setattr(ai_router.semantic_cache, "get", fake_get)

    shared_db = MockSession()

    def override_db():
        yield shared_db

    app.dependency_overrides[get_db] = override_db
    api_key = _seed_tenant_api_key(shared_db, "tenant_fullstack", name="FullStack Tenant")

    request_obj = ai_router.AiRequest(
        module="convert",
        inputs={"industry": "Marketing", "target_buyer": ai_router.DEFAULT_TARGET_BUYER},
        automation={"product": "agency"},
    )
    workflow_metadata = ai_router._convert_workflow_metadata(request_obj, ai_router.MODULE_CONFIG["convert"])
    workflow_context = ai_router._convert_workflow_context(request_obj, ai_router.MODULE_CONFIG["convert"])
    task_type = ai_router.build_workflow_memory_task_type(
        workflow_metadata["workflow_name"],
        workflow_metadata["offer_type"],
        workflow_metadata["stage"],
    )
    input_text = ai_router.build_workflow_memory_input_text(
        ai_router._convert_workflow_input_text(request_obj, ai_router.MODULE_CONFIG["convert"]),
        workflow_context,
    )
    workflow_cache[("tenant_fullstack", task_type)] = {
        "input_text": input_text,
        "output": ai_router.build_workflow_memory_envelope(
            workflow_type=workflow_metadata["workflow_name"],
            offer_type=workflow_metadata["offer_type"],
            stage=workflow_metadata["stage"],
            output={
                "pitch": {
                    "headline": "Borderline cached offer",
                    "body": "Cached body",
                    "time_saved": "5-10 hours per week",
                    "cost_equiv": "$500-$1,500/month",
                    "roi_days": 30,
                    "cta": "Want to try Agency for $30/mo?",
                },
                "template_id": "autopitch_v1",
                "product": {
                    "name": "Agency",
                    "product_id": "prod_UICyBy4ItoEBsW",
                    "payment_url": "https://buy.stripe.com/bJefZaeRR4V20iRfh5fnO02",
                    "price": "$30/mo",
                },
                "execution": {
                    "email": {"to": None, "subject": "Borderline cached offer", "body": "Cached body"},
                    "crm_payload": {},
                    "follow_up_sequence": [2, 5, 10],
                },
            },
            context=workflow_context,
            metadata=workflow_metadata,
        ),
    }

    for idx, outcome in enumerate(["send_approval", "delivered", "rejection"]):
        shared_db.add(
            CRMActivityRecord(
                id=f"act_borderline_{idx}",
                tenant_id="tenant_fullstack",
                lead_id=None,
                deal_id=None,
                contact_id=None,
                activity_type="workflow_outcome",
                subject=f"borderline:{outcome}",
                body=None,
                record_metadata={
                    "task_type": task_type,
                    "outcome": outcome,
                    "source": "reused",
                },
                created_at=datetime.utcnow(),
            )
        )

    client = TestClient(app)
    response = client.post(
        "/v1/ai",
        json={
            "module": "convert",
            "inputs": {
                "industry": "Marketing",
                "target_buyer": ai_router.DEFAULT_TARGET_BUYER,
            },
            "automation": {
                "product": "agency",
            },
        },
        headers={"Authorization": f"Bearer {api_key}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["output"]["pitch"]["headline"] != "Borderline cached offer"
    assert body["usage"]["workflow_memory"]["status"] == "fallback"
    assert body["usage"]["workflow_memory"]["reason"] == "low_quality_score"
    assert body["usage"]["workflow_memory"]["score"] == -0.3333333333333333
    assert body["usage"]["workflow_memory"]["reuse_threshold"] == 0.0


@pytest.mark.smoke
def test_core_registry_roundtrip(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

    app, module = _load_service_app("core")
    monkeypatch.setattr(module, "check_database", lambda _: (True, "ok"))
    monkeypatch.setattr(module, "check_redis", lambda _: (True, "ok"))

    client = TestClient(app)
    register = client.post(
        "/registry/register",
        json={
            "service_id": "svc_smoke",
            "service_type": "vertical",
            "endpoint": "http://svc-smoke",
            "port": 8080,
            "version": "1.0.0",
            "capabilities": ["summary"],
            "metadata": {"tier": "staging"},
        },
    )
    assert register.status_code == 200

    discovered = client.post("/registry/discover?capability=summary")
    assert discovered.status_code == 200
    assert discovered.json()[0]["service_id"] == "svc_smoke"
