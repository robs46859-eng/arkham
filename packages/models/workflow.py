"""
Workflow run and step ORM models.
Implements: System Contracts — Workflow Contract.
All workflow state is persisted for restart and audit per build rules §6.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

from .base import Base


class WorkflowRunRecord(Base):
    __tablename__ = "workflow_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # format: wf_<ulid>
    tenant_id: Mapped[str] = mapped_column(String, nullable=False)
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id"), nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)  # running | complete | failed | paused
    approval_state: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="not_required",
    )  # not_required | pending | approved | rejected
    current_step: Mapped[str] = mapped_column(String, nullable=False)
    approval_requested_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    approval_resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    approval_actor_id: Mapped[str | None] = mapped_column(String, nullable=True)
    approval_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    checkpoint: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class WorkflowStepRecord(Base):
    __tablename__ = "workflow_steps"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    workflow_id: Mapped[str] = mapped_column(String, ForeignKey("workflow_runs.id"), nullable=False)
    step_name: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    checkpoint: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
