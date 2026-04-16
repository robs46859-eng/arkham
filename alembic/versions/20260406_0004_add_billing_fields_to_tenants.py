"""add billing fields to tenants

Revision ID: 20260406_0004
Revises: 20260405_0003
Create Date: 2026-04-06 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260406_0004"
down_revision = "20260405_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("updated_at", sa.DateTime(), nullable=True))
    op.add_column(
        "tenants",
        sa.Column("plan", sa.String(), nullable=False, server_default="free"),
    )
    op.add_column(
        "tenants",
        sa.Column("stripe_customer_id", sa.String(), nullable=True),
    )
    op.add_column(
        "tenants",
        sa.Column("stripe_subscription_id", sa.String(), nullable=True),
    )
    op.create_index(
        "ix_tenants_stripe_customer_id", "tenants", ["stripe_customer_id"], unique=True
    )
    op.create_index(
        "ix_tenants_stripe_subscription_id", "tenants", ["stripe_subscription_id"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_tenants_stripe_subscription_id", table_name="tenants")
    op.drop_index("ix_tenants_stripe_customer_id", table_name="tenants")
    op.drop_column("tenants", "stripe_subscription_id")
    op.drop_column("tenants", "stripe_customer_id")
    op.drop_column("tenants", "plan")
    op.drop_column("tenants", "updated_at")
