from __future__ import annotations

import importlib
import sys
import types
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from packages.db import get_db
from packages.models import (
    BuildingElementRecord,
    DocumentChunkRecord,
    IngestionJob,
    IssueRecord,
    Project,
    ProjectFile,
    SidecarParoleVerdict,
    Tenant,
    TenantActorRoleRecord,
    WorkflowRunRecord,
)
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


def test_digital_twin_project_summary(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("SIGNING_KEY", "digital-twin-test-signing-key")
    monkeypatch.setenv("ADMIN_TOKEN", "digital-twin-admin-token")

    app, module = _load_gateway_app()
    monkeypatch.setattr(module, "check_database", lambda _: (True, "ok"))
    monkeypatch.setattr(module, "check_redis", lambda _: (True, "ok"))

    db = MockSession()
    now = datetime.now(timezone.utc)
    db.add(Tenant(id="tenant_one", name="Tenant One", is_active=True, created_at=now, updated_at=now, plan="enterprise"))
    db.add(
        TenantActorRoleRecord(
            id="actor_role_1",
            tenant_id="tenant_one",
            actor_id="actor_1",
            display_name="Ops Lead",
            role="operator",
            granted_permissions=["projects:read", "twins:read"],
            denied_permissions=[],
            is_active=True,
            created_at=now - timedelta(days=10),
            updated_at=now - timedelta(hours=3),
        )
    )
    db.add(Project(id="proj_1", tenant_id="tenant_one", name="Twin One", created_at=now - timedelta(days=1)))
    db.add(ProjectFile(id="file_ifc", project_id="proj_1", tenant_id="tenant_one", file_type="ifc", storage_path="gs://bucket/file.ifc", registered_at=now - timedelta(hours=6)))
    db.add(ProjectFile(id="file_pdf", project_id="proj_1", tenant_id="tenant_one", file_type="pdf", storage_path="gs://bucket/file.pdf", registered_at=now - timedelta(hours=5)))
    db.add(IngestionJob(id="job_1", file_id="file_ifc", project_id="proj_1", tenant_id="tenant_one", status="complete", entities_created=24, error_log=None, created_at=now - timedelta(hours=5), updated_at=now - timedelta(hours=4)))
    db.add(
        BuildingElementRecord(
            id="elem_1",
            project_id="proj_1",
            source_file_id="file_ifc",
            category="IfcRoof",
            properties={"system": "solar-ready", "exposure": "high-wind exterior envelope"},
            created_at=now - timedelta(hours=4),
        )
    )
    db.add(
        DocumentChunkRecord(
            id="chunk_1",
            file_id="file_pdf",
            page=1,
            text="Roof solar panel exposure study with wind uplift, storm drainage, and freeze weather notes.",
            confidence=0.91,
        )
    )
    db.add(IssueRecord(id="issue_1", project_id="proj_1", type="weather_fallout", severity="high", source_refs=["chunk_1"], confidence=0.88))
    db.add(WorkflowRunRecord(id="wf_1", tenant_id="tenant_one", project_id="proj_1", type="coordination", status="failed", current_step="review", checkpoint={}, created_at=now - timedelta(hours=2), updated_at=now - timedelta(minutes=30)))
    db.add(
        SidecarParoleVerdict(
            id="vrd_1",
            persona_id="persona_tenant_one",
            tenant_id="tenant_one",
            request_id="req_1",
            checkpoint="intake",
            verdict="reject",
            battery_scores={"identity": 0.22},
            drift_score=0.71,
            yard_match_score=0.11,
            yard_match_id="yard_risk",
            reasoning="operational turbulence detected",
            shadow_mode=True,
            created_at=now - timedelta(hours=1),
        )
    )

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    response = client.get("/v1/admin/digital-twins/projects?tenant_id=tenant_one", headers={"X-Admin-Token": "digital-twin-admin-token"})
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["project_id"] == "proj_1"
    assert body[0]["twin_status"] == "active"
    assert body[0]["twin_version"] == "0.3.0"
    assert body[0]["building_element_count"] == 1
    assert body[0]["document_chunk_count"] == 1
    assert body[0]["high_severity_issue_count"] == 1
    assert "high_severity_issues" in body[0]["alerts"]
    assert body[0]["operational_predictability"]["band"] in {"volatile", "low", "moderate", "high"}
    assert body[0]["operational_predictability"]["confidence"] > 0
    operational_keys = {factor["key"] for factor in body[0]["operational_predictability"]["factors"]}
    assert "human_interaction" in operational_keys
    assert "bad_actor_pressure" in operational_keys
    assert "fallout_risk" in operational_keys

    assert body[0]["environmental_predictability"]["band"] in {"volatile", "low", "moderate", "high"}
    assert body[0]["environmental_predictability"]["confidence"] > 0
    environmental_keys = {factor["key"] for factor in body[0]["environmental_predictability"]["factors"]}
    assert "weather_exposure" in environmental_keys
    assert "solar_exposure" in environmental_keys
    assert "wind_exposure" in environmental_keys
