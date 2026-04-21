from __future__ import annotations

import importlib
import sys
import types
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from packages.db import get_db
from packages.models import SidecarParoleVerdict, SidecarPersona, SidecarScorecard
from tests.conftest import MockSession


def _load_gateway_app():
    module_path = "services.gateway.app.main"
    module_prefix = module_path.rsplit(".", 1)[0]
    if "redis" not in sys.modules:
        sys.modules["redis"] = types.SimpleNamespace(Redis=object)
    if "jwt" not in sys.modules:
        sys.modules["jwt"] = types.SimpleNamespace(
            encode=lambda *args, **kwargs: "test-token",
            decode=lambda *args, **kwargs: {"sub": "tenant_test"},
            InvalidTokenError=Exception,
            ExpiredSignatureError=Exception,
            InvalidSignatureError=Exception,
            DecodeError=Exception,
        )
    for module_name in list(sys.modules):
        if module_name == module_prefix or module_name.startswith(f"{module_prefix}."):
            sys.modules.pop(module_name)
    module = importlib.import_module(module_path)
    return module.app, module


def test_governance_admin_routes(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("SIGNING_KEY", "governance-test-signing-key")
    monkeypatch.setenv("ADMIN_TOKEN", "governance-admin-token")

    app, module = _load_gateway_app()
    monkeypatch.setattr(module, "check_database", lambda _: (True, "ok"))
    monkeypatch.setattr(module, "check_redis", lambda _: (True, "ok"))

    shared_db = MockSession()
    now = datetime.now(timezone.utc)
    shared_db.add(
        SidecarPersona(
            id="persona_1",
            tenant_id="tenant_one",
            display_name="Tenant One Persona",
            owner_tenant="tenant_one",
            state="active",
            created_at=now - timedelta(hours=2),
            updated_at=now - timedelta(hours=1),
        )
    )
    shared_db.add(
        SidecarPersona(
            id="persona_2",
            tenant_id="tenant_two",
            display_name="Tenant Two Persona",
            owner_tenant="tenant_two",
            state="probation",
            created_at=now - timedelta(hours=3),
            updated_at=now - timedelta(hours=2),
        )
    )
    shared_db.add(
        SidecarParoleVerdict(
            id="vrd_new",
            persona_id="persona_1",
            tenant_id="tenant_one",
            request_id="req_001",
            checkpoint="intake",
            verdict="hold",
            battery_scores={"identity": 0.33, "boundary": 1.0},
            drift_score=None,
            yard_match_score=0.23,
            yard_match_id="yard_escape",
            reasoning="score=50/100",
            shadow_mode=True,
            created_at=now,
        )
    )
    shared_db.add(
        SidecarParoleVerdict(
            id="vrd_old",
            persona_id="persona_2",
            tenant_id="tenant_two",
            request_id="req_002",
            checkpoint="probation",
            verdict="approve",
            battery_scores={"identity": 0.91},
            drift_score=0.12,
            yard_match_score=0.71,
            yard_match_id=None,
            reasoning="score=100/100",
            shadow_mode=False,
            created_at=now - timedelta(minutes=30),
        )
    )
    shared_db.add(
        SidecarScorecard(
            id="sc_001",
            persona_id="persona_1",
            tenant_id="tenant_one",
            request_id="req_001",
            checkpoint="intake",
            battery="identity",
            scores={"overall": 0.33},
            total_tokens=31,
            latency_ms=4,
            cost_usd=0.0,
            passed=False,
            created_at=now,
        )
    )

    def override_db():
        yield shared_db

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    headers = {"X-Admin-Token": "governance-admin-token"}

    summary = client.get("/v1/admin/governance/summary", headers=headers)
    assert summary.status_code == 200
    summary_body = summary.json()
    assert summary_body["total_verdicts"] == 2
    assert summary_body["shadow_mode_count"] == 1
    assert summary_body["enforced_count"] == 1
    assert summary_body["verdict_counts"]["hold"] == 1
    assert summary_body["checkpoint_counts"]["intake"] == 1

    verdicts = client.get(
        "/v1/admin/governance/verdicts?tenant_id=tenant_one&shadow_mode=true",
        headers=headers,
    )
    assert verdicts.status_code == 200
    verdict_rows = verdicts.json()
    assert len(verdict_rows) == 1
    assert verdict_rows[0]["verdict_id"] == "vrd_new"
    assert verdict_rows[0]["persona_display_name"] == "Tenant One Persona"
    assert verdict_rows[0]["persona_state"] == "active"
    assert verdict_rows[0]["scorecards"][0]["battery"] == "identity"
