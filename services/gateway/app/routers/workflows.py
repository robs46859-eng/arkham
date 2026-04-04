"""
Workflow entry endpoints on the gateway.
Implements: Service Spec §1.5 — POST /v1/workflows/start, GET /v1/workflows/{workflow_id}.
The gateway initiates workflows and proxies status — orchestration service owns execution.
STUB: actual orchestration client (HTTP call to orchestration service) is next step.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from packages.schemas import WorkflowRun, WorkflowStatus
from ..middleware.auth import require_tenant

router = APIRouter(prefix="/v1/workflows", tags=["workflows"])


class WorkflowStartRequest(BaseModel):
    tenant_id: str  # format: tenant_<ulid>
    project_id: str  # format: proj_<ulid>
    workflow_type: str  # e.g. "project_intake"
    inputs: dict[str, Any] = {}


@router.post("/start", response_model=WorkflowRun)
async def start_workflow(
    request: WorkflowStartRequest,
    _auth: tuple[str, str] = Depends(require_tenant),
) -> WorkflowRun:
    """
    Initiate a workflow. Gateway creates the initial run record and hands off
    to the orchestration service.
    STUB: orchestration client call and DB persistence are next steps.
    """
    now = datetime.utcnow()
    workflow_id = f"wf_{uuid.uuid4().hex}"

    # STUB — replace with real orchestration service client call and DB write
    return WorkflowRun(
        workflow_id=workflow_id,
        type=request.workflow_type,
        tenant_id=request.tenant_id,
        project_id=request.project_id,
        status=WorkflowStatus.running,
        current_step="initializing",
        checkpoint={},
        steps=[],
        created_at=now,
        updated_at=now,
    )


@router.get("/{workflow_id}", response_model=WorkflowRun)
async def get_workflow(
    workflow_id: str,
    _auth: tuple[str, str] = Depends(require_tenant),
) -> WorkflowRun:
    """
    Look up workflow status by ID.
    STUB: query orchestration service or workflow_runs table.
    """
    if not workflow_id.startswith("wf_"):
        raise HTTPException(status_code=400, detail="Invalid workflow_id format. Expected: wf_<ulid>")

    # STUB — replace with real DB lookup
    raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found (stub — DB lookup not yet wired)")
