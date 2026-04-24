"""Worldgraph ORM models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base

WORLDGRAPH_SCHEMA = "worldgraph"


class WorldgraphIngestJobRecord(Base):
    __tablename__ = "wg_ingest_jobs"
    __table_args__ = {"schema": WORLDGRAPH_SCHEMA}

    job_id: Mapped[str] = mapped_column(String, primary_key=True)
    namespace: Mapped[str] = mapped_column(String, nullable=False, index=True)
    source_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String, nullable=False, index=True)
    manifest_uri: Mapped[str | None] = mapped_column(String, nullable=True)
    stats_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    error_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class WorldgraphRawObjectRecord(Base):
    __tablename__ = "wg_raw_objects"
    __table_args__ = {"schema": WORLDGRAPH_SCHEMA}

    raw_object_id: Mapped[str] = mapped_column(String, primary_key=True)
    namespace: Mapped[str] = mapped_column(String, nullable=False, index=True)
    source_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    object_uri: Mapped[str] = mapped_column(String, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String, nullable=False, index=True)
    content_type: Mapped[str] = mapped_column(String, nullable=False, default="application/octet-stream")
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)


class WorldgraphRawRecordRecord(Base):
    __tablename__ = "wg_raw_records"
    __table_args__ = (
        UniqueConstraint(
            "namespace",
            "source_name",
            "source_primary_key",
            "payload_hash",
            name="uq_wg_raw_record_idempotency",
        ),
        {"schema": WORLDGRAPH_SCHEMA},
    )

    raw_record_id: Mapped[str] = mapped_column(String, primary_key=True)
    job_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    namespace: Mapped[str] = mapped_column(String, nullable=False, index=True)
    source_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    source_primary_key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    raw_object_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    payload_hash: Mapped[str] = mapped_column(String, nullable=False, index=True)
    schema_version: Mapped[str] = mapped_column(String, nullable=False, default="v1")
    quarantine_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)


class WorldgraphEntityProposalRecord(Base):
    __tablename__ = "wg_entity_proposals"
    __table_args__ = {"schema": WORLDGRAPH_SCHEMA}

    proposal_id: Mapped[str] = mapped_column(String, primary_key=True)
    namespace: Mapped[str] = mapped_column(String, nullable=False, index=True)
    proposal_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    draft_entity_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    dedupe_candidates_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_by_job_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String, nullable=True)


class WorldgraphProposalSourceRecord(Base):
    __tablename__ = "wg_proposal_sources"
    __table_args__ = {"schema": WORLDGRAPH_SCHEMA}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    proposal_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    raw_record_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    excerpt_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    source_weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)


class WorldgraphEntityRecord(Base):
    __tablename__ = "wg_entities"
    __table_args__ = {"schema": WORLDGRAPH_SCHEMA}

    entity_id: Mapped[str] = mapped_column(String, primary_key=True)
    namespace: Mapped[str] = mapped_column(String, nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    canonical_slug: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    canonical_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)


class WorldgraphEntityAliasRecord(Base):
    __tablename__ = "wg_entity_aliases"
    __table_args__ = (
        UniqueConstraint("entity_id", "alias", "alias_type", name="uq_wg_entity_alias"),
        {"schema": WORLDGRAPH_SCHEMA},
    )

    alias_id: Mapped[str] = mapped_column(String, primary_key=True)
    entity_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    alias: Mapped[str] = mapped_column(String, nullable=False, index=True)
    language_code: Mapped[str | None] = mapped_column(String, nullable=True)
    alias_type: Mapped[str] = mapped_column(String, nullable=False, default="name_variant")
    is_primary: Mapped[bool] = mapped_column(nullable=False, default=False)


class WorldgraphEntityIdentifierRecord(Base):
    __tablename__ = "wg_entity_identifiers"
    __table_args__ = {"schema": WORLDGRAPH_SCHEMA}

    identifier_id: Mapped[str] = mapped_column(String, primary_key=True)
    entity_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    namespace: Mapped[str] = mapped_column(String, nullable=False, index=True)
    scheme: Mapped[str] = mapped_column(String, nullable=False, index=True)
    value: Mapped[str] = mapped_column(String, nullable=False, index=True)


class WorldgraphEntityCategoryRecord(Base):
    __tablename__ = "wg_entity_categories"
    __table_args__ = (
        UniqueConstraint("entity_id", "category", name="uq_wg_entity_category"),
        {"schema": WORLDGRAPH_SCHEMA},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    category: Mapped[str] = mapped_column(String, nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)


class WorldgraphEntityRelationshipRecord(Base):
    __tablename__ = "wg_entity_relationships"
    __table_args__ = {"schema": WORLDGRAPH_SCHEMA}

    relationship_id: Mapped[str] = mapped_column(String, primary_key=True)
    from_entity_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    relationship_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    to_entity_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    relationship_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class WorldgraphEntityProvenanceRecord(Base):
    __tablename__ = "wg_entity_provenance"
    __table_args__ = {"schema": WORLDGRAPH_SCHEMA}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    raw_record_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    proposal_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    field_path: Mapped[str] = mapped_column(String, nullable=False)
    source_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    accepted_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)


class WorldgraphSearchDocumentRecord(Base):
    __tablename__ = "wg_search_documents"
    __table_args__ = {"schema": WORLDGRAPH_SCHEMA}

    entity_id: Mapped[str] = mapped_column(String, primary_key=True)
    search_text: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)


class WorldgraphEntityEmbeddingRecord(Base):
    __tablename__ = "wg_entity_embeddings"
    __table_args__ = (
        UniqueConstraint("entity_id", "embedding_model", "embedding_version", name="uq_wg_entity_embedding_version"),
        {"schema": WORLDGRAPH_SCHEMA},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    embedding_model: Mapped[str] = mapped_column(String, nullable=False, index=True)
    embedding_version: Mapped[str] = mapped_column(String, nullable=False, index=True)
    embedding_json: Mapped[list[float]] = mapped_column(JSON, nullable=False, default=list)
    content_hash: Mapped[str] = mapped_column(String, nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)


class WorldgraphTravelRawAirportRecord(Base):
    __tablename__ = "wg_travel_raw_airports"
    __table_args__ = {"schema": WORLDGRAPH_SCHEMA}

    raw_record_id: Mapped[str] = mapped_column(String, primary_key=True)
    airport_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    city: Mapped[str | None] = mapped_column(String, nullable=True)
    country: Mapped[str | None] = mapped_column(String, nullable=True)
    iata: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    icao: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)


class WorldgraphTravelRawAirlineRecord(Base):
    __tablename__ = "wg_travel_raw_airlines"
    __table_args__ = {"schema": WORLDGRAPH_SCHEMA}

    raw_record_id: Mapped[str] = mapped_column(String, primary_key=True)
    airline_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    alias: Mapped[str | None] = mapped_column(String, nullable=True)
    iata: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    icao: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    callsign: Mapped[str | None] = mapped_column(String, nullable=True)
    country: Mapped[str | None] = mapped_column(String, nullable=True)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)


class WorldgraphTravelRawRouteRecord(Base):
    __tablename__ = "wg_travel_raw_routes"
    __table_args__ = {"schema": WORLDGRAPH_SCHEMA}

    raw_record_id: Mapped[str] = mapped_column(String, primary_key=True)
    route_key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    airline_code: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    source_airport: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    destination_airport: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    stops: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

