"""
Deliverable contract schema.
Implements: System Contracts Document — Deliverable Contract
Every deliverable must include source_trace and be reproducible from the same inputs.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class Deliverable(BaseModel):
    """Versioned deliverable artifact record."""

    deliverable_id: str  # format: deliv_<ulid>
    project_id: str  # format: proj_<ulid>
    type: str
    artifact_path: str
    source_trace: list[str] = Field(default_factory=list)  # list of file_<ulid> or elem_<ulid>
    created_at: datetime
