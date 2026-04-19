"""
AI Consistency Lab Vertical
Implements: Model testing, validation, consistency analysis, and cross-document coordination checking.
"""

from __future__ import annotations

import json
import os
import uuid
import datetime
from typing import Any, Dict, List

import httpx
from fastapi import HTTPException
from pydantic import BaseModel, Field

from packages.vertical_base import VerticalBase
from packages.schemas.gateway import InferenceRequest, InferenceResponse, TaskType, InferenceInput, ModelTier
from .settings import get_settings

settings = get_settings()

# ── Vertical Setup ───────────────────────────────────────────────────────────

vertical = VerticalBase(
    service_id="ai_consistency",
    title="AI Consistency Lab",
    port=8000,
    capabilities=[
        "model-validation", 
        "consistency-analysis", 
        "consistency_check", 
        "coordination_review", 
        "compliance_gap"
    ],
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
                "max_tokens": 6144,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_message}],
            },
        )
        resp.raise_for_status()
        return resp.json()["content"][0]["text"]


# ── Schemas: Model Comparison ────────────────────────────────────────────────

class ConsistencyTestRequest(BaseModel):
    test_name: str
    tenant_id: str
    project_id: str
    prompt: str
    model_a_tier: ModelTier = ModelTier.local
    model_b_tier: ModelTier = ModelTier.mid
    criteria: List[str] = Field(default_factory=list)


class ConsistencyTestResult(BaseModel):
    test_id: str
    timestamp: str
    request: ConsistencyTestRequest
    response_a: Dict[str, Any]
    response_b: Dict[str, Any]
    consistency_score: float
    analysis: str


# ── Schemas: Document Coordination ───────────────────────────────────────────

class DocumentSection(BaseModel):
    discipline: str      # Architectural, Structural, MEP, Civil, Landscape
    document_type: str   # Drawings, Specifications, Schedule, Report
    content: str         # Description or extracted text


class ConsistencyCheckRequest(BaseModel):
    project_name: str
    sections: list[DocumentSection]
    check_types: list[str] = Field(
        default_factory=lambda: ["contradictions", "missing_coordination", "code_compliance", "dimensional"]
    )
    applicable_codes: list[str] = Field(default_factory=lambda: ["IBC 2021", "ADA", "NFPA 101"])


class ConsistencyIssue(BaseModel):
    issue_id: str
    check_type: str       # contradiction / missing_coordination / code_compliance / dimensional
    severity: str         # Critical / Major / Minor
    disciplines_affected: list[str]
    location: str
    description: str
    recommendation: str
    reference: str = ""   # code section or drawing reference


class ConsistencyCheckResponse(BaseModel):
    project_name: str
    documents_reviewed: int
    consistency_score: float   # 0.0–100.0 (100 = perfect consistency)
    issues: list[ConsistencyIssue]
    critical_count: int
    major_count: int
    minor_count: int
    executive_summary: str
    recommended_actions: list[str]


# ── State ────────────────────────────────────────────────────────────────────

# In-memory stores for v1
test_results: Dict[str, ConsistencyTestResult] = {}
_checks: dict[str, dict] = {}


# ── Prompts ───────────────────────────────────────────────────────────────────

_SYSTEM = """You are an expert BIM coordinator and construction document reviewer with 25 years of AEC experience.
You specialize in multi-discipline coordination, catching contradictions between architectural, structural, and MEP drawings,
identifying code compliance gaps, and flagging missing information before construction.

Respond with valid JSON only — no markdown, no code fences.

Structure:
{
  "consistency_score": 78.5,
  "issues": [
    {
      "issue_id": "CHK-001",
      "check_type": "contradiction",
      "severity": "Critical",
      "disciplines_affected": ["Structural", "MEP"],
      "location": "Level 3, Grid C-4",
      "description": "Structural drawing S3.02 shows W18x35 beam at EL +36'-0\". MEP drawing M2.10 shows 24\" supply duct at EL +35'-6\". 6\" clearance is insufficient for beam depth plus fireproofing.",
      "recommendation": "MEP to lower duct or reroute. Coordinate with structural engineer to verify beam can be raised 6\".",
      "reference": "S3.02 / M2.10"
    }
  ],
  "executive_summary": "string",
  "recommended_actions": ["string"]
}

Be specific about locations, drawing references, and elevations. Use realistic AEC terminology.
Generate at least 5 issues covering different check types and severity levels.
Score: deduct 15 pts per Critical, 5 pts per Major, 1 pt per Minor from 100."""


# ── Routes: Model Comparison ─────────────────────────────────────────────────

@app.post("/tests/run", response_model=ConsistencyTestResult)
async def run_consistency_test(request: ConsistencyTestRequest):
    """
    Run a consistency test by querying two different model tiers via the Gateway.
    """
    test_id = f"test_{uuid.uuid4().hex[:8]}"
    
    # In a real implementation, we would call the gateway here.
    # For now, we simulate the gateway calls to keep the build ladder intact.
    
    # Mock Gateway Call A
    mock_response_a = {
        "model_used": request.model_a_tier,
        "output": {"text": f"Response from {request.model_a_tier} for: {request.prompt}"},
        "latency_ms": 150
    }
    
    # Mock Gateway Call B
    mock_response_b = {
        "model_used": request.model_b_tier,
        "output": {"text": f"Response from {request.model_b_tier} for: {request.prompt}"},
        "latency_ms": 450
    }
    
    # Logic to compare responses (Deterministic fallback)
    # If text is identical, score is 1.0. Otherwise 0.5 (placeholder).
    score = 1.0 if mock_response_a["output"]["text"] == mock_response_b["output"]["text"] else 0.5
    
    result = ConsistencyTestResult(
        test_id=test_id,
        timestamp=datetime.datetime.utcnow().isoformat(),
        request=request,
        response_a=mock_response_a,
        response_b=mock_response_b,
        consistency_score=score,
        analysis="Simulated consistency check. identical responses result in 1.0."
    )
    
    test_results[test_id] = result
    
    # Publish event to the bus
    await vertical.publish_event("consistency.test.completed", {
        "test_id": test_id,
        "score": score,
        "tenant_id": request.tenant_id
    })
    
    return result


@app.get("/tests/{test_id}", response_model=ConsistencyTestResult)
async def get_test_result(test_id: str):
    """Retrieve results of a previous consistency test."""
    if test_id not in test_results:
        raise HTTPException(status_code=404, detail="Test result not found")
    return test_results[test_id]


@app.get("/tests", response_model=List[str])
async def list_tests():
    """List IDs of completed consistency tests."""
    return list(test_results.keys())


# ── Routes: Document Coordination ───────────────────────────────────────────

@app.post("/check", response_model=ConsistencyCheckResponse)
async def run_consistency_check(req: ConsistencyCheckRequest) -> ConsistencyCheckResponse:
    """Run cross-document consistency check across multiple disciplines."""
    docs_text = "\n\n".join(
        f"--- {s.discipline} / {s.document_type} ---\n{s.content}"
        for s in req.sections
    )

    user_msg = f"""
Project: {req.project_name}
Applicable Codes: {', '.join(req.applicable_codes)}
Check Types Requested: {', '.join(req.check_types)}
Documents to Review ({len(req.sections)} sections):

{docs_text}

Perform a comprehensive coordination review. Identify contradictions, missing coordination,
code compliance gaps, and dimensional conflicts across all disciplines.
""".strip()

    raw = await _call_claude(_SYSTEM, user_msg)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}") + 1
        data = json.loads(raw[start:end])

    issues = [ConsistencyIssue(**i) for i in data["issues"]]
    check_id = f"check_{len(_checks) + 1}"
    result = ConsistencyCheckResponse(
        project_name=req.project_name,
        documents_reviewed=len(req.sections),
        consistency_score=float(data["consistency_score"]),
        issues=issues,
        critical_count=sum(1 for i in issues if i.severity == "Critical"),
        major_count=sum(1 for i in issues if i.severity == "Major"),
        minor_count=sum(1 for i in issues if i.severity == "Minor"),
        executive_summary=data["executive_summary"],
        recommended_actions=data["recommended_actions"],
    )
    _checks[check_id] = result.model_dump()
    return result


@app.get("/checks")
async def list_checks():
    return {"checks": list(_checks.keys()), "count": len(_checks)}


@app.get("/checks/{check_id}")
async def get_check(check_id: str):
    if check_id not in _checks:
        raise HTTPException(status_code=404, detail="Check not found")
    return _checks[check_id]


# ── General Routes ───────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "service": "ai_consistency",
        "status": "operational",
        "capabilities": vertical.capabilities,
        "metrics": {
            "model_tests": len(test_results),
            "doc_checks": len(_checks)
        }
    }
