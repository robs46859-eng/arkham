"""create worldgraph schema and v1 tables

Revision ID: 20260423_0009
Revises: 20260421_0007
Create Date: 2026-04-23 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "20260423_0009"
down_revision = "20260421_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS worldgraph")
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "wg_ingest_jobs",
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("namespace", sa.String(), nullable=False),
        sa.Column("source_name", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("manifest_uri", sa.String(), nullable=True),
        sa.Column("stats_json", sa.JSON(), nullable=False),
        sa.Column("error_json", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("job_id"),
        schema="worldgraph",
    )
    op.create_index("ix_wg_ingest_jobs_namespace", "wg_ingest_jobs", ["namespace"], schema="worldgraph")
    op.create_index("ix_wg_ingest_jobs_source_name", "wg_ingest_jobs", ["source_name"], schema="worldgraph")
    op.create_index("ix_wg_ingest_jobs_status", "wg_ingest_jobs", ["status"], schema="worldgraph")

    op.create_table(
        "wg_raw_objects",
        sa.Column("raw_object_id", sa.String(), nullable=False),
        sa.Column("namespace", sa.String(), nullable=False),
        sa.Column("source_name", sa.String(), nullable=False),
        sa.Column("object_uri", sa.String(), nullable=False),
        sa.Column("checksum_sha256", sa.String(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("ingested_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("raw_object_id"),
        schema="worldgraph",
    )
    op.create_index("ix_wg_raw_objects_namespace", "wg_raw_objects", ["namespace"], schema="worldgraph")
    op.create_index("ix_wg_raw_objects_source_name", "wg_raw_objects", ["source_name"], schema="worldgraph")
    op.create_index("ix_wg_raw_objects_checksum_sha256", "wg_raw_objects", ["checksum_sha256"], schema="worldgraph")

    op.create_table(
        "wg_raw_records",
        sa.Column("raw_record_id", sa.String(), nullable=False),
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("namespace", sa.String(), nullable=False),
        sa.Column("source_name", sa.String(), nullable=False),
        sa.Column("source_primary_key", sa.String(), nullable=False),
        sa.Column("raw_object_id", sa.String(), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("payload_hash", sa.String(), nullable=False),
        sa.Column("schema_version", sa.String(), nullable=False),
        sa.Column("quarantine_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("raw_record_id"),
        sa.UniqueConstraint(
            "namespace",
            "source_name",
            "source_primary_key",
            "payload_hash",
            name="uq_wg_raw_record_idempotency",
        ),
        schema="worldgraph",
    )
    op.create_index("ix_wg_raw_records_job_id", "wg_raw_records", ["job_id"], schema="worldgraph")
    op.create_index("ix_wg_raw_records_namespace", "wg_raw_records", ["namespace"], schema="worldgraph")
    op.create_index("ix_wg_raw_records_source_name", "wg_raw_records", ["source_name"], schema="worldgraph")
    op.create_index("ix_wg_raw_records_source_primary_key", "wg_raw_records", ["source_primary_key"], schema="worldgraph")
    op.create_index("ix_wg_raw_records_payload_hash", "wg_raw_records", ["payload_hash"], schema="worldgraph")

    op.create_table(
        "wg_entities",
        sa.Column("entity_id", sa.String(), nullable=False),
        sa.Column("namespace", sa.String(), nullable=False),
        sa.Column("entity_type", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("canonical_slug", sa.String(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("canonical_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("entity_id"),
        schema="worldgraph",
    )
    op.create_index("ix_wg_entities_namespace", "wg_entities", ["namespace"], schema="worldgraph")
    op.create_index("ix_wg_entities_entity_type", "wg_entities", ["entity_type"], schema="worldgraph")
    op.create_index("ix_wg_entities_display_name", "wg_entities", ["display_name"], schema="worldgraph")

    op.create_table(
        "wg_entity_aliases",
        sa.Column("alias_id", sa.String(), nullable=False),
        sa.Column("entity_id", sa.String(), nullable=False),
        sa.Column("alias", sa.String(), nullable=False),
        sa.Column("language_code", sa.String(), nullable=True),
        sa.Column("alias_type", sa.String(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("alias_id"),
        sa.UniqueConstraint("entity_id", "alias", "alias_type", name="uq_wg_entity_alias"),
        schema="worldgraph",
    )
    op.create_index("ix_wg_entity_aliases_entity_id", "wg_entity_aliases", ["entity_id"], schema="worldgraph")
    op.create_index("ix_wg_entity_aliases_alias", "wg_entity_aliases", ["alias"], schema="worldgraph")

    op.create_table(
        "wg_entity_identifiers",
        sa.Column("identifier_id", sa.String(), nullable=False),
        sa.Column("entity_id", sa.String(), nullable=False),
        sa.Column("namespace", sa.String(), nullable=False),
        sa.Column("scheme", sa.String(), nullable=False),
        sa.Column("value", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("identifier_id"),
        sa.UniqueConstraint("namespace", "scheme", "value", name="uq_wg_identifier_namespace_scheme_value"),
        schema="worldgraph",
    )
    op.create_index("ix_wg_entity_identifiers_entity_id", "wg_entity_identifiers", ["entity_id"], schema="worldgraph")
    op.create_index("ix_wg_entity_identifiers_scheme", "wg_entity_identifiers", ["scheme"], schema="worldgraph")
    op.create_index("ix_wg_entity_identifiers_value", "wg_entity_identifiers", ["value"], schema="worldgraph")

    op.create_table(
        "wg_entity_categories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("entity_id", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("entity_id", "category", name="uq_wg_entity_category"),
        schema="worldgraph",
    )
    op.create_index("ix_wg_entity_categories_entity_id", "wg_entity_categories", ["entity_id"], schema="worldgraph")
    op.create_index("ix_wg_entity_categories_category", "wg_entity_categories", ["category"], schema="worldgraph")

    op.create_table(
        "wg_entity_relationships",
        sa.Column("relationship_id", sa.String(), nullable=False),
        sa.Column("from_entity_id", sa.String(), nullable=False),
        sa.Column("relationship_type", sa.String(), nullable=False),
        sa.Column("to_entity_id", sa.String(), nullable=False),
        sa.Column("relationship_json", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("relationship_id"),
        schema="worldgraph",
    )
    op.create_index(
        "ix_wg_entity_relationships_from_entity_id",
        "wg_entity_relationships",
        ["from_entity_id"],
        schema="worldgraph",
    )
    op.create_index(
        "ix_wg_entity_relationships_to_entity_id",
        "wg_entity_relationships",
        ["to_entity_id"],
        schema="worldgraph",
    )
    op.create_index(
        "ix_wg_entity_relationships_relationship_type",
        "wg_entity_relationships",
        ["relationship_type"],
        schema="worldgraph",
    )

    op.create_table(
        "wg_entity_provenance",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("entity_id", sa.String(), nullable=False),
        sa.Column("raw_record_id", sa.String(), nullable=False),
        sa.Column("proposal_id", sa.String(), nullable=True),
        sa.Column("field_path", sa.String(), nullable=False),
        sa.Column("source_value", sa.Text(), nullable=True),
        sa.Column("accepted_value", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema="worldgraph",
    )
    op.create_index("ix_wg_entity_provenance_entity_id", "wg_entity_provenance", ["entity_id"], schema="worldgraph")
    op.create_index("ix_wg_entity_provenance_raw_record_id", "wg_entity_provenance", ["raw_record_id"], schema="worldgraph")

    op.create_table(
        "wg_entity_proposals",
        sa.Column("proposal_id", sa.String(), nullable=False),
        sa.Column("namespace", sa.String(), nullable=False),
        sa.Column("proposal_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("draft_entity_json", sa.JSON(), nullable=False),
        sa.Column("dedupe_candidates_json", sa.JSON(), nullable=False),
        sa.Column("created_by_job_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_by", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("proposal_id"),
        schema="worldgraph",
    )
    op.create_index("ix_wg_entity_proposals_namespace", "wg_entity_proposals", ["namespace"], schema="worldgraph")
    op.create_index("ix_wg_entity_proposals_status", "wg_entity_proposals", ["status"], schema="worldgraph")
    op.create_index(
        "ix_wg_entity_proposals_created_by_job_id",
        "wg_entity_proposals",
        ["created_by_job_id"],
        schema="worldgraph",
    )

    op.create_table(
        "wg_proposal_sources",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("proposal_id", sa.String(), nullable=False),
        sa.Column("raw_record_id", sa.String(), nullable=False),
        sa.Column("excerpt_json", sa.JSON(), nullable=False),
        sa.Column("source_weight", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema="worldgraph",
    )
    op.create_index("ix_wg_proposal_sources_proposal_id", "wg_proposal_sources", ["proposal_id"], schema="worldgraph")
    op.create_index("ix_wg_proposal_sources_raw_record_id", "wg_proposal_sources", ["raw_record_id"], schema="worldgraph")

    op.create_table(
        "wg_search_documents",
        sa.Column("entity_id", sa.String(), nullable=False),
        sa.Column("search_text", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("entity_id"),
        schema="worldgraph",
    )

    op.create_table(
        "wg_entity_embeddings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("entity_id", sa.String(), nullable=False),
        sa.Column("embedding_model", sa.String(), nullable=False),
        sa.Column("embedding_version", sa.String(), nullable=False),
        sa.Column("embedding_json", sa.JSON(), nullable=False),
        sa.Column("content_hash", sa.String(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("entity_id", "embedding_model", "embedding_version", name="uq_wg_entity_embedding_version"),
        schema="worldgraph",
    )
    op.create_index("ix_wg_entity_embeddings_entity_id", "wg_entity_embeddings", ["entity_id"], schema="worldgraph")
    op.create_index("ix_wg_entity_embeddings_embedding_model", "wg_entity_embeddings", ["embedding_model"], schema="worldgraph")
    op.create_index("ix_wg_entity_embeddings_embedding_version", "wg_entity_embeddings", ["embedding_version"], schema="worldgraph")

    op.create_table(
        "wg_travel_raw_airports",
        sa.Column("raw_record_id", sa.String(), nullable=False),
        sa.Column("airport_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("country", sa.String(), nullable=True),
        sa.Column("iata", sa.String(), nullable=True),
        sa.Column("icao", sa.String(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("ingested_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("raw_record_id"),
        schema="worldgraph",
    )
    op.create_index("ix_wg_travel_raw_airports_airport_id", "wg_travel_raw_airports", ["airport_id"], schema="worldgraph")
    op.create_index("ix_wg_travel_raw_airports_iata", "wg_travel_raw_airports", ["iata"], schema="worldgraph")
    op.create_index("ix_wg_travel_raw_airports_icao", "wg_travel_raw_airports", ["icao"], schema="worldgraph")

    op.create_table(
        "wg_travel_raw_airlines",
        sa.Column("raw_record_id", sa.String(), nullable=False),
        sa.Column("airline_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("alias", sa.String(), nullable=True),
        sa.Column("iata", sa.String(), nullable=True),
        sa.Column("icao", sa.String(), nullable=True),
        sa.Column("callsign", sa.String(), nullable=True),
        sa.Column("country", sa.String(), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("ingested_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("raw_record_id"),
        schema="worldgraph",
    )
    op.create_index("ix_wg_travel_raw_airlines_airline_id", "wg_travel_raw_airlines", ["airline_id"], schema="worldgraph")
    op.create_index("ix_wg_travel_raw_airlines_iata", "wg_travel_raw_airlines", ["iata"], schema="worldgraph")
    op.create_index("ix_wg_travel_raw_airlines_icao", "wg_travel_raw_airlines", ["icao"], schema="worldgraph")

    op.create_table(
        "wg_travel_raw_routes",
        sa.Column("raw_record_id", sa.String(), nullable=False),
        sa.Column("route_key", sa.String(), nullable=False),
        sa.Column("airline_code", sa.String(), nullable=True),
        sa.Column("source_airport", sa.String(), nullable=True),
        sa.Column("destination_airport", sa.String(), nullable=True),
        sa.Column("stops", sa.Integer(), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("ingested_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("raw_record_id"),
        schema="worldgraph",
    )
    op.create_index("ix_wg_travel_raw_routes_route_key", "wg_travel_raw_routes", ["route_key"], schema="worldgraph")
    op.create_index("ix_wg_travel_raw_routes_airline_code", "wg_travel_raw_routes", ["airline_code"], schema="worldgraph")
    op.create_index(
        "ix_wg_travel_raw_routes_source_airport",
        "wg_travel_raw_routes",
        ["source_airport"],
        schema="worldgraph",
    )
    op.create_index(
        "ix_wg_travel_raw_routes_destination_airport",
        "wg_travel_raw_routes",
        ["destination_airport"],
        schema="worldgraph",
    )


def downgrade() -> None:
    op.drop_table("wg_travel_raw_routes", schema="worldgraph")
    op.drop_table("wg_travel_raw_airlines", schema="worldgraph")
    op.drop_table("wg_travel_raw_airports", schema="worldgraph")
    op.drop_table("wg_entity_embeddings", schema="worldgraph")
    op.drop_table("wg_search_documents", schema="worldgraph")
    op.drop_table("wg_proposal_sources", schema="worldgraph")
    op.drop_table("wg_entity_proposals", schema="worldgraph")
    op.drop_table("wg_entity_provenance", schema="worldgraph")
    op.drop_table("wg_entity_relationships", schema="worldgraph")
    op.drop_table("wg_entity_categories", schema="worldgraph")
    op.drop_table("wg_entity_identifiers", schema="worldgraph")
    op.drop_table("wg_entity_aliases", schema="worldgraph")
    op.drop_table("wg_entities", schema="worldgraph")
    op.drop_table("wg_raw_records", schema="worldgraph")
    op.drop_table("wg_raw_objects", schema="worldgraph")
    op.drop_table("wg_ingest_jobs", schema="worldgraph")
    op.execute("DROP SCHEMA IF EXISTS worldgraph CASCADE")
