"""
AutoPitch — Architectural Proposal Generation Vertical.
Generates professional, client-facing project proposals from briefs,
firm profiles, and project data. Outputs structured proposal documents.
"""

from __future__ import annotations

import json
import os

import httpx
from fastapi import HTTPException
from pydantic import BaseModel, Field

from packages.vertical_base import VerticalBase

vertical = VerticalBase(
    service_id="autopitch",
    title="AutoPitch — Proposal Generator",
    port=8000,
    capabilities=["proposal_generation", "fee_schedule", "scope_writing"],
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

class FirmProfile(BaseModel):
    name: str
    years_in_business: int = 0
    specialties: list[str] = Field(default_factory=list)
    notable_projects: list[str] = Field(default_factory=list)
    team_size: int = 0
    licenses: list[str] = Field(default_factory=list)


class ProposalRequest(BaseModel):
    project_name: str
    client_name: str
    client_organization: str = ""
    project_type: str = "commercial"
    project_description: str
    estimated_construction_cost: float | None = None
    gross_floor_area_sqft: float | None = None
    location: str = ""
    timeline_months: int | None = None
    special_requirements: list[str] = Field(default_factory=list)
    firm: FirmProfile
    services_included: list[str] = Field(
        default_factory=lambda: [
            "Schematic Design", "Design Development",
            "Construction Documents", "Bidding & Negotiation",
            "Construction Administration"
        ]
    )
    fee_basis: str = "percentage"  # percentage / fixed / hourly


class ProposalSection(BaseModel):
    heading: str
    content: str


class FeeLineItem(BaseModel):
    phase: str
    description: str
    fee_usd: float
    percentage_of_total: float


class ProposalResponse(BaseModel):
    project_name: str
    client_name: str
    prepared_by: str
    sections: list[ProposalSection]
    fee_schedule: list[FeeLineItem]
    total_fee_usd: float
    fee_basis: str
    proposed_timeline_months: int
    validity_days: int = 30
    key_assumptions: list[str]
    exclusions: list[str]


_proposals: dict[str, dict] = {}

_SYSTEM = """You are an expert architectural business development writer who has written hundreds of winning proposals.
You write professional, compelling, and specific architectural proposals that win work.

Respond with valid JSON only — no markdown, no code fences.

Structure:
{
  "sections": [
    {
      "heading": "Executive Summary",
      "content": "Full section content..."
    },
    {
      "heading": "Understanding of Project",
      "content": "..."
    },
    {
      "heading": "Proposed Scope of Services",
      "content": "..."
    },
    {
      "heading": "Project Approach & Methodology",
      "content": "..."
    },
    {
      "heading": "Project Team",
      "content": "..."
    },
    {
      "heading": "Relevant Experience",
      "content": "..."
    },
    {
      "heading": "Proposed Schedule",
      "content": "..."
    }
  ],
  "fee_schedule": [
    {
      "phase": "Schematic Design",
      "description": "Develop conceptual design alternatives, program verification, massing studies",
      "fee_usd": 45000,
      "percentage_of_total": 15.0
    }
  ],
  "total_fee_usd": 300000,
  "proposed_timeline_months": 18,
  "key_assumptions": ["string"],
  "exclusions": ["string"]
}

Architecture fees: typically 6-12% of construction cost for full services.
Split by phase: SD 15%, DD 20%, CDs 40%, Bidding 5%, CA 20%.
Write in a professional, client-focused tone. Be specific about the project and client needs.
Include all 7 sections with substantive, project-specific content."""


# ── Routes ───────────────────────────────────────────────────────────────────

@app.post("/proposal", response_model=ProposalResponse)
async def generate_proposal(req: ProposalRequest) -> ProposalResponse:
    """Generate a complete architectural project proposal."""
    firm_str = f"""
Firm: {req.firm.name}
Years in Business: {req.firm.years_in_business}
Specialties: {', '.join(req.firm.specialties) or 'General architecture'}
Team Size: {req.firm.team_size or 'Not specified'} staff
Notable Projects: {'; '.join(req.firm.notable_projects) or 'Not specified'}
Licenses: {', '.join(req.firm.licenses) or 'Licensed architect(s)'}
""".strip()

    user_msg = f"""
Client: {req.client_name}{' / ' + req.client_organization if req.client_organization else ''}
Project: {req.project_name}
Type: {req.project_type}
Location: {req.location or 'Not specified'}
Description: {req.project_description}
Est. Construction Cost: {'${:,.0f}'.format(req.estimated_construction_cost) if req.estimated_construction_cost else 'TBD'}
GFA: {'{:,.0f} SF'.format(req.gross_floor_area_sqft) if req.gross_floor_area_sqft else 'TBD'}
Timeline: {f'{req.timeline_months} months' if req.timeline_months else 'To be determined'}
Services: {', '.join(req.services_included)}
Fee Basis: {req.fee_basis}
Special Requirements: {'; '.join(req.special_requirements) or 'None specified'}

{firm_str}

Generate a complete, winning architectural proposal tailored to this client and project.
Make the content specific, compelling, and professional. Reference the actual project details throughout.
""".strip()

    raw = await _call_claude(_SYSTEM, user_msg)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}") + 1
        data = json.loads(raw[start:end])

    proposal_id = f"proposal_{len(_proposals) + 1}"
    result = ProposalResponse(
        project_name=req.project_name,
        client_name=req.client_name,
        prepared_by=req.firm.name,
        sections=[ProposalSection(**s) for s in data["sections"]],
        fee_schedule=[FeeLineItem(**f) for f in data["fee_schedule"]],
        total_fee_usd=data["total_fee_usd"],
        fee_basis=req.fee_basis,
        proposed_timeline_months=data["proposed_timeline_months"],
        key_assumptions=data.get("key_assumptions", []),
        exclusions=data.get("exclusions", []),
    )
    _proposals[proposal_id] = result.model_dump()
    return result


@app.get("/proposals")
async def list_proposals():
    return {"proposals": list(_proposals.keys()), "count": len(_proposals)}


@app.get("/proposals/{proposal_id}")
async def get_proposal(proposal_id: str):
    if proposal_id not in _proposals:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return _proposals[proposal_id]


@app.get("/")
async def root():
    return {"service": "autopitch", "status": "operational", "proposals": len(_proposals)}
