"""Worldgraph schemas shared across services."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

WorldgraphNamespace = Literal["travel", "property"]
WorldgraphEntityType = Literal["airport", "airline", "route", "place", "poi", "property", "unit"]
WorldgraphProposalStatus = Literal["pending", "approved", "rejected", "auto_promoted"]
WorldgraphIngestStatus = Literal["pending", "running", "complete", "failed"]


class WorldgraphAlias(BaseModel):
    alias: str
    language_code: str | None = None
    alias_type: str = "name_variant"
    is_primary: bool = False


class WorldgraphIdentifier(BaseModel):
    scheme: str
    value: str


class WorldgraphEntity(BaseModel):
    entity_id: str
    namespace: WorldgraphNamespace
    entity_type: WorldgraphEntityType
    display_name: str
    description: str | None = None
    canonical_slug: str | None = None
    aliases: list[WorldgraphAlias] = Field(default_factory=list)
    identifiers: list[WorldgraphIdentifier] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    canonical_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class WorldgraphSearchResult(BaseModel):
    entity: WorldgraphEntity
    score: float


class WorldgraphProposal(BaseModel):
    proposal_id: str
    namespace: WorldgraphNamespace
    proposal_type: str
    status: WorldgraphProposalStatus
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str | None = None
    draft_entity_json: dict[str, Any] = Field(default_factory=dict)
    dedupe_candidates_json: list[dict[str, Any]] = Field(default_factory=list)
    created_by_job_id: str | None = None
    created_at: datetime
    resolved_at: datetime | None = None
    resolved_by: str | None = None


class WorldgraphIngestJob(BaseModel):
    job_id: str
    namespace: WorldgraphNamespace
    source_name: str
    status: WorldgraphIngestStatus
    manifest_uri: str | None = None
    stats_json: dict[str, Any] = Field(default_factory=dict)
    error_json: dict[str, Any] = Field(default_factory=dict)
    started_at: datetime
    finished_at: datetime | None = None


class WorldgraphIngestRequest(BaseModel):
    source_name: Literal["openflights"]


class WorldgraphEntityCreate(BaseModel):
    entity_type: WorldgraphEntityType
    display_name: str
    description: str | None = None
    canonical_json: dict[str, Any] = Field(default_factory=dict)
    aliases: list[WorldgraphAlias] = Field(default_factory=list)
    identifiers: list[WorldgraphIdentifier] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)

