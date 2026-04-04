"""
Domain entity schemas — building elements, document chunks, issues, schedules, markups.
Implements: System Contracts Document — Building Element, Document Chunk, Issue contracts.
These are the source-of-truth structured records for BIM data. Never generate without validation.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class IssueSeverity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class BuildingElement(BaseModel):
    """Normalized building element extracted from IFC or document sources."""

    element_id: str  # format: elem_<ulid>
    project_id: str  # format: proj_<ulid>
    category: str
    properties: dict[str, Any] = Field(default_factory=dict)
    source_file_id: str  # format: file_<ulid>
    created_at: datetime


class DocumentChunk(BaseModel):
    """Page-level text chunk extracted from a PDF source file."""

    chunk_id: str  # format: chunk_<ulid>
    file_id: str  # format: file_<ulid>
    page: int
    text: str
    confidence: float = Field(ge=0.0, le=1.0)


class Issue(BaseModel):
    """Identified issue linked to project source records."""

    issue_id: str  # format: issue_<ulid>
    project_id: str  # format: proj_<ulid>
    type: str
    severity: IssueSeverity
    source_refs: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


class ScheduleRow(BaseModel):
    """Normalized schedule row from CSV, XLSX, or schedule PDF extraction."""

    row_id: str  # format: row_<ulid>
    project_id: str  # format: proj_<ulid>
    file_id: str  # format: file_<ulid>
    task_name: str
    start_date: str | None = None
    end_date: str | None = None
    status: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)


class MarkupRecord(BaseModel):
    """Parsed markup or annotation record from an annotated document or image."""

    markup_id: str  # format: markup_<ulid>
    project_id: str  # format: proj_<ulid>
    file_id: str  # format: file_<ulid>
    page: int | None = None
    annotation_text: str
    annotation_type: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
