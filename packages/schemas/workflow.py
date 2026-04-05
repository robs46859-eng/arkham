"""
Workflow contract schemas.
Implements: System Contracts Document — Workflow Contract
All workflows must be restartable — checkpoint is required.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WorkflowStatus(str, Enum):
    running = "running"
    complete = "complete"
    failed = "failed"
    paused = "paused"


class WorkflowStep(BaseModel):
    """Individual step record within a workflow run."""

    step_name: str
    status: WorkflowStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    checkpoint: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "step_name": "extract_rfis",
                "status": "running",
                "started_at": "2026-04-05T12:40:00Z",
                "completed_at": None,
                "error": None,
                "checkpoint": {"processed_pages": 12},
            }
        }
    )


class WorkflowRun(BaseModel):
    """Full workflow run record. Must be persisted and resumable from checkpoint."""

    workflow_id: str  # format: wf_<ulid>
    type: str
    tenant_id: str  # format: tenant_<ulid>
    project_id: str  # format: proj_<ulid>
    status: WorkflowStatus
    current_step: str
    checkpoint: dict[str, Any] = Field(default_factory=dict)
    steps: list[WorkflowStep] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "workflow_id": "wf_01hv6r7v6j8x7m4r9k2p1q3s4t",
                "type": "project_intake",
                "tenant_id": "tenant_01hv6n6j6h8x7m4r9k2p1q3s4t",
                "project_id": "proj_01hv6n8h0q9x2r4s6t8u1v3w5y",
                "status": "running",
                "current_step": "extract_rfis",
                "checkpoint": {"uploaded_files": 3},
                "steps": [
                    {
                        "step_name": "ingest_documents",
                        "status": "complete",
                        "started_at": "2026-04-05T12:35:00Z",
                        "completed_at": "2026-04-05T12:38:00Z",
                        "error": None,
                        "checkpoint": {"uploaded_files": 3},
                    }
                ],
                "created_at": "2026-04-05T12:35:00Z",
                "updated_at": "2026-04-05T12:40:00Z",
            }
        }
    )
