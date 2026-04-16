"""add automation log

Revision ID: 20260407_0005
Revises: 20260406_0004
Create Date: 2026-04-07 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260407_0005"
down_revision = "20260406_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "automation_log",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_automation_log_tenant_id", "automation_log", ["tenant_id"])
    op.create_index("ix_automation_log_created_at", "automation_log", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_automation_log_created_at", table_name="automation_log")
    op.drop_index("ix_automation_log_tenant_id", table_name="automation_log")
    op.drop_table("automation_log")
