"""
Workflow orchestration endpoints.
Implements: Service Spec §3.5 core endpoints.
  POST /v1/workflows/start         — start a named workflow
  GET  /v1/workflows/{workflow_id} — get run status
  GET  /v1/workflows/{workflow_id}/steps — get step-level progress
  POST /v1/workflows/{workflow_id}/retry — retry from last checkpoint
STUB: checkpoint store, step runner, retry manager, dead-letter handler.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from packages.schemas import WorkflowRun, WorkflowStep, WorkflowStatus

router = APIRouter(prefix="/v1/workflows", tags=["workflows"])


class WorkflowStartRequest(BaseModel):
    tenant_id: str  # format: tenant_<ulid>
    project_id: str  # format: proj_<ulid>
    workflow_type: str  # e.g. "project_intake"
    inputs: dict[str, Any] = {}


@router.post("/start", response_model=WorkflowRun)
async def start_workflow(request: WorkflowStartRequest) -> WorkflowRun:
    """
    Start a named workflow. Persists initial run record and dispatches first step.
    STUB: checkpoint is persisted in workflow_runs table; step dispatch goes to queue.
    Workflow types: project_intake, project_analysis, issue_register, deliverable_generation.
    """
    now = datetime.utcnow()
    workflow_id = f"wf_{uuid.uuid4().hex}"

    # STUB: create WorkflowRunRecord, dispatch first step to step_runner
    return WorkflowRun(
        workflow_id=workflow_id,
        type=request.workflow_type,
        tenant_id=request.tenant_id,
        project_id=request.project_id,
        status=WorkflowStatus.running,
        current_step="file_registration",
        checkpoint={"inputs": request.inputs},
        steps=[
            WorkflowStep(
                step_name="file_registration",
                status=WorkflowStatus.running,
                started_at=now,
            )
        ],
        created_at=now,
        updated_at=now,
    )


@router.get("/{workflow_id}", response_model=WorkflowRun)
async def get_workflow(workflow_id: str) -> WorkflowRun:
    """
    Get current workflow run status.
    STUB: query workflow_runs table by workflow_id.
    """
    if not workflow_id.startswith("wf_"):
        raise HTTPException(status_code=400, detail="Invalid workflow_id format. Expected: wf_<ulid>")
    raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found (stub — DB not yet wired)")


@router.get("/{workflow_id}/steps", response_model=list[WorkflowStep])
async def get_workflow_steps(workflow_id: str) -> list[WorkflowStep]:
    """
    Get step-level progress for a workflow run.
    STUB: query workflow_steps table by workflow_id.
    """
    if not workflow_id.startswith("wf_"):
        raise HTTPException(status_code=400, detail="Invalid workflow_id format. Expected: wf_<ulid>")
    return []


@router.post("/{workflow_id}/retry", response_model=WorkflowRun)
async def retry_workflow(workflow_id: str) -> WorkflowRun:
    """
    Retry a failed workflow from its last persisted checkpoint.
    STUB: load checkpoint from workflow_runs, re-dispatch from current_step.
    Idempotency: retry must not create duplicate artifacts.
    """
    if not workflow_id.startswith("wf_"):
        raise HTTPException(status_code=400, detail="Invalid workflow_id format. Expected: wf_<ulid>")
    raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found (stub — DB not yet wired)")
