"""
Domain entity ORM models — building elements, document chunks, issues.
These are the structured records that are the authoritative source of truth.
Implements: Data Truth Hierarchy §7 — structured domain records are tier 1 truth.
"""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

from .base import Base


class BuildingElementRecord(Base):
    __tablename__ = "building_elements"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # format: elem_<ulid>
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id"), nullable=False)
    source_file_id: Mapped[str] = mapped_column(String, ForeignKey("project_files.id"), nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    properties: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class DocumentChunkRecord(Base):
    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # format: chunk_<ulid>
    file_id: Mapped[str] = mapped_column(String, ForeignKey("project_files.id"), nullable=False)
    page: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)


class IssueRecord(Base):
    __tablename__ = "issues"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # format: issue_<ulid>
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id"), nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[str] = mapped_column(String, nullable=False)  # low | medium | high
    source_refs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
