"""
Cyberscribe — Technical Specification & Documentation Vertical.
Generates CSI MasterFormat specification sections, issue registers,
and project documentation from BIM data and project descriptions.
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx
from fastapi import HTTPException
from pydantic import BaseModel, Field

from packages.vertical_base import VerticalBase

vertical = VerticalBase(
    service_id="cyberscribe",
    title="Cyberscribe — Technical Documentation",
    port=8000,
    capabilities=["spec_generation", "documentation", "issue_register"],
    event_subscriptions=[],
)

app = vertical.app

# ── LLM helper ───────────────────────────────────────────────────────────────

async def _call_claude(system_prompt: str, user_message: str, model: str = "claude-3-5-sonnet-20241022") -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=502, detail="ANTHROPIC_API_KEY not configured")
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 8192,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_message}],
            },
        )
        resp.raise_for_status()
        return resp.json()["content"][0]["text"]


# ── Request / Response models ─────────────────────────────────────────────────

class SpecSection(BaseModel):
    section_number: str   # e.g. "03 30 00"
    section_title: str    # e.g. "Cast-in-Place Concrete"
    part_1_general: str
    part_2_products: str
    part_3_execution: str


class SpecRequest(BaseModel):
    project_name: str
    project_type: str = "commercial"
    scope_description: str
    materials_noted: list[str] = Field(default_factory=list)
    standards_required: list[str] = Field(default_factory=list)  # e.g. ["ACI 318", "ASTM A615"]
    divisions_requested: list[str] = Field(default_factory=list) # e.g. ["03", "05", "09"]
    bim_data: dict[str, Any] = Field(default_factory=dict)


class SpecResponse(BaseModel):
    project_name: str
    sections: list[SpecSection]
    general_notes: list[str]
    referenced_standards: list[str]


class IssueRegisterRequest(BaseModel):
    project_name: str
    document_summary: str
    known_conflicts: list[str] = Field(default_factory=list)
    disciplines: list[str] = Field(default_factory=lambda: ["Architectural", "Structural", "MEP"])


class Issue(BaseModel):
    issue_id: str
    discipline: str
    severity: str  # Critical / Major / Minor
    location: str
    description: str
    recommendation: str
    status: str = "Open"


class IssueRegisterResponse(BaseModel):
    project_name: str
    total_issues: int
    critical: int
    major: int
    minor: int
    issues: list[Issue]


_specs: dict[str, dict] = {}
_registers: dict[str, dict] = {}

_SPEC_SYSTEM = """You are a licensed architect and specification writer with 20+ years of AEC experience.
You write precise, professional CSI MasterFormat 3-part specifications.

Respond with valid JSON only — no markdown, no code fences.

Structure:
{
  "sections": [
    {
      "section_number": "03 30 00",
      "section_title": "Cast-in-Place Concrete",
      "part_1_general": "Full Part 1 text with subsections...",
      "part_2_products": "Full Part 2 text with subsections...",
      "part_3_execution": "Full Part 3 text with subsections..."
    }
  ],
  "general_notes": ["string"],
  "referenced_standards": ["ASTM A615", "ACI 318", ...]
}

Each section must be professional, complete, and reference appropriate industry standards (ASTM, ACI, AISC, etc.).
Write at a minimum 3 sections. Be thorough and technically precise."""

_ISSUE_SYSTEM = """You are an expert construction document reviewer and BIM coordinator.
Your job is to identify coordination issues, contradictions, and missing information across project documents.

Respond with valid JSON only — no markdown, no code fences.

Structure:
{
  "issues": [
    {
      "issue_id": "ISS-001",
      "discipline": "Structural",
      "severity": "Critical",
      "location": "Grid A/3, Level 2",
      "description": "Structural beam at elevation 24'-0\" conflicts with HVAC duct shown at 23'-6\" on MEP drawings.",
      "recommendation": "Coordinate beam depth or reroute ductwork. Structural engineer to confirm if beam can be raised.",
      "status": "Open"
    }
  ]
}

Generate realistic, specific issues. Include Critical, Major, and Minor severity items.
Issue IDs must be sequential: ISS-001, ISS-002, etc."""


# ── Routes ───────────────────────────────────────────────────────────────────

@app.post("/spec", response_model=SpecResponse)
async def generate_spec(req: SpecRequest) -> SpecResponse:
    """Generate CSI MasterFormat specification sections for a project."""
    divisions_str = (
        f"Focus on divisions: {', '.join(req.divisions_requested)}"
        if req.divisions_requested
        else "Select the most relevant divisions for this project type."
    )

    user_msg = f"""
Project: {req.project_name}
Type: {req.project_type}
Scope: {req.scope_description}
Materials: {', '.join(req.materials_noted) or 'Not specified'}
Required Standards: {', '.join(req.standards_required) or 'Standard industry references'}
{divisions_str}

BIM Data:
{json.dumps(req.bim_data, indent=2) if req.bim_data else "None provided — generate from scope."}

Generate complete, professional 3-part specifications.
""".strip()

    raw = await _call_claude(_SPEC_SYSTEM, user_msg)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}") + 1
        data = json.loads(raw[start:end])

    spec_id = f"spec_{len(_specs) + 1}"
    result = SpecResponse(
        project_name=req.project_name,
        sections=[SpecSection(**s) for s in data["sections"]],
        general_notes=data.get("general_notes", []),
        referenced_standards=data.get("referenced_standards", []),
    )
    _specs[spec_id] = result.model_dump()
    return result


@app.post("/issue-register", response_model=IssueRegisterResponse)
async def generate_issue_register(req: IssueRegisterRequest) -> IssueRegisterResponse:
    """Generate a coordination issue register from project document summary."""
    user_msg = f"""
Project: {req.project_name}
Disciplines: {', '.join(req.disciplines)}
Document Summary: {req.document_summary}
Known Conflicts: {'; '.join(req.known_conflicts) or 'None specified — identify from summary.'}

Generate a comprehensive issue register with coordination problems, contradictions, and missing info.
Include Critical, Major, and Minor severity issues across the disciplines.
""".strip()

    raw = await _call_claude(_ISSUE_SYSTEM, user_msg)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}") + 1
        data = json.loads(raw[start:end])

    issues = [Issue(**i) for i in data["issues"]]
    reg_id = f"reg_{len(_registers) + 1}"
    result = IssueRegisterResponse(
        project_name=req.project_name,
        total_issues=len(issues),
        critical=sum(1 for i in issues if i.severity == "Critical"),
        major=sum(1 for i in issues if i.severity == "Major"),
        minor=sum(1 for i in issues if i.severity == "Minor"),
        issues=issues,
    )
    _registers[reg_id] = result.model_dump()
    return result


@app.get("/specs")
async def list_specs():
    return {"specs": list(_specs.keys()), "count": len(_specs)}


@app.get("/specs/{spec_id}")
async def get_spec(spec_id: str):
    if spec_id not in _specs:
        raise HTTPException(status_code=404, detail="Spec not found")
    return _specs[spec_id]


@app.get("/issue-registers")
async def list_registers():
    return {"registers": list(_registers.keys()), "count": len(_registers)}


@app.get("/")
async def root():
    return {"service": "cyberscribe", "status": "operational", "specs": len(_specs), "registers": len(_registers)}
