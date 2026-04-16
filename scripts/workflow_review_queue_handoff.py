"""Import a shadow-run artifact into the workflow review queue and apply review decisions.

This script exercises the same gateway endpoints that will own controlled outreach
approval later, but stops at approval-state transitions and never sends.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.db import get_db
from packages.models import Tenant
from tests.conftest import MockSession


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _load_gateway_app():
    os.environ["APP_ENV"] = "test"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    os.environ["REDIS_URL"] = "redis://localhost:6379/0"
    os.environ["SIGNING_KEY"] = "review-queue-handoff-signing-key-0123456789"
    os.environ["ADMIN_TOKEN"] = "review-queue-admin-token"

    module_path = "services.gateway.app.main"
    module_prefix = module_path.rsplit(".", 1)[0]
    for module_name in list(sys.modules):
        if module_name == module_prefix or module_name.startswith(f"{module_prefix}."):
            sys.modules.pop(module_name)
    module = importlib.import_module(module_path)
    module.check_database = lambda _: (True, "ok")
    module.check_redis = lambda _: (True, "ok")
    return module.app


def _load_artifact(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise SystemExit(f"Expected a list artifact at {path}, got {type(payload).__name__}")
    return payload


def _normalize_items(items: list[dict], tenant_id: str | None) -> list[dict]:
    normalized: list[dict] = []
    for item in items:
        lead = item.get("lead") or {}
        eligibility = item.get("eligibility") or {}
        decision = item.get("decision") or {}
        resolved_tenant_id = item.get("tenant_id") or tenant_id
        if not resolved_tenant_id:
            raise SystemExit("Artifact item is missing tenant_id and no --tenant-id default was provided")
        normalized.append(
            {
                "tenant_id": resolved_tenant_id,
                "case_name": item.get("case") or "unknown_case",
                "request_id": (item.get("request_id") or f"{resolved_tenant_id}:{item.get('case') or 'case'}"),
                "lead": lead,
                "eligibility": eligibility,
                "decision": decision,
                "output_preview": item.get("output_preview") or {},
                "execution_contract": item.get("execution_contract") or {},
                "workflow_context": item.get("workflow_context") or {},
                "reviewer": item.get("reviewer") or {},
                "expectation": item.get("expectation"),
            }
        )
    return normalized


def _seed_tenants(db: MockSession, tenant_ids: set[str]) -> None:
    now = _utcnow()
    for tenant_id in sorted(tenant_ids):
        db.add(
            Tenant(
                id=tenant_id,
                name=f"Review Queue {tenant_id}",
                is_active=True,
                created_at=now,
                updated_at=now,
                plan="free",
            )
        )


def _parse_review_arg(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise SystemExit(f"Invalid --review '{value}'. Use CASE=approved|rejected|needs_fix|pending|skipped")
    case_name, status = value.split("=", 1)
    case_name = case_name.strip()
    status = status.strip().lower()
    if not case_name:
        raise SystemExit(f"Invalid --review '{value}': missing case name")
    if status not in {"approved", "rejected", "needs_fix", "pending", "skipped"}:
        raise SystemExit(f"Invalid review status '{status}' in --review '{value}'")
    return case_name, status


def _parse_execution_arg(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise SystemExit(f"Invalid --execute '{value}'. Use CASE=queued|ready|blocked")
    case_name, status = value.split("=", 1)
    case_name = case_name.strip()
    status = status.strip().lower()
    if not case_name:
        raise SystemExit(f"Invalid --execute '{value}': missing case name")
    if status not in {"queued", "ready", "blocked"}:
        raise SystemExit(f"Invalid execution status '{status}' in --execute '{value}'")
    return case_name, status


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Import a workflow-memory shadow artifact into the review queue.")
    parser.add_argument("--artifact", required=True, help="Path to the shadow-run JSON artifact")
    parser.add_argument("--tenant-id", default=None, help="Default tenant ID if the artifact lacks tenant_id fields")
    parser.add_argument("--label", default=None, help="Optional review batch label override")
    parser.add_argument("--reviewer", default="Operator One", help="Reviewer name applied to updates")
    parser.add_argument("--actor", default="operator.one", help="Admin actor recorded on review, execution, and delivery actions")
    parser.add_argument(
        "--review",
        action="append",
        default=[],
        help="Apply a review status to a case, e.g. borderline_reuse=needs_fix",
    )
    parser.add_argument(
        "--execute",
        action="append",
        default=[],
        help="Create an execution record for an approved case, e.g. no_cache_generate=queued",
    )
    parser.add_argument(
        "--deliver",
        action="append",
        default=[],
        help="Create a delivery attempt for an execution case, e.g. no_cache_generate",
    )
    args = parser.parse_args(argv[1:])

    artifact_path = Path(args.artifact).expanduser().resolve()
    items = _normalize_items(_load_artifact(artifact_path), args.tenant_id)
    tenant_ids = {item["tenant_id"] for item in items}

    app = _load_gateway_app()
    shared_db = MockSession()
    _seed_tenants(shared_db, tenant_ids)

    def override_db():
        yield shared_db

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    admin_headers = {
        "X-Admin-Token": "review-queue-admin-token",
        "X-Admin-Actor": args.actor,
    }

    batch_label = args.label or artifact_path.stem
    imported = client.post(
        "/v1/crm/workflow-review-queue/import",
        json={
            "batch_label": batch_label,
            "source_artifact": str(artifact_path),
            "items": items,
        },
        headers=admin_headers,
    )
    if imported.status_code != 200:
        raise SystemExit(f"Import failed: {imported.status_code} {imported.text}")
    imported_items = imported.json()

    requested_reviews = dict(_parse_review_arg(value) for value in args.review)
    if not requested_reviews:
        pending_items = [item for item in imported_items if item["review_status"] == "pending"]
        if pending_items:
            requested_reviews[pending_items[0]["case_name"]] = "approved"
        if len(pending_items) > 1:
            requested_reviews[pending_items[1]["case_name"]] = "needs_fix"

    updates: list[dict] = []
    for item in imported_items:
        status = requested_reviews.get(item["case_name"])
        if not status:
            continue
        response = client.patch(
            f"/v1/crm/workflow-review-queue/items/{item['review_item_id']}",
            json={
                "review_status": status,
                "reviewer_name": args.reviewer,
                "reviewer_notes": f"{status.replace('_', ' ')} via controlled handoff batch",
            },
            headers=admin_headers,
        )
        if response.status_code != 200:
            raise SystemExit(f"Review update failed for {item['case_name']}: {response.status_code} {response.text}")
        updates.append(response.json())

    requested_executions = dict(_parse_execution_arg(value) for value in args.execute)
    executions: list[dict] = []
    executions_by_case: dict[str, dict] = {}
    for item in imported_items:
        execution_status = requested_executions.get(item["case_name"])
        if not execution_status:
            continue
        response = client.post(
            f"/v1/crm/workflow-review-queue/items/{item['review_item_id']}/execution",
            json={
                "execution_status": execution_status,
                "metadata": {
                    "mode": "shadow_execution_simulation",
                    "artifact": str(artifact_path),
                },
            },
            headers=admin_headers,
        )
        if response.status_code != 200:
            raise SystemExit(f"Execution create failed for {item['case_name']}: {response.status_code} {response.text}")
        execution = response.json()
        executions.append(execution)
        executions_by_case[item["case_name"]] = execution

    requested_deliveries = [value.strip() for value in args.deliver if value.strip()]
    deliveries: list[dict] = []
    delivery_history: dict[str, list[dict]] = {}
    for case_name in requested_deliveries:
        execution = executions_by_case.get(case_name)
        if not execution:
            raise SystemExit(f"Delivery requested for {case_name}, but no execution was created for that case")
        response = client.post(
            f"/v1/crm/workflow-executions/{execution['execution_id']}/deliver",
            json={
                "metadata": {
                    "mode": "shadow_delivery_simulation",
                    "artifact": str(artifact_path),
                },
            },
            headers=admin_headers,
        )
        if response.status_code != 200:
            raise SystemExit(f"Delivery create failed for {case_name}: {response.status_code} {response.text}")
        delivery = response.json()
        deliveries.append(delivery)
        history_response = client.get(
            f"/v1/crm/workflow-executions/{execution['execution_id']}/deliveries",
            headers=admin_headers,
        )
        if history_response.status_code != 200:
            raise SystemExit(f"Delivery history failed for {case_name}: {history_response.status_code} {history_response.text}")
        delivery_history[case_name] = history_response.json()

    queue_snapshot: dict[str, list[dict]] = {}
    for tenant_id in sorted(tenant_ids):
        response = client.get(
            f"/v1/crm/workflow-review-queue/{tenant_id}?batch_label={batch_label}&limit=100",
            headers=admin_headers,
        )
        if response.status_code != 200:
            raise SystemExit(f"Queue list failed for {tenant_id}: {response.status_code} {response.text}")
        queue_snapshot[tenant_id] = response.json()

    output = {
        "batch_label": batch_label,
        "source_artifact": str(artifact_path),
        "tenant_ids": sorted(tenant_ids),
        "imported_count": len(imported_items),
        "updated_count": len(updates),
        "execution_count": len(executions),
        "delivery_count": len(deliveries),
        "requested_reviews": requested_reviews,
        "requested_executions": requested_executions,
        "requested_deliveries": requested_deliveries,
        "actor": args.actor,
        "imported_items": imported_items,
        "updates": updates,
        "executions": executions,
        "deliveries": deliveries,
        "delivery_history": delivery_history,
        "queue_snapshot": queue_snapshot,
    }

    safe_label = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in batch_label).strip("_") or "review_queue"
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output_path = ROOT / "artifacts" / "shadow-runs" / "review-queue" / f"{safe_label}_{timestamp}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")

    print(f"Saved review-queue handoff report to {output_path}")
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
