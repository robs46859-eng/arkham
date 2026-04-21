"""sidecar governance tables

Revision ID: 20260421_0006
Revises: 20260407_0005
Create Date: 2026-04-21 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260421_0006"
down_revision = "20260407_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sidecar_personas",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("display_name", sa.String()),
        sa.Column("owner_tenant", sa.String()),
        sa.Column("state", sa.String(), nullable=False, server_default="intake"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_sidecar_personas_tenant_id", "sidecar_personas", ["tenant_id"])
    op.create_index("ix_sidecar_personas_owner_tenant", "sidecar_personas", ["owner_tenant"])

    op.create_table(
        "sidecar_scorecards",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("persona_id", sa.String(), sa.ForeignKey("sidecar_personas.id"), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("request_id", sa.String()),
        sa.Column("checkpoint", sa.String(), nullable=False),
        sa.Column("battery", sa.String(), nullable=False),
        sa.Column("scores", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("passed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_sidecar_scorecards_persona_id", "sidecar_scorecards", ["persona_id"])
    op.create_index("ix_sidecar_scorecards_request_id", "sidecar_scorecards", ["request_id"])
    op.create_index("ix_sidecar_scorecards_tenant_id", "sidecar_scorecards", ["tenant_id"])

    op.create_table(
        "sidecar_fingerprints",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("persona_id", sa.String(), sa.ForeignKey("sidecar_personas.id"), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("checkpoint", sa.String(), nullable=False),
        sa.Column("vector", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("fp_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_sidecar_fingerprints_persona_id", "sidecar_fingerprints", ["persona_id"])
    op.create_index("ix_sidecar_fingerprints_tenant_id", "sidecar_fingerprints", ["tenant_id"])

    op.create_table(
        "sidecar_parole_verdicts",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("persona_id", sa.String(), sa.ForeignKey("sidecar_personas.id"), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("request_id", sa.String()),
        sa.Column("checkpoint", sa.String(), nullable=False),
        sa.Column("verdict", sa.String(), nullable=False),
        sa.Column("battery_scores", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("drift_score", sa.Float()),
        sa.Column("yard_match_score", sa.Float()),
        sa.Column("yard_match_id", sa.String()),
        sa.Column("reasoning", sa.Text()),
        sa.Column("shadow_mode", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_sidecar_parole_verdicts_persona_id", "sidecar_parole_verdicts", ["persona_id"])
    op.create_index("ix_sidecar_parole_verdicts_request_id", "sidecar_parole_verdicts", ["request_id"])
    op.create_index("ix_sidecar_parole_verdicts_tenant_id", "sidecar_parole_verdicts", ["tenant_id"])

    op.create_table(
        "sidecar_bloods_vault",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("persona_id", sa.String(), sa.ForeignKey("sidecar_personas.id"), nullable=False),
        sa.Column("owner_tenant", sa.String(), nullable=False),
        sa.Column("transcript_encrypted", sa.LargeBinary()),
        sa.Column("probe_type", sa.String()),
        sa.Column("result", sa.String()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_sidecar_bloods_vault_persona_id", "sidecar_bloods_vault", ["persona_id"])
    op.create_index("ix_sidecar_bloods_vault_owner_tenant", "sidecar_bloods_vault", ["owner_tenant"])

    op.create_table(
        "sidecar_benchmark_cache",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("battery", sa.String(), nullable=False, unique=True),
        sa.Column("baseline", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("version", sa.String()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_sidecar_benchmark_cache_battery", "sidecar_benchmark_cache", ["battery"])

    op.create_table(
        "sidecar_audit_log",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("request_id", sa.String()),
        sa.Column("persona_id", sa.String()),
        sa.Column("tenant_id", sa.String()),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("old_state", sa.String()),
        sa.Column("new_state", sa.String()),
        sa.Column(
            "audit_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_sidecar_audit_log_request_id", "sidecar_audit_log", ["request_id"])
    op.create_index("ix_sidecar_audit_log_persona_id", "sidecar_audit_log", ["persona_id"])
    op.create_index("ix_sidecar_audit_log_tenant_id", "sidecar_audit_log", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("sidecar_audit_log")
    op.drop_table("sidecar_benchmark_cache")
    op.drop_table("sidecar_bloods_vault")
    op.drop_table("sidecar_parole_verdicts")
    op.drop_table("sidecar_fingerprints")
    op.drop_table("sidecar_scorecards")
    op.drop_table("sidecar_personas")
