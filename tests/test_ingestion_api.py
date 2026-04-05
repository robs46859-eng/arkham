"""
BIM ingestion API contract tests.
Implements: Build Rules §8 — API and routing tests for ingestion service.
Tests: file registration, ingestion dispatch, ID format validation.
"""

import importlib
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
BIM_DIR = ROOT / "services" / "bim_ingestion"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql://robco:password@localhost:5432/robco_db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

    sys.path.insert(0, str(BIM_DIR))
    for mod in list(sys.modules):
        if mod == "app" or mod.startswith("app."):
            sys.modules.pop(mod)
    app = importlib.import_module("app.main").app
    yield TestClient(app)
    sys.path.remove(str(BIM_DIR))


def test_register_file_returns_file_id(client):
    response = client.post(
        "/v1/files/register",
        json={
            "tenant_id": "tenant_abc123",
            "project_id": "proj_abc123",
            "file_type": "ifc",
            "storage_path": "s3://bim-files/proj_abc123/model.ifc",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["file_id"].startswith("file_")
    assert body["file_type"] == "ifc"


def test_register_file_rejects_bad_tenant_id(client):
    response = client.post(
        "/v1/files/register",
        json={
            "tenant_id": "bad-format",
            "project_id": "proj_abc123",
            "file_type": "pdf",
            "storage_path": "s3://bim-files/proj_abc123/report.pdf",
        },
    )
    assert response.status_code == 400


def test_register_file_rejects_bad_project_id(client):
    response = client.post(
        "/v1/files/register",
        json={
            "tenant_id": "tenant_abc123",
            "project_id": "bad-format",
            "file_type": "pdf",
            "storage_path": "s3://bim-files/proj_abc123/report.pdf",
        },
    )
    assert response.status_code == 400


def test_ingest_returns_queued_job(client):
    response = client.post(
        "/v1/files/file_testid123/ingest",
        json={
            "tenant_id": "tenant_abc123",
            "project_id": "proj_abc123",
            "file_id": "file_testid123",
            "file_type": "ifc",
            "storage_path": "s3://bim-files/proj_abc123/model.ifc",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "queued"
    assert body["job_id"].startswith("job_")


def test_ingest_rejects_file_id_mismatch(client):
    response = client.post(
        "/v1/files/file_wrong/ingest",
        json={
            "tenant_id": "tenant_abc123",
            "project_id": "proj_abc123",
            "file_id": "file_different",
            "file_type": "ifc",
            "storage_path": "s3://bim-files/proj_abc123/model.ifc",
        },
    )
    assert response.status_code == 400


def test_get_job_status_not_found(client):
    response = client.get("/v1/ingestion/jobs/job_nonexistent")
    assert response.status_code == 404


def test_get_job_bad_format(client):
    response = client.get("/v1/ingestion/jobs/bad_format")
    assert response.status_code == 400


def test_list_project_files_empty(client):
    response = client.get("/v1/projects/proj_abc123/files")
    assert response.status_code == 200
    assert response.json() == []
