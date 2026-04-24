"""add remediation plans table

Revision ID: 20260423_0012
Revises: 20260423_0011
Create Date: 2026-04-23 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260423_0012"
down_revision = "20260423_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "remediation_plans",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("audit_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("workflow_id", sa.String(), nullable=False),
        sa.Column("inventory", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("risk_tiers", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("dependency_chain", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("rollback_notes", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["audit_id"], ["codebase_audits.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflow_runs.id"]),
    )


def downgrade() -> None:
    op.drop_table("remediation_plans")
