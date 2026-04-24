"""
Workflow contract schemas.
Implements: System Contracts Document — Workflow Contract
All workflows must be restartable — checkpoint is required.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class WorkflowStatus(str, Enum):
    running = "running"
    complete = "complete"
    failed = "failed"
    paused = "paused"


class WorkflowApprovalState(str, Enum):
    not_required = "not_required"
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class WorkflowStep(BaseModel):
    """Individual step record within a workflow run."""

    step_name: str
    status: WorkflowStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    checkpoint: dict[str, Any] = Field(default_factory=dict)


class WorkflowRun(BaseModel):
    """Full workflow run record. Must be persisted and resumable from checkpoint."""

    workflow_id: str  # format: wf_<ulid>
    type: str
    tenant_id: str  # format: tenant_<ulid>
    project_id: str  # format: proj_<ulid>
    status: WorkflowStatus
    approval_state: WorkflowApprovalState = WorkflowApprovalState.not_required
    current_step: str
    approval_requested_at: datetime | None = None
    approval_resolved_at: datetime | None = None
    approval_actor_id: str | None = None
    approval_notes: str | None = None
    checkpoint: dict[str, Any] = Field(default_factory=dict)
    steps: list[WorkflowStep] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
