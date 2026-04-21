"""drop FK from sidecar_fingerprints.persona_id

Revision ID: 20260421_0007
Revises: 20260421_0006
Create Date: 2026-04-21 00:00:00.000000
"""

from alembic import op

revision = "20260421_0007"
down_revision = "20260421_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "sidecar_fingerprints_persona_id_fkey",
        "sidecar_fingerprints",
        type_="foreignkey",
    )


def downgrade() -> None:
    op.create_foreign_key(
        "sidecar_fingerprints_persona_id_fkey",
        "sidecar_fingerprints",
        "sidecar_personas",
        ["persona_id"],
        ["id"],
    )
