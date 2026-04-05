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
def test_core_registry_roundtrip(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

    app, module = _load_service_app("core")
    monkeypatch.setattr(module, "check_database", lambda _: (True, "ok"))
    monkeypatch.setattr(module, "check_redis", lambda _: (True, "ok"))

    client = TestClient(app)
    register = client.post(
        "/register",
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

    discovered = client.post("/discover?capability=summary")
    assert discovered.status_code == 200
    assert discovered.json()[0]["service_id"] == "svc_smoke"
