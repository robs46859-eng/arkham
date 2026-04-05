#!/usr/bin/env python3
"""Export the gateway FastAPI OpenAPI schema to a checked-in JSON artifact."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = REPO_ROOT / "docs" / "openapi" / "gateway.openapi.json"


def ensure_import_defaults() -> None:
    """Provide safe defaults so schema export works outside a deployed env."""
    os.environ.setdefault("APP_ENV", "test")
    os.environ.setdefault("DATABASE_URL", "postgresql://placeholder")
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
    os.environ.setdefault("SIGNING_KEY", "test-signing-key-not-for-production")
    os.environ.setdefault("PRIVACY_SERVICE_TOKEN", "test-privacy-token")


def export_schema(output_path: Path) -> None:
    sys.path.insert(0, str(REPO_ROOT))
    ensure_import_defaults()

    from services.gateway.app.main import app

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    output_path = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_OUTPUT
    export_schema(output_path)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
