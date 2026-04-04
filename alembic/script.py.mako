/* Alembic script template */
{{""}}
{% if rev_id %}
Revision ID: {{ rev_id }}
Revises: {{ down_revision or "None" }}
Create Date: {{ create_date }}
{% endif %}
{% if upgrade %}
def upgrade():
    """Add upgrade migrations here."""
    pass
{% endif %}
{% if downgrade %}
def downgrade():
    """Add downgrade migrations here."""
    pass
{% endif %}
