"""Run a small operator-review shadow batch for workflow-memory decisions.

This script uses the existing dry-run convert path and workflow-memory decision
audit to generate a reviewable set without sending any real outbound messages.
"""

from __future__ import annotations

import csv
import importlib
import json
import os
import sys
import argparse
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.db import get_db
from packages.models import CRMActivityRecord, Tenant
from services.gateway.app.auth.api_keys import issue_api_key
from tests.conftest import MockSession


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _seed_tenant_api_key(db: MockSession, tenant_id: str, *, name: str) -> str:
    now = _utcnow()
    tenant = Tenant(
        id=tenant_id,
        name=name,
        is_active=True,
        created_at=now,
        updated_at=now,
        plan="free",
    )
    db.add(tenant)
    issued = issue_api_key(tenant_id=tenant_id)
    db.add(issued.record)
    return issued.plaintext


def _load_gateway_app():
    os.environ["APP_ENV"] = "test"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    os.environ["REDIS_URL"] = "redis://localhost:6379/0"
    os.environ["SIGNING_KEY"] = "shadow-run-signing-key-0123456789"
    os.environ["ADMIN_TOKEN"] = "shadow-run-admin-token"
    os.environ["AUTOMATION_DRY_RUN"] = "true"

    module_path = "services.gateway.app.main"
    module_prefix = module_path.rsplit(".", 1)[0]
    for module_name in list(sys.modules):
        if module_name == module_prefix or module_name.startswith(f"{module_prefix}."):
            sys.modules.pop(module_name)
    module = importlib.import_module(module_path)
    module.check_database = lambda _: (True, "ok")
    module.check_redis = lambda _: (True, "ok")
    return module.app


def _load_leads(*, offset: int = 0, limit: int = 5) -> list[dict[str, Any]]:
    path = ROOT / "leads" / "apollo-contacts-export.csv"
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        return rows[offset : offset + limit]


def _case_plan() -> list[dict[str, Any]]:
    return [
        {
            "case": "no_cache_generate",
            "cache_mode": "none",
            "outcomes": [],
            "expectation": "fresh generation because no reusable flow exists yet",
        },
        {
            "case": "borderline_reuse",
            "cache_mode": "valid",
            "outcomes": ["send_approval", "delivered", "rejection"],
            "expectation": "reuse because score sits just above threshold and there is no compatibility failure",
        },
        {
            "case": "borderline_regenerate",
            "cache_mode": "valid",
            "outcomes": ["send_approval", "delivered", "delivered", "rejection", "rejection"],
            "expectation": "regenerate because score falls just below threshold",
        },
        {
            "case": "partial_payload_regenerate",
            "cache_mode": "partial",
            "outcomes": ["reply"],
            "expectation": "regenerate because payload is incomplete even though quality is strong",
        },
        {
            "case": "version_drift_regenerate",
            "cache_mode": "stale_version",
            "outcomes": ["delivered"],
            "expectation": "regenerate because cached offer version drifted from active workflow",
        },
    ]


def _build_cached_output() -> dict[str, Any]:
    return {
        "pitch": {
            "headline": "Reusable outreach flow",
            "body": "FullStack gives agency operators one AI gateway to discover, monitor, and convert niche SaaS opportunities.",
            "time_saved": "5-10 hours per week",
            "cost_equiv": "$500-$1,500/month",
            "roi_days": 30,
            "cta": "Want to try Agency for $30/mo?",
        },
        "template_id": "autopitch_v1",
        "product": {
            "name": "Agency",
            "product_id": "prod_UICyBy4ItoEBsW",
            "payment_url": "https://buy.stripe.com/bJefZaeRR4V20iRfh5fnO02",
            "price": "$30/mo",
        },
        "execution": {
            "email": {
                "to": None,
                "subject": "Reusable outreach flow",
                "body": "FullStack gives agency operators one AI gateway to discover, monitor, and convert niche SaaS opportunities.",
            },
            "crm_payload": {},
            "follow_up_sequence": [2, 5, 10],
        },
    }


def _lead_eligibility(lead: dict[str, Any]) -> dict[str, Any]:
    missing: list[str] = []
    email = (lead.get("Email") or "").strip()
    first_name = (lead.get("First Name") or "").strip()
    company = (lead.get("Company Name") or "").strip()
    if not email:
        missing.append("email")
    if not first_name:
        missing.append("first_name")
    if not company:
        missing.append("company_name")
    return {
        "sendable": len(missing) == 0,
        "status": "sendable" if len(missing) == 0 else "incomplete",
        "missing_fields": missing,
        "email": email or None,
        "first_name": first_name or None,
        "company_name": company or None,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Run a dry-run workflow-memory shadow batch.")
    parser.add_argument("--offset", type=int, default=0, help="Zero-based lead offset into the CSV")
    parser.add_argument("--limit", type=int, default=5, help="Number of leads to include in the batch")
    parser.add_argument("--label", default="shadow", help="Optional label to include in the output filename")
    args = parser.parse_args(argv[1:])

    app = _load_gateway_app()
    from services.gateway.app.routers import ai as ai_router
    from services.gateway.app.routers import crm as crm_router

    ai_router.settings.enable_semantic_cache = True
    crm_router.settings.enable_semantic_cache = True

    workflow_cache: dict[tuple[str, str], dict[str, Any]] = {}

    async def fake_set(*, tenant_id: str, task_type: str, input_text: str, output: dict[str, Any]) -> None:
        workflow_cache[(tenant_id, task_type)] = {"input_text": input_text, "output": output}

    async def fake_get(*, tenant_id: str, task_type: str, input_text: str, threshold=None):
        record = workflow_cache.get((tenant_id, task_type))
        if record and record["input_text"] == input_text:
            return record["output"]
        return None

    ai_router.semantic_cache.set = fake_set
    ai_router.semantic_cache.get = fake_get
    crm_router.semantic_cache.set = fake_set
    crm_router.semantic_cache.get = fake_get

    shared_db = MockSession()

    def override_db():
        yield shared_db

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    admin_headers = {"X-Admin-Token": "shadow-run-admin-token"}

    client.patch(
        "/v1/crm/workflow-memory/config",
        json={
            "reuse_min_score": -0.5,
            "outcome_weights": {
                "send_approval": 1.0,
                "delivered": 2.0,
                "reply": 5.0,
                "booking": 8.0,
                "rejection": -4.0,
            },
        },
        headers=admin_headers,
    )

    leads = _load_leads(offset=max(args.offset, 0), limit=max(args.limit, 1))
    plans = _case_plan()
    cached_output = _build_cached_output()
    batch_results: list[dict[str, Any]] = []

    for lead, plan in zip(leads, plans):
        tenant_id = f"tenant_shadow_{plan['case']}"
        api_key = _seed_tenant_api_key(shared_db, tenant_id, name=f"Shadow {plan['case']}")
        eligibility = _lead_eligibility(lead)

        request_payload = {
            "module": "convert",
            "inputs": {
                "industry": lead.get("Industry") or "Marketing",
                "target_buyer": ai_router.DEFAULT_TARGET_BUYER,
                "pain_point": "manual prospecting and follow-up",
            },
            "auto_execute": True,
            "automation": {
                "product": "agency",
                "max_leads": 1,
                "leads": [lead],
            },
        }

        request_obj = ai_router.AiRequest(**request_payload)
        workflow_metadata = ai_router._convert_workflow_metadata(request_obj, ai_router.MODULE_CONFIG["convert"])
        workflow_context = ai_router._convert_workflow_context(request_obj, ai_router.MODULE_CONFIG["convert"])
        task_type = ai_router.build_workflow_memory_task_type(
            workflow_metadata["workflow_name"],
            workflow_metadata["offer_type"],
            workflow_metadata["stage"],
        )
        input_text = ai_router.build_workflow_memory_input_text(
            ai_router._convert_workflow_input_text(request_obj, ai_router.MODULE_CONFIG["convert"]),
            workflow_context,
        )

        if plan["cache_mode"] != "none":
            if plan["cache_mode"] == "partial":
                output = {"pitch": {"headline": "Partial only"}}
                metadata = workflow_metadata
            elif plan["cache_mode"] == "stale_version":
                output = cached_output
                metadata = {**workflow_metadata, "offer_version": "stale-offer.v0"}
            else:
                output = cached_output
                metadata = workflow_metadata

            workflow_cache[(tenant_id, task_type)] = {
                "input_text": input_text,
                "output": ai_router.build_workflow_memory_envelope(
                    workflow_type=workflow_metadata["workflow_name"],
                    offer_type=workflow_metadata["offer_type"],
                    stage=workflow_metadata["stage"],
                    output=output,
                    context=workflow_context,
                    metadata=metadata,
                ),
            }

        for idx, outcome in enumerate(plan["outcomes"]):
            shared_db.add(
                CRMActivityRecord(
                    id=f"act_{plan['case']}_{idx}",
                    tenant_id=tenant_id,
                    lead_id=None,
                    deal_id=None,
                    contact_id=None,
                    activity_type="workflow_outcome",
                    subject=f"{plan['case']}:{outcome}",
                    body=None,
                    record_metadata={
                        "workflow_type": workflow_metadata["workflow_name"],
                        "offer_type": workflow_metadata["offer_type"],
                        "stage": workflow_metadata["stage"],
                        "task_type": task_type,
                        "outcome": outcome,
                        "source": "reused",
                    },
                    created_at=_utcnow(),
                )
            )

        if eligibility["sendable"]:
            response = client.post("/v1/ai", json=request_payload, headers={"Authorization": f"Bearer {api_key}"})
            if response.status_code != 200:
                raise SystemExit(f"convert request failed for {plan['case']}: {response.status_code} {response.text}")
            body = response.json()
            metrics = client.get(
                f"/v1/crm/workflow-memory/metrics/{tenant_id}?workflow_type=fullstack_outreach&offer_type=agency&stage=first_touch",
                headers=admin_headers,
            ).json()
            decisions = client.get(
                f"/v1/crm/workflow-memory/decisions/{tenant_id}?workflow_type=fullstack_outreach&offer_type=agency&stage=first_touch&limit=3",
                headers=admin_headers,
            ).json()
            decision = decisions[0] if decisions else {}
            first_automation = body["automation"][0] if body.get("automation") else {}
            payload = first_automation.get("payload") if isinstance(first_automation, dict) else None
            if not isinstance(payload, dict):
                payload = first_automation if isinstance(first_automation, dict) else {}
        else:
            body = {
                "usage": {
                    "workflow_memory": {
                        "status": "skipped_preflight",
                        "reason": "incomplete_lead",
                        "score": None,
                        "reuse_threshold": 0.0,
                        "stored": False,
                        "estimated_time_saved_ms": 0,
                    }
                },
                "output": {
                    "pitch": {
                        "headline": None,
                    }
                },
                "automation": [],
            }
            metrics = {
                "hit_rate": 0.0,
                "fallback_rate": 0.0,
                "fallback_reasons": {},
                "outcome_score": 0.0,
                "outcome_counts": {},
            }
            decision = {
                "metadata": {
                    "decision_summary": "skipped before preview because lead is incomplete",
                    "reason_path": ["preflight:incomplete_lead", "decision:skip"],
                },
                "fallback_reason": "incomplete_lead",
            }
            payload = {}

        batch_results.append(
            {
                "tenant_id": tenant_id,
                "lead": {
                    "name": f"{lead.get('First Name', '').strip()} {lead.get('Last Name', '').strip()}".strip(),
                    "company": lead.get("Company Name"),
                    "title": lead.get("Title"),
                    "email": lead.get("Email"),
                    "technologies": lead.get("Technologies"),
                },
                "eligibility": eligibility,
                "case": plan["case"],
                "expectation": plan["expectation"],
                "decision": {
                    "status": body["usage"]["workflow_memory"]["status"],
                    "reason": body["usage"]["workflow_memory"]["reason"],
                    "score": body["usage"]["workflow_memory"].get("score"),
                    "threshold": body["usage"]["workflow_memory"].get("reuse_threshold"),
                    "stored": body["usage"]["workflow_memory"].get("stored"),
                    "estimated_time_saved_ms": body["usage"]["workflow_memory"].get("estimated_time_saved_ms"),
                    "summary": decision.get("metadata", {}).get("decision_summary"),
                    "reason_path": decision.get("metadata", {}).get("reason_path"),
                    "fallback_reason": decision.get("fallback_reason"),
                },
                "output_preview": {
                    "headline": body["output"]["pitch"]["headline"],
                    "subject": payload.get("subject"),
                    "body_excerpt": ((str(payload.get("body", ""))[:220]) + "...") if payload.get("body") else None,
                },
                "execution_contract": {
                    "channel": "email",
                    "provider_mode": "dry_run",
                    "to": payload.get("to") or eligibility.get("email"),
                    "subject": payload.get("subject"),
                    "body": payload.get("body"),
                    "product": body["output"].get("product") or {},
                    "follow_up_sequence": body["output"].get("execution", {}).get("follow_up_sequence") or [],
                    "crm_payload": body["output"].get("execution", {}).get("crm_payload") or {},
                },
                "workflow_context": {
                    "workflow_type": "fullstack_outreach",
                    "offer_type": request_payload["automation"]["product"],
                    "stage": "first_touch",
                },
                "metrics": {
                    "hit_rate": metrics["hit_rate"],
                    "fallback_rate": metrics["fallback_rate"],
                    "fallback_reasons": metrics["fallback_reasons"],
                    "outcome_score": metrics["outcome_score"],
                    "outcome_counts": metrics["outcome_counts"],
                },
                "reviewer": {
                    "disposition": None,
                    "judgment_reason": None,
                    "operator_quality_assessment": None,
                    "notes": None,
                    "matches_system_decision": None,
                },
            }
        )

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    safe_label = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in str(args.label)).strip("_") or "shadow"
    output_path = ROOT / "artifacts" / "shadow-runs" / f"workflow_memory_{safe_label}_{timestamp}.json"
    output_path.write_text(json.dumps(batch_results, indent=2), encoding="utf-8")

    print(f"Saved shadow-run report to {output_path}")
    print(json.dumps(batch_results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
