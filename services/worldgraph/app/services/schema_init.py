"""Worldgraph table bootstrap for runtime safety."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from packages.models import (
    WorldgraphEntityAliasRecord,
    WorldgraphEntityCategoryRecord,
    WorldgraphEntityEmbeddingRecord,
    WorldgraphEntityIdentifierRecord,
    WorldgraphEntityProposalRecord,
    WorldgraphEntityProvenanceRecord,
    WorldgraphEntityRecord,
    WorldgraphEntityRelationshipRecord,
    WorldgraphIngestJobRecord,
    WorldgraphProposalSourceRecord,
    WorldgraphRawObjectRecord,
    WorldgraphRawRecordRecord,
    WorldgraphSearchDocumentRecord,
    WorldgraphTravelRawAirlineRecord,
    WorldgraphTravelRawAirportRecord,
    WorldgraphTravelRawRouteRecord,
)
from packages.models.base import Base


WORLDGRAPH_TABLES = [
    WorldgraphIngestJobRecord.__table__,
    WorldgraphRawObjectRecord.__table__,
    WorldgraphRawRecordRecord.__table__,
    WorldgraphEntityProposalRecord.__table__,
    WorldgraphProposalSourceRecord.__table__,
    WorldgraphEntityRecord.__table__,
    WorldgraphEntityAliasRecord.__table__,
    WorldgraphEntityIdentifierRecord.__table__,
    WorldgraphEntityCategoryRecord.__table__,
    WorldgraphEntityRelationshipRecord.__table__,
    WorldgraphEntityProvenanceRecord.__table__,
    WorldgraphSearchDocumentRecord.__table__,
    WorldgraphEntityEmbeddingRecord.__table__,
    WorldgraphTravelRawAirportRecord.__table__,
    WorldgraphTravelRawAirlineRecord.__table__,
    WorldgraphTravelRawRouteRecord.__table__,
]


def ensure_worldgraph_schema(db: Session) -> None:
    bind = getattr(db, "bind", None)
    if bind is None:
        return
    # Run schema creation and table DDL on the same connection/transaction.
    with bind.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS worldgraph"))
        Base.metadata.create_all(bind=conn, tables=WORLDGRAPH_TABLES)

