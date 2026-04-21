"""
Alembic migration environment.
Wired to packages.models.Base so autogenerate detects all ORM models.
DATABASE_URL from env overrides alembic.ini to avoid hardcoded credentials.
"""

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Import all models so their tables are registered on Base.metadata
from packages.models import Base
from packages.models import (  # noqa: F401
    Tenant,
    Project,
    ProjectFile,
    IngestionJob,
    BuildingElementRecord,
    DocumentChunkRecord,
    IssueRecord,
    WorkflowRunRecord,
    WorkflowStepRecord,
    DeliverableRecord,
    MemoryNoteRecord,
    UsageEventRecord,
    AutomationLogRecord,
    SidecarPersona,
    SidecarScorecard,
    SidecarFingerprint,
    SidecarParoleVerdict,
    SidecarBloodsVault,
    SidecarBenchmarkCache,
    SidecarAuditLog,
)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use DATABASE_URL env var if set; fall back to alembic.ini value.
# Escape % → %% so ConfigParser doesn't misinterpret URL-encoded chars (e.g. %2B).
database_url = os.environ.get("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Offline mode — emit SQL to stdout without a live DB connection."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Online mode — connect to the database and apply migrations."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
