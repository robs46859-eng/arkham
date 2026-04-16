"""
Omniscale — Quantity Takeoff & Cost Estimation Vertical.
Accepts project data and BIM summaries, returns structured cost estimates
using Claude for intelligent line-item generation.
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx
from fastapi import HTTPException
from pydantic import BaseModel, Field

from packages.vertical_base import EventPayload, VerticalBase

vertical = VerticalBase(
    service_id="omniscale",
    title="Omniscale — Quantity Takeoff",
    port=8000,
    capabilities=["quantity_takeoff", "cost_estimation", "dashboard", "metrics"],
    event_subscriptions=["workflow.started", "workflow.completed", "metric.updated"],
)

app = vertical.app

# ── LLM helper ───────────────────────────────────────────────────────────────

async def _call_claude(system_prompt: str, user_message: str, model: str = "claude-3-5-haiku-20241022") -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=502, detail="ANTHROPIC_API_KEY not configured")
    async with httpx.AsyncClient(timeout=90.0) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 4096,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_message}],
            },
        )
        resp.raise_for_status()
        return resp.json()["content"][0]["text"]


# ── Request / Response models ─────────────────────────────────────────────────

class TakeoffRequest(BaseModel):
    project_name: str
    project_type: str = "commercial"  # residential, commercial, industrial, civic
    location: str = ""
    gross_floor_area_sqft: float | None = None
    num_stories: int | None = None
    construction_type: str = ""       # e.g. "Type II-B steel frame"
    scope_description: str            # plain-language scope
    bim_data: dict[str, Any] = Field(default_factory=dict)  # parsed BIM elements
    include_divisions: list[str] = Field(default_factory=list)  # CSI divisions to include


class TakeoffLineItem(BaseModel):
    division: str
    description: str
    unit: str
    quantity: float
    unit_rate_usd: float
    total_usd: float
    notes: str = ""


class TakeoffResponse(BaseModel):
    project_name: str
    project_type: str
    line_items: list[TakeoffLineItem]
    subtotal_usd: float
    contingency_pct: float
    contingency_usd: float
    total_usd: float
    assumptions: list[str]
    exclusions: list[str]
    prepared_by: str = "Omniscale AI"


# In-memory store
_takeoffs: dict[str, dict] = {}

_SYSTEM = """You are an expert quantity surveyor and cost estimator for architecture and construction projects.
Your job is to produce detailed, realistic quantity takeoffs with unit costs based on current US construction market rates.

Always respond with valid JSON only — no markdown, no commentary, no code fences.

The JSON must have this exact structure:
{
  "line_items": [
    {
      "division": "03 - Concrete",
      "description": "Reinforced slab on grade, 6\" thick",
      "unit": "SF",
      "quantity": 12500,
      "unit_rate_usd": 12.50,
      "total_usd": 156250.00,
      "notes": "Includes vapor barrier and WWF"
    }
  ],
  "subtotal_usd": 0.0,
  "contingency_pct": 10.0,
  "contingency_usd": 0.0,
  "total_usd": 0.0,
  "assumptions": ["string"],
  "exclusions": ["string"]
}

Use CSI MasterFormat divisions. Include at least 8 line items covering the major scopes.
Use realistic 2024-2025 US unit costs. Calculate subtotal, contingency, and total accurately."""


# ── Routes ───────────────────────────────────────────────────────────────────

@app.post("/takeoff", response_model=TakeoffResponse)
async def run_takeoff(req: TakeoffRequest) -> TakeoffResponse:
    """Generate a quantity takeoff and cost estimate for a project."""
    user_msg = f"""
Project: {req.project_name}
Type: {req.project_type}
Location: {req.location or "Not specified"}
GFA: {req.gross_floor_area_sqft or "Not specified"} SF
Stories: {req.num_stories or "Not specified"}
Construction Type: {req.construction_type or "Not specified"}
Scope: {req.scope_description}

BIM Data (parsed elements):
{json.dumps(req.bim_data, indent=2) if req.bim_data else "No BIM data provided — estimate from scope description."}

{"Include only these CSI divisions: " + ", ".join(req.include_divisions) if req.include_divisions else "Include all relevant CSI divisions."}

Produce a detailed quantity takeoff with realistic unit costs.
""".strip()

    raw = await _call_claude(_SYSTEM, user_msg)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Extract JSON from partial response
        start = raw.find("{")
        end = raw.rfind("}") + 1
        data = json.loads(raw[start:end])

    takeoff_id = f"takeoff_{len(_takeoffs) + 1}"
    result = TakeoffResponse(
        project_name=req.project_name,
        project_type=req.project_type,
        line_items=[TakeoffLineItem(**item) for item in data["line_items"]],
        subtotal_usd=data["subtotal_usd"],
        contingency_pct=data["contingency_pct"],
        contingency_usd=data["contingency_usd"],
        total_usd=data["total_usd"],
        assumptions=data["assumptions"],
        exclusions=data["exclusions"],
    )
    _takeoffs[takeoff_id] = result.model_dump()
    return result


@app.get("/takeoffs")
async def list_takeoffs():
    return {"takeoffs": list(_takeoffs.keys()), "count": len(_takeoffs)}


@app.get("/takeoffs/{takeoff_id}")
async def get_takeoff(takeoff_id: str):
    if takeoff_id not in _takeoffs:
        raise HTTPException(status_code=404, detail="Takeoff not found")
    return _takeoffs[takeoff_id]


# ── Dashboard metrics (kept from original) ────────────────────────────────────

_metrics: dict[str, Any] = {
    "active_services": 0, "active_workflows": 0,
    "total_takeoffs": 0, "recent_events": [],
}


@vertical.on_event("workflow.completed")
async def on_workflow_completed(event: EventPayload):
    _metrics["active_workflows"] = max(0, _metrics["active_workflows"] - 1)


@app.get("/metrics")
async def get_metrics():
    _metrics["total_takeoffs"] = len(_takeoffs)
    return _metrics


@app.get("/")
async def root():
    return {"service": "omniscale", "status": "operational", "takeoffs": len(_takeoffs)}
