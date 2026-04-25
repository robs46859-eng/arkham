"""add workflow approval fields

Revision ID: 20260423_0008
Revises: 20260421_0007
Create Date: 2026-04-23 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20260423_0010"
down_revision = "20260423_0009"
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
    if not _has_table("workflow_runs"):
        return

    if not _has_column("workflow_runs", "approval_state"):
        op.add_column(
            "workflow_runs",
            sa.Column(
                "approval_state",
                sa.String(),
                nullable=False,
                server_default="not_required",
            ),
        )
        op.alter_column("workflow_runs", "approval_state", server_default=None)
    if not _has_column("workflow_runs", "approval_requested_at"):
        op.add_column(
            "workflow_runs",
            sa.Column("approval_requested_at", sa.DateTime(), nullable=True),
        )
    if not _has_column("workflow_runs", "approval_resolved_at"):
        op.add_column(
            "workflow_runs",
            sa.Column("approval_resolved_at", sa.DateTime(), nullable=True),
        )
    if not _has_column("workflow_runs", "approval_actor_id"):
        op.add_column(
            "workflow_runs",
            sa.Column("approval_actor_id", sa.String(), nullable=True),
        )
    if not _has_column("workflow_runs", "approval_notes"):
        op.add_column(
            "workflow_runs",
            sa.Column("approval_notes", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    if not _has_table("workflow_runs"):
        return
    for column_name in [
        "approval_notes",
        "approval_actor_id",
        "approval_resolved_at",
        "approval_requested_at",
        "approval_state",
    ]:
        if _has_column("workflow_runs", column_name):
            op.drop_column("workflow_runs", column_name)
