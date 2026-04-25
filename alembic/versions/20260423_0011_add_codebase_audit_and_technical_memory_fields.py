"""add codebase audit and technical memory fields

Revision ID: 20260423_0011
Revises: 20260423_0010
Create Date: 2026-04-23 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

revision = "20260423_0011"
down_revision = "20260423_0010"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    return inspect(bind).has_table(table_name)


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table(table_name):
        return False
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    if (
        not _has_table("codebase_audits")
        and _has_table("projects")
        and _has_table("workflow_runs")
    ):
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

    if _has_table("memory_notes"):
        if not _has_column("memory_notes", "note_type"):
            op.add_column(
                "memory_notes",
                sa.Column("note_type", sa.String(), nullable=False, server_default="business"),
            )
            op.alter_column("memory_notes", "note_type", server_default=None)
        if not _has_column("memory_notes", "metadata"):
            op.add_column(
                "memory_notes",
                sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
            )
            op.alter_column("memory_notes", "metadata", server_default=None)
        if not _has_column("memory_notes", "created_at"):
            op.add_column(
                "memory_notes",
                sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            )
            op.alter_column("memory_notes", "created_at", server_default=None)
        if not _has_column("memory_notes", "updated_at"):
            op.add_column(
                "memory_notes",
                sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            )
            op.alter_column("memory_notes", "updated_at", server_default=None)


def downgrade() -> None:
    if _has_table("memory_notes"):
        for col in ["updated_at", "created_at", "metadata", "note_type"]:
            if _has_column("memory_notes", col):
                op.drop_column("memory_notes", col)
    if _has_table("codebase_audits"):
        op.drop_table("codebase_audits")
