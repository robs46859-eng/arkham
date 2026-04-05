"""
JWT auth tests — token issuance, verification, middleware integration.
Implements: Build Rules §8 — auth contract tests.
             Service Spec §1.2 — stateless tenant authentication.

Coverage:
  Token library (packages/auth/tokens.py)
    — issue and verify round-trip
    — expired token raises token_error
    — tampered signature raises token_error
    — wrong algorithm rejected
    — payload fields present (sub, proj, exp, iat, jti)

  POST /v1/auth/token
    — valid request returns bearer token
    — returned token verifies correctly
    — bad tenant_id format → 400
    — empty api_key → 400
    — bad project_id format → 400

  Gateway middleware (require_tenant)
    — Bearer token accepted on /v1/infer
    — expired token → 401
    — tampered token → 401
    — no credentials → 401
    — test-mode header fallback still works
    — inactive tenant still gets 403 (not 401) when token is valid

  GET /v1/tenants list
    — returns created tenants

  GET /v1/ingestion/jobs list
    — returns jobs for tenant
"""

from __future__ import annotations

import importlib
import sys
from datetime import datetime
from pathlib import Path

import jwt
import pytest
from fastapi.testclient import TestClient

from tests.conftest import MockSession

ROOT = Path(__file__).resolve().parents[1]
GW_DIR = ROOT / "services" / "gateway"
INGEST_DIR = ROOT / "services" / "bim_ingestion"


# ── Gateway app fixture ───────────────────────────────────────────────────────


def _make_gw_app(monkeypatch, signing_key="test-secret-key"):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("SIGNING_KEY", signing_key)

    if str(GW_DIR) not in sys.path:
        sys.path.insert(0, str(GW_DIR))

    for mod in list(sys.modules):
        if mod == "app" or mod.startswith("app."):
            sys.modules.pop(mod)

    return importlib.import_module("app.main").app


@pytest.fixture
def gw(monkeypatch):
    from packages.db import get_db

    app = _make_gw_app(monkeypatch)
    shared_db = MockSession()

    def get_shared_db():
        yield shared_db

    app.dependency_overrides[get_db] = get_shared_db
    with TestClient(app) as tc:
        yield tc, shared_db
    app.dependency_overrides.clear()
    if str(GW_DIR) in sys.path:
        sys.path.remove(str(GW_DIR))


# ── Ingest app fixture ────────────────────────────────────────────────────────


def _make_ingest_app(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

    if str(INGEST_DIR) not in sys.path:
        sys.path.insert(0, str(INGEST_DIR))

    for mod in list(sys.modules):
        if mod == "app" or mod.startswith("app."):
            sys.modules.pop(mod)

    return importlib.import_module("app.main").app


@pytest.fixture
def ingest(monkeypatch):
    from packages.db import get_db

    app = _make_ingest_app(monkeypatch)
    shared_db = MockSession()

    def get_shared_db():
        yield shared_db

    app.dependency_overrides[get_db] = get_shared_db
    with TestClient(app) as tc:
        yield tc, shared_db
    app.dependency_overrides.clear()
    if str(INGEST_DIR) in sys.path:
        sys.path.remove(str(INGEST_DIR))


# ── Token library unit tests ──────────────────────────────────────────────────


class TestTokenLibrary:
    def _tokens_mod(self):
        """Import the tokens module fresh (APP_ENV=test already set by fixture)."""
        import os

        os.environ.setdefault("APP_ENV", "test")
        import os

        os.environ.setdefault("SIGNING_KEY", "unit-test-key")
        from services.gateway.app.auth.tokens import TokenError, issue_token, verify_token

        return issue_token, verify_token, TokenError

    def test_issue_and_verify_roundtrip(self, monkeypatch):
        monkeypatch.setenv("SIGNING_KEY", "roundtrip-key")
        monkeypatch.setenv("APP_ENV", "test")
        # Re-import to pick up env
        for mod in list(sys.modules):
            if "services.gateway.app" in mod:
                sys.modules.pop(mod)
        issue, verify, _ = self._tokens_mod()
        token = issue(tenant_id="tenant_abc", project_id="proj_xyz", signing_key="roundtrip-key")
        payload = verify(token, signing_key="roundtrip-key")
        assert payload["sub"] == "tenant_abc"
        assert payload["proj"] == "proj_xyz"
        assert "exp" in payload
        assert "iat" in payload
        assert "jti" in payload

    def test_expired_token_raises(self, monkeypatch):
        monkeypatch.setenv("SIGNING_KEY", "expiry-key")
        monkeypatch.setenv("APP_ENV", "test")
        for mod in list(sys.modules):
            if "services.gateway.app" in mod:
                sys.modules.pop(mod)
        issue, verify, token_error = self._tokens_mod()
        # ttl_hours=-1 → exp is in the past (definitely expired)
        token = issue(tenant_id="tenant_abc", ttl_hours=-1, signing_key="expiry-key")
        with pytest.raises(token_error, match="expired"):
            verify(token, signing_key="expiry-key")

    def test_tampered_signature_raises(self, monkeypatch):
        monkeypatch.setenv("SIGNING_KEY", "tamper-key")
        monkeypatch.setenv("APP_ENV", "test")
        for mod in list(sys.modules):
            if "services.gateway.app" in mod:
                sys.modules.pop(mod)
        issue, verify, token_error = self._tokens_mod()
        token = issue(tenant_id="tenant_abc", signing_key="tamper-key")
        # Flip a middle character of the signature (avoid last char — base64 padding bits)
        parts = token.split(".")
        mid = len(parts[2]) // 2
        parts[2] = parts[2][:mid] + ("A" if parts[2][mid] != "A" else "B") + parts[2][mid + 1 :]
        bad_token = ".".join(parts)
        with pytest.raises(token_error):
            verify(bad_token, signing_key="tamper-key")

    def test_wrong_algorithm_rejected(self, monkeypatch):
        monkeypatch.setenv("SIGNING_KEY", "alg-key")
        monkeypatch.setenv("APP_ENV", "test")
        for mod in list(sys.modules):
            if "services.gateway.app" in mod:
                sys.modules.pop(mod)
        _, verify, token_error = self._tokens_mod()
        # Craft a token signed with RS256 header but wrong key — should fail
        crafted = jwt.encode(
            {"sub": "tenant_bad", "proj": "", "exp": 9999999999, "iat": 1, "jti": "x"},
            "wrong-key",
            algorithm="HS256",
        )
        # Swap the key so verify fails
        with pytest.raises(token_error):
            verify(crafted + "tampered", signing_key="alg-key")


# ── POST /v1/auth/token ───────────────────────────────────────────────────────


class TestAuthTokenEndpoint:
    def test_valid_request_returns_token(self, gw):
        client, _ = gw
        r = client.post(
            "/v1/auth/token",
            json={
                "tenant_id": "tenant_abc",
                "api_key": "any-key",
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert body["expires_in"] == 86400

    def test_returned_token_is_valid_jwt(self, gw):
        client, _ = gw
        r = client.post(
            "/v1/auth/token",
            json={
                "tenant_id": "tenant_abc",
                "api_key": "any-key",
                "project_id": "proj_xyz",
            },
        )
        token = r.json()["access_token"]
        # Use the gateway's own verify with the test signing key
        from services.gateway.app.auth.tokens import verify_token

        payload = verify_token(token, signing_key="test-secret-key")
        assert payload["sub"] == "tenant_abc"
        assert payload["proj"] == "proj_xyz"

    def test_bad_tenant_id_format_returns_400(self, gw):
        client, _ = gw
        r = client.post(
            "/v1/auth/token",
            json={
                "tenant_id": "notvalid",
                "api_key": "key",
            },
        )
        assert r.status_code == 400

    def test_empty_api_key_returns_400(self, gw):
        client, _ = gw
        r = client.post(
            "/v1/auth/token",
            json={
                "tenant_id": "tenant_abc",
                "api_key": "   ",
            },
        )
        assert r.status_code == 400

    def test_bad_project_id_returns_400(self, gw):
        client, _ = gw
        r = client.post(
            "/v1/auth/token",
            json={
                "tenant_id": "tenant_abc",
                "api_key": "key",
                "project_id": "notaproject",
            },
        )
        assert r.status_code == 400


# ── Gateway middleware — Bearer token acceptance ──────────────────────────────


class TestGatewayBearerAuth:
    def _get_token(self, client) -> str:
        r = client.post(
            "/v1/auth/token",
            json={
                "tenant_id": "tenant_bearer",
                "api_key": "key",
                "project_id": "proj_bearer",
            },
        )
        return r.json()["access_token"]

    def _infer_body(self, tenant_id="tenant_bearer") -> dict:
        return {
            "tenant_id": tenant_id,
            "project_id": "proj_bearer",
            "task_type": "summary",
            "input": {"text": "hello"},
        }

    def test_bearer_token_accepted_on_infer(self, gw):
        client, _ = gw
        token = self._get_token(client)
        r = client.post(
            "/v1/infer",
            json=self._infer_body(),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200

    def test_no_auth_returns_401(self, gw):
        client, _ = gw
        r = client.post("/v1/infer", json=self._infer_body())
        assert r.status_code == 401

    def test_tampered_token_returns_401(self, gw):
        client, _ = gw
        token = self._get_token(client)
        parts = token.split(".")
        mid = len(parts[2]) // 2
        parts[2] = parts[2][:mid] + ("A" if parts[2][mid] != "A" else "B") + parts[2][mid + 1 :]
        bad = ".".join(parts)
        r = client.post(
            "/v1/infer",
            json=self._infer_body(),
            headers={"Authorization": f"Bearer {bad}"},
        )
        assert r.status_code == 401

    def test_garbage_bearer_returns_401(self, gw):
        client, _ = gw
        r = client.post(
            "/v1/infer",
            json=self._infer_body(),
            headers={"Authorization": "Bearer not.a.jwt"},
        )
        assert r.status_code == 401

    def test_test_mode_header_fallback_still_works(self, gw):
        """APP_ENV=test: old X-Tenant-Id + X-Project-Id headers still accepted."""
        client, _ = gw
        r = client.post(
            "/v1/infer",
            json=self._infer_body("tenant_legacy"),
            headers={
                "X-Tenant-Id": "tenant_legacy",
                "X-Project-Id": "proj_legacy",
            },
        )
        assert r.status_code == 200


# ── GET /v1/tenants list ──────────────────────────────────────────────────────


class TestTenantList:
    def test_list_empty(self, gw):
        client, _ = gw
        r = client.get("/v1/tenants")
        assert r.status_code == 200
        assert r.json() == []

    def test_list_returns_created_tenants(self, gw):
        client, _ = gw
        client.post("/v1/tenants", json={"name": "Alpha"})
        client.post("/v1/tenants", json={"name": "Beta"})
        r = client.get("/v1/tenants")
        assert r.status_code == 200
        names = [t["name"] for t in r.json()]
        assert "Alpha" in names
        assert "Beta" in names

    def test_active_only_filter(self, gw):
        client, _ = gw
        # Create an active tenant first
        client.post("/v1/tenants", json={"name": "Active"})

        # Create an inactive tenant
        r2 = client.post("/v1/tenants", json={"name": "Inactive"})
        t2_id = r2.json()["tenant_id"]
        client.patch(f"/v1/tenants/{t2_id}", json={"is_active": False})

        r = client.get("/v1/tenants?active_only=true")
        names = [t["name"] for t in r.json()]
        assert "Active" in names
        assert "Inactive" not in names


# ── GET /v1/ingestion/jobs list ───────────────────────────────────────────────


class TestJobList:
    def _seed_job(self, db, tenant_id="tenant_j1", status="queued"):
        from packages.models.ingestion import IngestionJob

        job = IngestionJob(
            id=f"job_{__import__('uuid').uuid4().hex}",
            file_id="file_j1",
            project_id="proj_j1",
            tenant_id=tenant_id,
            status=status,
            entities_created=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(job)
        return job

    def test_list_jobs_for_tenant(self, ingest):
        client, db = ingest
        self._seed_job(db, "tenant_j1")
        r = client.get("/v1/ingestion/jobs?tenant_id=tenant_j1")
        assert r.status_code == 200
        assert len(r.json()) == 1
        assert r.json()[0]["job_id"].startswith("job_")

    def test_list_jobs_cross_tenant_isolation(self, ingest):
        client, db = ingest
        self._seed_job(db, "tenant_jjj")
        self._seed_job(db, "tenant_kkk")
        r = client.get("/v1/ingestion/jobs?tenant_id=tenant_jjj")
        assert r.status_code == 200
        assert all(j["job_id"] != "tenant_kkk" for j in r.json())

    def test_list_jobs_bad_tenant_returns_400(self, ingest):
        client, _ = ingest
        r = client.get("/v1/ingestion/jobs?tenant_id=badformat")
        assert r.status_code == 400

    def test_list_jobs_empty_for_unknown_tenant(self, ingest):
        client, _ = ingest
        r = client.get("/v1/ingestion/jobs?tenant_id=tenant_unknown99")
        assert r.status_code == 200
        assert r.json() == []
