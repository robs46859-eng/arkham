"""add tenant api keys table

Revision ID: 20260405_0003
Revises: 20260404_0002
Create Date: 2026-04-05 11:30:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260405_0003"
down_revision = "20260404_0002"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return inspect(op.get_bind()).has_table(table_name)


def _has_index(table_name: str, index_name: str) -> bool:
    indexes = inspect(op.get_bind()).get_indexes(table_name)
    return any(index["name"] == index_name for index in indexes)


def upgrade() -> None:
    if not _has_table("tenant_api_keys"):
        op.create_table(
            "tenant_api_keys",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("tenant_id", sa.String(), sa.ForeignKey("tenants.id"), nullable=False),
            sa.Column("key_prefix", sa.String(), nullable=False),
            sa.Column("secret_hash", sa.String(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("last_used_at", sa.DateTime(), nullable=True),
        )
    if not _has_index("tenant_api_keys", "ix_tenant_api_keys_tenant_id"):
        op.create_index("ix_tenant_api_keys_tenant_id", "tenant_api_keys", ["tenant_id"])
    if not _has_index("tenant_api_keys", "ix_tenant_api_keys_key_prefix"):
        op.create_index("ix_tenant_api_keys_key_prefix", "tenant_api_keys", ["key_prefix"], unique=True)


def downgrade() -> None:
    if _has_table("tenant_api_keys"):
        if _has_index("tenant_api_keys", "ix_tenant_api_keys_key_prefix"):
            op.drop_index("ix_tenant_api_keys_key_prefix", table_name="tenant_api_keys")
        if _has_index("tenant_api_keys", "ix_tenant_api_keys_tenant_id"):
            op.drop_index("ix_tenant_api_keys_tenant_id", table_name="tenant_api_keys")
        op.drop_table("tenant_api_keys")
