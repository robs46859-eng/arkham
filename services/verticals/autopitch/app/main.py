"""
AutoPitch — AEC Proposal and Pursuit Package Generation Vertical.
Generates proposal drafts, fee schedules, and exclusions from project briefs.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Header
from pydantic import BaseModel, Field

from packages.vertical_base import VerticalBase

# ── Initialization ───────────────────────────────────────────────────────────

vertical = VerticalBase(
    service_id="autopitch",
    title="AutoPitch — Proposal & Pursuit",
    port=8000,
    capabilities=["proposal_generation", "fee_modeling", "pursuit_analytics"],
    event_subscriptions=["lead.status_changed"],
)

app = vertical.app

# ── Models ───────────────────────────────────────────────────────────────────

class ProjectBrief(BaseModel):
    project_name: str
    project_type: str
    client_name: str
    context: str
    scope_notes: str
    timeline_months: int = 12
    pricing_strategy: str = "Lump Sum"

class ProposalOutput(BaseModel):
    id: str
    project_name: str
    proposal_text: str
    fee_schedule: List[Dict[str, Any]]
    exclusions: List[str]
    created_at: str

# ── Routes ───────────────────────────────────────────────────────────────────

@app.post("/generate", response_model=ProposalOutput)
async def generate_proposal(brief: ProjectBrief, x_tenant_id: str = Header(...)):
    """
    Generate a proposal package from a project brief.
    In a full implementation, this would call f-ai or an LLM directly.
    """
    proposal_id = f"prop_{uuid.uuid4().hex[:8]}"
    
    # Mock logic for generation
    fee_schedule = [
        {"phase": "Pre-Design", "fee": 25000, "type": brief.pricing_strategy},
        {"phase": "Schematic Design", "fee": 75000, "type": brief.pricing_strategy},
        {"phase": "Design Development", "fee": 125000, "type": brief.pricing_strategy},
    ]
    
    exclusions = [
        "Geotechnical surveys",
        "Hazardous material abatement",
        "Permit and filing fees paid to third parties"
    ]
    
    output = ProposalOutput(
        id=proposal_id,
        project_name=brief.project_name,
        proposal_text=f"# Proposal for {brief.project_name}\n\n## Client: {brief.client_name}\n\n{brief.context}\n\n### Scope of Work\n{brief.scope_notes}",
        fee_schedule=fee_schedule,
        exclusions=exclusions,
        created_at=datetime.now(timezone.utc).isoformat()
    )
    
    # In a real integrated flow, we might save this to PapaBase or a separate store
    await vertical.publish_event("proposal.generated", {
        "proposal_id": proposal_id,
        "project_name": brief.project_name,
        "tenant_id": x_tenant_id
    })
    
    return output

@app.get("/")
async def root():
    return {
        "service": "autopitch",
        "status": "operational",
        "capabilities": vertical.capabilities
    }
