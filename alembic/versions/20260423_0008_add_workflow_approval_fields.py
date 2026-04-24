"""add workflow approval fields

Revision ID: 20260423_0008
Revises: 20260421_0007
Create Date: 2026-04-23 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "20260423_0010"
down_revision = "20260423_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workflow_runs",
        sa.Column(
            "approval_state",
            sa.String(),
            nullable=False,
            server_default="not_required",
        ),
    )
    op.add_column(
        "workflow_runs",
        sa.Column("approval_requested_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "workflow_runs",
        sa.Column("approval_resolved_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "workflow_runs",
        sa.Column("approval_actor_id", sa.String(), nullable=True),
    )
    op.add_column(
        "workflow_runs",
        sa.Column("approval_notes", sa.Text(), nullable=True),
    )
    op.alter_column("workflow_runs", "approval_state", server_default=None)


def downgrade() -> None:
    op.drop_column("workflow_runs", "approval_notes")
    op.drop_column("workflow_runs", "approval_actor_id")
    op.drop_column("workflow_runs", "approval_resolved_at")
    op.drop_column("workflow_runs", "approval_requested_at")
    op.drop_column("workflow_runs", "approval_state")
