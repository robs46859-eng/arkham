"""
Memory contract schema.
Implements: System Contracts Document — Memory Contract
Memory is assistive context only — never authoritative over structured BIM records.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class MemoryNote(BaseModel):
    """Scoped memory note stored by the memory service."""

    note_id: str  # format: mem_<ulid>
    tenant_id: str  # format: tenant_<ulid>
    project_id: str  # format: proj_<ulid>
    content: str
    tags: list[str] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)  # references to other note_ids or entity IDs
