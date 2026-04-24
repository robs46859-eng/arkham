from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


API_BASE = os.environ.get("STELARAI_API_BASE", "https://api.fsai.pro/api/v1").rstrip("/")
AUTH_TOKEN = os.environ.get("STELARAI_AUTH_TOKEN", "").strip()
TENANT_ID = os.environ.get("STELARAI_TENANT_ID", "").strip() or None


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)


def request(method: str, path: str, payload: dict | None = None) -> dict:
    if not AUTH_TOKEN:
        fail("STELARAI_AUTH_TOKEN is required.")
    url = f"{API_BASE}{path}"
    body = None
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {AUTH_TOKEN}",
    }
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, method=method, data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")
        fail(f"{method} {path} failed with HTTP {exc.code}: {body_text}")
    except urllib.error.URLError as exc:
        fail(f"{method} {path} failed: {exc}")


def main() -> None:
    workspace_payload = {
        "tenant_id": TENANT_ID,
        "name": "StelarAI Smoke Workspace",
        "slug": "stelarai-smoke-workspace",
        "target_domain": "stelarai.tech",
        "primary_model_tier": "balanced",
        "enabled_modules": [
            "canvas-builder",
            "digital-it-girl",
            "public-beta",
            "autopitch",
        ],
    }

    workspace = request("POST", "/stelarai/workspaces", workspace_payload)
    workspace_id = workspace["id"]

    account = request(
        "POST",
        f"/stelarai/workspaces/{workspace_id}/accounts",
        {
            "workspace_id": workspace_id,
            "provider_key": "anthropic",
            "account_label": "Smoke Anthropic Account",
            "connection_scope": "business",
            "metadata": {"purpose": "smoke"},
        },
    )

    source = request(
        "POST",
        f"/stelarai/workspaces/{workspace_id}/sources",
        {
            "workspace_id": workspace_id,
            "source_kind": "internal-notes",
            "source_label": "Smoke Internal Source",
            "sync_mode": "manual",
            "metadata": {"purpose": "smoke"},
        },
    )

    workflow = request(
        "POST",
        f"/stelarai/workspaces/{workspace_id}/workflows",
        {
            "workspace_id": workspace_id,
            "module_key": "canvas-builder",
            "name": "Smoke Workflow",
            "provider_lane": "cheap",
            "workflow": {
                "nodes": [
                    {"id": "n1", "type": "input", "label": "Start"},
                    {"id": "n2", "type": "llm", "label": "Draft"},
                ],
                "edges": [{"source": "n1", "target": "n2"}],
            },
        },
    )

    workflow_detail = request("GET", f"/stelarai/workflows/{workflow['id']}")
    account_list = request("GET", f"/stelarai/workspaces/{workspace_id}/accounts")
    source_list = request("GET", f"/stelarai/workspaces/{workspace_id}/sources")
    workflow_list = request("GET", f"/stelarai/workspaces/{workspace_id}/workflows")

    summary = {
        "workspace_id": workspace_id,
        "account_id": account["id"],
        "source_id": source["id"],
        "workflow_id": workflow["id"],
        "counts": {
            "accounts": account_list["total"],
            "sources": source_list["total"],
            "workflows": workflow_list["total"],
        },
        "workflow_detail": workflow_detail,
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
