"""
Workflow orchestration endpoints.
Implements: Service Spec §3.5 core endpoints.
  POST /v1/workflows/start         — start a named workflow
  GET  /v1/workflows/{workflow_id} — get run status
  GET  /v1/workflows/{workflow_id}/steps — get step-level progress
  POST /v1/workflows/{workflow_id}/retry — retry from last checkpoint
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from packages.db import get_db
from packages.models.workflow import WorkflowRunRecord, WorkflowStepRecord
from packages.schemas import (
    WorkflowApprovalState,
    WorkflowRun,
    WorkflowStep,
    WorkflowStatus,
)

router = APIRouter(prefix="/v1/workflows", tags=["workflows"])


class WorkflowStartRequest(BaseModel):
    tenant_id: str  # format: tenant_<ulid>
    project_id: str  # format: proj_<ulid>
    workflow_type: str  # e.g. "project_intake", "codebase_audit"
    inputs: dict[str, Any] = {}


def _to_schema(run: WorkflowRunRecord, steps: list[WorkflowStepRecord]) -> WorkflowRun:
    return WorkflowRun(
        workflow_id=run.id,
        type=run.type,
        tenant_id=run.tenant_id,
        project_id=run.project_id,
        status=WorkflowStatus(run.status),
        approval_state=WorkflowApprovalState(run.approval_state),
        current_step=run.current_step,
        approval_requested_at=run.approval_requested_at,
        approval_resolved_at=run.approval_resolved_at,
        approval_actor_id=run.approval_actor_id,
        approval_notes=run.approval_notes,
        checkpoint=run.checkpoint,
        steps=[
            WorkflowStep(
                step_name=s.step_name,
                status=WorkflowStatus(s.status),
                started_at=s.started_at,
                completed_at=s.completed_at,
                error=s.error,
                checkpoint=s.checkpoint,
            )
            for s in steps
        ],
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


@router.post("/start", response_model=WorkflowRun)
async def start_workflow(request: WorkflowStartRequest, db: Session = Depends(get_db)) -> WorkflowRun:
    """
    Start a named workflow. Persists initial run record and dispatches first step.
    Workflow types: codebase_audit, project_intake, project_analysis.
    """
    now = datetime.utcnow()
    workflow_id = f"wf_{uuid.uuid4().hex}"

    # First step based on type
    first_step = "ingest_context" if request.workflow_type == "codebase_audit" else "file_registration"

    run = WorkflowRunRecord(
        id=workflow_id,
        tenant_id=request.tenant_id,
        project_id=request.project_id,
        type=request.workflow_type,
        status=WorkflowStatus.running.value,
        approval_state=WorkflowApprovalState.not_required.value,
        current_step=first_step,
        checkpoint={"inputs": request.inputs},
        created_at=now,
        updated_at=now,
    )
    db.add(run)

    step = WorkflowStepRecord(
        id=f"step_{uuid.uuid4().hex}",
        workflow_id=workflow_id,
        step_name=first_step,
        status=WorkflowStatus.running.value,
        started_at=now,
        checkpoint={},
    )
    db.add(step)
    db.commit()
    db.refresh(run)

    return _to_schema(run, [step])


@router.get("/{workflow_id}", response_model=WorkflowRun)
async def get_workflow(workflow_id: str, db: Session = Depends(get_db)) -> WorkflowRun:
    """Get current workflow run status from database."""
    run = db.query(WorkflowRunRecord).filter(WorkflowRunRecord.id == workflow_id).first()
    if not run:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")
    
    steps = db.query(WorkflowStepRecord).filter(WorkflowStepRecord.workflow_id == workflow_id).all()
    return _to_schema(run, steps)


@router.get("/{workflow_id}/steps", response_model=list[WorkflowStep])
async def get_workflow_steps(workflow_id: str, db: Session = Depends(get_db)) -> list[WorkflowStep]:
    """Get step-level progress for a workflow run."""
    steps = db.query(WorkflowStepRecord).filter(WorkflowStepRecord.workflow_id == workflow_id).all()
    return [
        WorkflowStep(
            step_name=s.step_name,
            status=WorkflowStatus(s.status),
            started_at=s.started_at,
            completed_at=s.completed_at,
            error=s.error,
            checkpoint=s.checkpoint,
        )
        for s in steps
    ]


@router.post("/{workflow_id}/retry", response_model=WorkflowRun)
async def retry_workflow(workflow_id: str, db: Session = Depends(get_db)) -> WorkflowRun:
    """Retry a failed workflow from its last persisted checkpoint."""
    run = db.query(WorkflowRunRecord).filter(WorkflowRunRecord.id == workflow_id).first()
    if not run:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")

    if run.status != WorkflowStatus.failed.value:
        raise HTTPException(status_code=400, detail="Only failed workflows can be retried")

    run.status = WorkflowStatus.running.value
    run.updated_at = datetime.utcnow()
    
    # Create new step for the retry
    step = WorkflowStepRecord(
        id=f"step_{uuid.uuid4().hex}",
        workflow_id=workflow_id,
        step_name=run.current_step,
        status=WorkflowStatus.running.value,
        started_at=datetime.utcnow(),
        checkpoint=run.checkpoint,
    )
    db.add(step)
    db.commit()
    db.refresh(run)

    steps = db.query(WorkflowStepRecord).filter(WorkflowStepRecord.workflow_id == workflow_id).all()
    return _to_schema(run, steps)


@router.get("/{workflow_id}/artifacts", response_model=list[dict[str, Any]])
async def get_workflow_artifacts(workflow_id: str, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    """Retrieve artifacts (like CodebaseAuditResult) produced by this workflow."""
    audits = db.query(CodebaseAuditRecord).filter(CodebaseAuditRecord.workflow_id == workflow_id).all()
    return [
        {
            "id": a.id,
            "type": "codebase_audit",
            "summary": a.summary,
            "findings": a.findings,
            "evidence": a.evidence,
            "proposed_actions": a.proposed_actions,
            "created_at": a.created_at,
        }
        for a in audits
    ]


class ApprovalRequest(BaseModel):
    actor_id: str
    notes: str | None = None


@router.post("/{workflow_id}/approve", response_model=WorkflowRun)
async def approve_workflow(workflow_id: str, request: ApprovalRequest, db: Session = Depends(get_db)) -> WorkflowRun:
    """Approve a paused workflow and resume execution."""
    run = db.query(WorkflowRunRecord).filter(WorkflowRunRecord.id == workflow_id).first()
    if not run:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")

    if run.approval_state != WorkflowApprovalState.pending.value:
        raise HTTPException(status_code=400, detail="Workflow is not in PENDING approval state")

    run.approval_state = WorkflowApprovalState.approved.value
    run.status = WorkflowStatus.running.value
    run.approval_resolved_at = datetime.utcnow()
    run.approval_actor_id = request.actor_id
    run.approval_notes = request.notes
    run.updated_at = datetime.utcnow()

    # Update the step status so the worker picks it up
    step = (
        db.query(WorkflowStepRecord)
        .filter(WorkflowStepRecord.workflow_id == workflow_id)
        .filter(WorkflowStepRecord.step_name == run.current_step)
        .filter(WorkflowStepRecord.status == WorkflowStatus.paused.value)
        .first()
    )
    if step:
        step.status = WorkflowStatus.running.value
        step.started_at = datetime.utcnow()

    db.commit()
    db.refresh(run)
    steps = db.query(WorkflowStepRecord).filter(WorkflowStepRecord.workflow_id == workflow_id).all()
    return _to_schema(run, steps)


@router.post("/{workflow_id}/reject", response_model=WorkflowRun)
async def reject_workflow(workflow_id: str, request: ApprovalRequest, db: Session = Depends(get_db)) -> WorkflowRun:
    """Reject a paused workflow and stop execution."""
    run = db.query(WorkflowRunRecord).filter(WorkflowRunRecord.id == workflow_id).first()
    if not run:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")

    if run.approval_state != WorkflowApprovalState.pending.value:
        raise HTTPException(status_code=400, detail="Workflow is not in PENDING approval state")

    run.approval_state = WorkflowApprovalState.rejected.value
    run.status = WorkflowStatus.failed.value  # Rejection is a terminal failure state for this path
    run.approval_resolved_at = datetime.utcnow()
    run.approval_actor_id = request.actor_id
    run.approval_notes = request.notes
    run.updated_at = datetime.utcnow()

    # Mark the step as failed
    step = (
        db.query(WorkflowStepRecord)
        .filter(WorkflowStepRecord.workflow_id == workflow_id)
        .filter(WorkflowStepRecord.step_name == run.current_step)
        .filter(WorkflowStepRecord.status == WorkflowStatus.paused.value)
        .first()
    )
    if step:
        step.status = WorkflowStatus.failed.value
        step.error = f"Rejected by {request.actor_id}: {request.notes}"
        step.completed_at = datetime.utcnow()

    db.commit()
    db.refresh(run)
    steps = db.query(WorkflowStepRecord).filter(WorkflowStepRecord.workflow_id == workflow_id).all()
    return _to_schema(run, steps)
