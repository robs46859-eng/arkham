"""Gateway CRM router tests."""

from __future__ import annotations

import importlib
import sys

from fastapi.testclient import TestClient

from packages.db import get_db
from packages.models import Tenant, TenantActorRoleRecord
from tests.conftest import MockSession


def _load_gateway_app():
    module_path = "services.gateway.app.main"
    module_prefix = module_path.rsplit(".", 1)[0]
    for module_name in list(sys.modules):
        if module_name == module_prefix or module_name.startswith(f"{module_prefix}."):
            sys.modules.pop(module_name)
    module = importlib.import_module(module_path)
    return module.app, module


def test_crm_roundtrip_context(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("SIGNING_KEY", "crm-test-signing-key-0123456789")

    app, module = _load_gateway_app()
    monkeypatch.setattr(module, "check_database", lambda _: (True, "ok"))
    monkeypatch.setattr(module, "check_redis", lambda _: (True, "ok"))

    shared_db = MockSession()
    shared_db.add(
        Tenant(
            id="tenant_crm",
            name="CRM Tenant",
            is_active=True,
            created_at=__import__("datetime").datetime.utcnow(),
            updated_at=__import__("datetime").datetime.utcnow(),
            plan="free",
        )
    )

    def override_db():
        yield shared_db

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    headers = {"X-Tenant-Id": "tenant_crm", "X-Project-Id": "proj_crm"}

    company = client.post(
        "/v1/crm/companies",
        json={"name": "Apollo Agency", "website": "https://apollo.example"},
        headers=headers,
    )
    assert company.status_code == 200
    company_id = company.json()["company_id"]

    contact = client.post(
        "/v1/crm/contacts",
        json={
            "company_id": company_id,
            "first_name": "Ada",
            "last_name": "Stone",
            "email": "ada@example.com",
            "title": "Founder",
        },
        headers=headers,
    )
    assert contact.status_code == 200
    contact_id = contact.json()["contact_id"]

    lead = client.post(
        "/v1/crm/leads",
        json={
            "company_id": company_id,
            "contact_id": contact_id,
            "source": "csv",
            "status": "new",
            "fit_score": 0.91,
            "metadata": {"list": "apollo"},
        },
        headers=headers,
    )
    assert lead.status_code == 200
    lead_id = lead.json()["lead_id"]

    activity = client.post(
        "/v1/crm/activities",
        json={
            "lead_id": lead_id,
            "activity_type": "note",
            "subject": "Agent research",
            "body": "Strong candidate for outreach.",
        },
        headers=headers,
    )
    assert activity.status_code == 200

    context = client.get("/v1/crm/context", headers=headers)
    assert context.status_code == 200
    body = context.json()
    assert body["totals"]["companies"] == 1
    assert body["totals"]["contacts"] == 1
    assert body["totals"]["leads"] == 1
    assert body["totals"]["activities"] == 1
    assert body["companies"][0]["name"] == "Apollo Agency"
    assert body["contacts"][0]["email"] == "ada@example.com"


def test_workflow_memory_store_and_recall(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("SIGNING_KEY", "crm-test-signing-key-0123456789")

    app, module = _load_gateway_app()
    monkeypatch.setattr(module, "check_database", lambda _: (True, "ok"))
    monkeypatch.setattr(module, "check_redis", lambda _: (True, "ok"))

    from services.gateway.app.routers import crm as crm_router

    monkeypatch.setattr(crm_router.settings, "enable_semantic_cache", True)

    cache_store: dict[tuple[str, str], dict] = {}

    async def fake_set(*, tenant_id: str, task_type: str, input_text: str, output: dict) -> None:
        cache_store[(tenant_id, task_type)] = {"input_text": input_text, "output": output}

    async def fake_get(*, tenant_id: str, task_type: str, input_text: str, threshold=None):
        record = cache_store.get((tenant_id, task_type))
        if record and record["input_text"] == input_text:
            return record["output"]
        return None

    monkeypatch.setattr(crm_router.semantic_cache, "set", fake_set)
    monkeypatch.setattr(crm_router.semantic_cache, "get", fake_get)

    shared_db = MockSession()
    shared_db.add(
        Tenant(
            id="tenant_crm",
            name="CRM Tenant",
            is_active=True,
            created_at=__import__("datetime").datetime.utcnow(),
            updated_at=__import__("datetime").datetime.utcnow(),
            plan="free",
        )
    )

    def override_db():
        yield shared_db

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    headers = {"X-Tenant-Id": "tenant_crm", "X-Project-Id": "proj_crm"}

    store = client.post(
        "/v1/crm/workflow-memory/store",
        json={
            "workflow_type": "fullstack_outreach",
            "offer_type": "agency",
            "stage": "first_touch",
            "input_text": "Founder at an agency already using HubSpot and Make.",
            "context": {"industry": "marketing", "company_size": "1-10"},
            "output": {"subject": "Cut manual outreach time", "body": "Discover -> Monitor -> Convert"},
            "metadata": {"won": True},
        },
        headers=headers,
    )
    assert store.status_code == 200
    assert store.json()["stored"] is True
    assert store.json()["task_type"] == "crm_flow:fullstack_outreach:agency:first_touch"

    recall = client.post(
        "/v1/crm/workflow-memory/recall",
        json={
            "workflow_type": "fullstack_outreach",
            "offer_type": "agency",
            "stage": "first_touch",
            "input_text": "Founder at an agency already using HubSpot and Make.",
            "context": {"industry": "marketing", "company_size": "1-10"},
        },
        headers=headers,
    )
    assert recall.status_code == 200
    assert recall.json()["cache_hit"] is True
    assert recall.json()["output"]["subject"] == "Cut manual outreach time"


def test_workflow_outcome_scoring(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("SIGNING_KEY", "crm-test-signing-key-0123456789")
    monkeypatch.setenv("ADMIN_TOKEN", "crm-admin-token")

    app, module = _load_gateway_app()
    monkeypatch.setattr(module, "check_database", lambda _: (True, "ok"))
    monkeypatch.setattr(module, "check_redis", lambda _: (True, "ok"))

    shared_db = MockSession()
    shared_db.add(
        Tenant(
            id="tenant_crm",
            name="CRM Tenant",
            is_active=True,
            created_at=__import__("datetime").datetime.utcnow(),
            updated_at=__import__("datetime").datetime.utcnow(),
            plan="free",
        )
    )

    def override_db():
        yield shared_db

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    headers = {"X-Tenant-Id": "tenant_crm", "X-Project-Id": "proj_crm"}

    delivered = client.post(
        "/v1/crm/workflow-memory/outcome",
        json={
            "workflow_type": "fullstack_outreach",
            "offer_type": "agency",
            "stage": "first_touch",
            "outcome": "delivered",
            "source": "reused",
        },
        headers=headers,
    )
    assert delivered.status_code == 200
    assert delivered.json()["score"] == 2.0

    rejection = client.post(
        "/v1/crm/workflow-memory/outcome",
        json={
            "workflow_type": "fullstack_outreach",
            "offer_type": "agency",
            "stage": "first_touch",
            "outcome": "rejection",
            "source": "reused",
        },
        headers=headers,
    )
    assert rejection.status_code == 200
    assert rejection.json()["counts"]["delivered"] == 1
    assert rejection.json()["counts"]["rejection"] == 1
    assert rejection.json()["score"] == -1.0

    config = client.get("/v1/crm/workflow-memory/config", headers={"X-Admin-Token": "crm-admin-token"})
    assert config.status_code == 200
    assert config.json()["configured_reuse_min_score"] == -0.5
    assert config.json()["effective_reuse_min_score"] == 0.0
    assert config.json()["auto_reuse_score_floor"] == 0.0
    assert config.json()["outcome_weights"]["reply"] == 5.0

    updated = client.patch(
        "/v1/crm/workflow-memory/config",
        json={
            "reuse_min_score": 0.25,
            "outcome_weights": {
                "send_approval": 1.0,
                "delivered": 1.5,
                "reply": 4.5,
                "booking": 8.0,
                "rejection": -5.0,
            },
        },
        headers={"X-Admin-Token": "crm-admin-token"},
    )
    assert updated.status_code == 200
    assert updated.json()["configured_reuse_min_score"] == 0.25
    assert updated.json()["effective_reuse_min_score"] == 0.25
    assert updated.json()["outcome_weights"]["delivered"] == 1.5

    metrics = client.get(
        "/v1/crm/workflow-memory/metrics/tenant_crm"
        "?workflow_type=fullstack_outreach&offer_type=agency&stage=first_touch",
        headers={"X-Admin-Token": "crm-admin-token"},
    )
    assert metrics.status_code == 200
    body = metrics.json()
    assert body["outcome_counts"]["delivered"] == 1
    assert body["outcome_counts"]["rejection"] == 1
    assert body["outcome_score"] == -1.75


def test_workflow_review_queue_import_and_approval(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("SIGNING_KEY", "crm-test-signing-key-0123456789")
    monkeypatch.setenv("ADMIN_TOKEN", "crm-admin-token")

    app, module = _load_gateway_app()
    monkeypatch.setattr(module, "check_database", lambda _: (True, "ok"))
    monkeypatch.setattr(module, "check_redis", lambda _: (True, "ok"))

    shared_db = MockSession()
    now = __import__("datetime").datetime.utcnow()
    shared_db.add(
        Tenant(
            id="tenant_crm",
            name="CRM Tenant",
            is_active=True,
            created_at=now,
            updated_at=now,
            plan="free",
        )
    )

    def override_db():
        yield shared_db

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    admin_headers = {"X-Admin-Token": "crm-admin-token", "X-Admin-Actor": "operator.one"}

    imported = client.post(
        "/v1/crm/workflow-review-queue/import",
        json={
            "batch_label": "shadow-batch-a",
            "source_artifact": "artifacts/shadow-runs/sample.json",
            "items": [
                {
                    "tenant_id": "tenant_crm",
                    "case_name": "borderline_regenerate",
                    "request_id": "req_123",
                    "lead": {
                        "name": "Ada Stone",
                        "company": "Apollo Agency",
                        "email": "ada@example.com",
                    },
                    "eligibility": {"status": "sendable"},
                    "decision": {"status": "fallback", "reason": "low_quality_score"},
                    "output_preview": {"headline": "Automation that ships"},
                    "execution_contract": {
                        "channel": "email",
                        "provider_mode": "dry_run",
                        "to": "ada@example.com",
                        "subject": "Automation that ships",
                        "body": "Ada, here is the controlled preview.",
                        "product": {"name": "Agency", "payment_url": "https://example.com/pay"},
                        "follow_up_sequence": [2, 5, 10],
                        "crm_payload": {"industry": "marketing"},
                    },
                    "workflow_context": {
                        "workflow_type": "fullstack_outreach",
                        "offer_type": "agency",
                        "stage": "first_touch",
                    },
                },
                {
                    "tenant_id": "tenant_crm",
                    "case_name": "incomplete_skip",
                    "request_id": "req_456",
                    "lead": {
                        "name": "No Email",
                        "company": "Missing Mail Co",
                        "email": "",
                    },
                    "eligibility": {"status": "incomplete"},
                    "decision": {"status": "skipped_preflight", "reason": "incomplete_lead"},
                    "output_preview": {},
                },
            ],
        },
        headers=admin_headers,
    )
    assert imported.status_code == 200
    body = imported.json()
    assert len(body) == 2
    assert body[0]["review_status"] == "pending"
    assert body[1]["review_status"] == "skipped"

    queue = client.get("/v1/crm/workflow-review-queue/tenant_crm", headers=admin_headers)
    assert queue.status_code == 200
    items = queue.json()
    assert len(items) == 2

    review_item_id = body[0]["review_item_id"]
    updated = client.patch(
        f"/v1/crm/workflow-review-queue/items/{review_item_id}",
        json={
            "review_status": "approved",
            "reviewer_name": "Operator One",
            "reviewer_notes": "Safe to move into controlled live review.",
        },
        headers=admin_headers,
    )
    assert updated.status_code == 200
    updated_body = updated.json()
    assert updated_body["review_status"] == "approved"
    history = updated_body["metadata"]["queue_state_history"]
    assert history[0]["review_status"] == "pending"
    assert history[0]["tenant_id"] == "tenant_crm"
    assert history[-1]["review_status"] == "approved"
    assert history[-1]["actor"] == "operator.one"
    assert updated_body["metadata"]["decision"]["reason"] == "low_quality_score"

    blocked = client.post(
        f"/v1/crm/workflow-review-queue/items/{body[1]['review_item_id']}/execution",
        json={"execution_status": "queued", "metadata": {"mode": "shadow"}},
        headers=admin_headers,
    )
    assert blocked.status_code == 409

    executed = client.post(
        f"/v1/crm/workflow-review-queue/items/{review_item_id}/execution",
        json={"execution_status": "queued", "metadata": {"mode": "shadow"}},
        headers=admin_headers,
    )
    assert executed.status_code == 200
    execution = executed.json()
    assert execution["review_item_id"] == review_item_id
    assert execution["execution_status"] == "queued"
    assert execution["metadata"]["tenant_id"] == "tenant_crm"
    assert execution["metadata"]["actor"] == "operator.one"
    assert execution["metadata"]["review_item_snapshot"]["review_status"] == "approved"
    assert execution["metadata"]["review_item_snapshot"]["tenant_id"] == "tenant_crm"
    assert execution["metadata"]["queue_state_history"][-1]["review_status"] == "approved"
    assert execution["metadata"]["requested_execution"]["mode"] == "shadow"

    delivered = client.post(
        f"/v1/crm/workflow-executions/{execution['execution_id']}/deliver",
        json={"metadata": {"adapter": "smtp-email", "mode": "simulation"}},
        headers=admin_headers,
    )
    assert delivered.status_code == 200
    delivery = delivered.json()
    assert delivery["execution_id"] == execution["execution_id"]
    assert delivery["channel"] == "email"
    assert delivery["provider"] == "dry_run"
    assert delivery["delivery_status"] == "dry_run"
    assert delivery["metadata"]["tenant_id"] == "tenant_crm"
    assert delivery["metadata"]["actor"] == "operator.one"
    assert delivery["metadata"]["review_snapshot"]["review_status"] == "approved"
    assert delivery["metadata"]["review_snapshot"]["tenant_id"] == "tenant_crm"
    assert delivery["metadata"]["attempt_contract"]["to"] == "ada@example.com"
    assert delivery["metadata"]["requested_delivery"]["adapter"] == "smtp-email"

    delivery_list = client.get(
        f"/v1/crm/workflow-executions/{execution['execution_id']}/deliveries",
        headers=admin_headers,
    )
    assert delivery_list.status_code == 200
    deliveries = delivery_list.json()
    assert len(deliveries) == 1
    assert deliveries[0]["delivery_id"] == delivery["delivery_id"]
    assert deliveries[0]["metadata"]["execution_snapshot"]["tenant_id"] == "tenant_crm"
    updated_body = updated.json()
    assert updated_body["review_status"] == "approved"
    assert updated_body["reviewer_name"] == "Operator One"
    assert updated_body["reviewer_notes"] == "Safe to move into controlled live review."


def test_tenant_actor_roles_and_permission_enforcement(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("SIGNING_KEY", "crm-test-signing-key-0123456789")
    monkeypatch.setenv("ADMIN_TOKEN", "crm-admin-token")

    app, module = _load_gateway_app()
    monkeypatch.setattr(module, "check_database", lambda _: (True, "ok"))
    monkeypatch.setattr(module, "check_redis", lambda _: (True, "ok"))

    shared_db = MockSession()
    now = __import__("datetime").datetime.utcnow()
    shared_db.add(
        Tenant(
            id="tenant_crm",
            name="CRM Tenant",
            is_active=True,
            created_at=now,
            updated_at=now,
            plan="free",
        )
    )

    def override_db():
        yield shared_db

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    owner_headers = {"X-Admin-Token": "crm-admin-token", "X-Admin-Actor": "owner.one"}

    owner_role = client.put(
        "/v1/tenants/tenant_crm/actors/owner.one",
        json={
            "actor_id": "owner.one",
            "display_name": "Owner One",
            "role": "owner",
        },
        headers=owner_headers,
    )
    assert owner_role.status_code == 200
    assert "tenant.members.manage" in owner_role.json()["permissions"]

    reviewer_role = client.put(
        "/v1/tenants/tenant_crm/actors/reviewer.one",
        json={
            "actor_id": "reviewer.one",
            "display_name": "Reviewer One",
            "role": "reviewer",
        },
        headers=owner_headers,
    )
    assert reviewer_role.status_code == 200
    assert reviewer_role.json()["role"] == "reviewer"
    assert "workflow.review" in reviewer_role.json()["permissions"]
    assert "workflow.deliver" not in reviewer_role.json()["permissions"]

    operator_role = client.put(
        "/v1/tenants/tenant_crm/actors/operator.one",
        json={
            "actor_id": "operator.one",
            "display_name": "Operator One",
            "role": "operator",
        },
        headers=owner_headers,
    )
    assert operator_role.status_code == 200
    assert "workflow.execute" in operator_role.json()["permissions"]
    assert "workflow.deliver" in operator_role.json()["permissions"]

    me = client.get("/v1/tenants/tenant_crm/actors/me", headers={"X-Admin-Token": "crm-admin-token", "X-Admin-Actor": "reviewer.one"})
    assert me.status_code == 200
    assert me.json()["role"] == "reviewer"

    imported = client.post(
        "/v1/crm/workflow-review-queue/import",
        json={
            "batch_label": "roles-batch",
            "items": [
                {
                    "tenant_id": "tenant_crm",
                    "case_name": "permission_case",
                    "request_id": "req_role_1",
                    "lead": {"name": "Ada Stone", "company": "Apollo Agency", "email": "ada@example.com"},
                    "eligibility": {"status": "sendable"},
                    "decision": {"status": "fallback", "reason": "not_found"},
                    "execution_contract": {
                        "channel": "email",
                        "provider_mode": "dry_run",
                        "to": "ada@example.com",
                        "subject": "Automation that ships",
                        "body": "Ada, here is the controlled preview.",
                    },
                    "workflow_context": {
                        "workflow_type": "fullstack_outreach",
                        "offer_type": "agency",
                        "stage": "first_touch",
                    },
                }
            ],
        },
        headers={"X-Admin-Token": "crm-admin-token", "X-Admin-Actor": "reviewer.one"},
    )
    assert imported.status_code == 200
    review_item_id = imported.json()[0]["review_item_id"]

    approved = client.patch(
        f"/v1/crm/workflow-review-queue/items/{review_item_id}",
        json={"review_status": "approved", "reviewer_name": "Reviewer One", "reviewer_notes": "Reviewed"},
        headers={"X-Admin-Token": "crm-admin-token", "X-Admin-Actor": "reviewer.one"},
    )
    assert approved.status_code == 200

    denied_execution = client.post(
        f"/v1/crm/workflow-review-queue/items/{review_item_id}/execution",
        json={"execution_status": "queued", "metadata": {"mode": "role-test"}},
        headers={"X-Admin-Token": "crm-admin-token", "X-Admin-Actor": "reviewer.one"},
    )
    assert denied_execution.status_code == 403

    execution = client.post(
        f"/v1/crm/workflow-review-queue/items/{review_item_id}/execution",
        json={"execution_status": "queued", "metadata": {"mode": "role-test"}},
        headers={"X-Admin-Token": "crm-admin-token", "X-Admin-Actor": "operator.one"},
    )
    assert execution.status_code == 200

    denied_delivery = client.post(
        f"/v1/crm/workflow-executions/{execution.json()['execution_id']}/deliver",
        json={"metadata": {"mode": "role-test"}},
        headers={"X-Admin-Token": "crm-admin-token", "X-Admin-Actor": "reviewer.one"},
    )
    assert denied_delivery.status_code == 403

    allowed_delivery = client.post(
        f"/v1/crm/workflow-executions/{execution.json()['execution_id']}/deliver",
        json={"metadata": {"mode": "role-test"}},
        headers={"X-Admin-Token": "crm-admin-token", "X-Admin-Actor": "operator.one"},
    )
    assert allowed_delivery.status_code == 200
