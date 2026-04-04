import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SERVICE_DIRS = {
    "gateway": ROOT / "services" / "gateway",
    "bim-ingestion": ROOT / "services" / "bim_ingestion",
    "orchestration": ROOT / "services" / "orchestration",
}


def _load_service_app(service_name: str):
    service_dir = SERVICE_DIRS[service_name]
    sys.path.insert(0, str(service_dir))
    for module_name in list(sys.modules):
        if module_name == "app" or module_name.startswith("app."):
            sys.modules.pop(module_name)
    return importlib.import_module("app.main").app


def test_services_health_endpoints(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql://robco:password@localhost:5432/robco_db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

    for service_name, service_dir in SERVICE_DIRS.items():
        app = _load_service_app(service_name)
        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {
            "status": "ok",
            "service": service_name,
            "environment": "test",
        }

        sys.path.remove(str(service_dir))
