"""add codebase audit and technical memory fields

Revision ID: 20260423_0011
Revises: 20260423_0010
Create Date: 2026-04-23 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260423_0011"
down_revision = "20260423_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create codebase_audits table
    op.create_table(
        "codebase_audits",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("workflow_id", sa.String(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("findings", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("proposed_actions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflow_runs.id"]),
    )

    # 2. Update memory_notes table
    op.add_column(
        "memory_notes",
        sa.Column("note_type", sa.String(), nullable=False, server_default="business"),
    )
    op.add_column(
        "memory_notes",
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
    )
    op.add_column(
        "memory_notes",
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.add_column(
        "memory_notes",
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.alter_column("memory_notes", "note_type", server_default=None)
    op.alter_column("memory_notes", "metadata", server_default=None)
    op.alter_column("memory_notes", "created_at", server_default=None)
    op.alter_column("memory_notes", "updated_at", server_default=None)


def downgrade() -> None:
    # 1. Safely drop memory_notes columns
    for col in ["updated_at", "created_at", "metadata", "note_type"]:
        try:
            op.drop_column("memory_notes", col)
        except Exception:
            pass
    # 2. Drop codebase_audits
    op.drop_table("codebase_audits")
