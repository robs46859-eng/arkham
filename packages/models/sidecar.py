"""SQLAlchemy ORM models for Arkham AI governance sidecar tables."""
from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class SidecarPersona(Base):
    __tablename__ = "sidecar_personas"

    id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(sa.String, nullable=False, index=True)
    display_name: Mapped[str | None] = mapped_column(sa.String)
    owner_tenant: Mapped[str | None] = mapped_column(sa.String, index=True)
    # intake → probation → active → escaped | released
    state: Mapped[str] = mapped_column(sa.String, default="intake")
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.utcnow)


class SidecarScorecard(Base):
    __tablename__ = "sidecar_scorecards"

    id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    persona_id: Mapped[str] = mapped_column(
        sa.String, sa.ForeignKey("sidecar_personas.id"), nullable=False, index=True
    )
    tenant_id: Mapped[str] = mapped_column(sa.String, nullable=False, index=True)
    request_id: Mapped[str | None] = mapped_column(sa.String, index=True)
    checkpoint: Mapped[str] = mapped_column(sa.String, nullable=False)
    battery: Mapped[str] = mapped_column(sa.String, nullable=False)
    scores: Mapped[dict] = mapped_column(JSONB, default=dict)
    total_tokens: Mapped[int] = mapped_column(sa.Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(sa.Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(sa.Float, default=0.0)
    passed: Mapped[bool] = mapped_column(sa.Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.utcnow)


class SidecarFingerprint(Base):
    __tablename__ = "sidecar_fingerprints"

    id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    persona_id: Mapped[str] = mapped_column(sa.String, nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(sa.String, nullable=False, index=True)
    # intake | probation | exit | yard  (yard = escaped prisoner)
    checkpoint: Mapped[str] = mapped_column(sa.String, nullable=False)
    vector: Mapped[list] = mapped_column(JSONB, nullable=False)
    fp_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.utcnow)


class SidecarParoleVerdict(Base):
    __tablename__ = "sidecar_parole_verdicts"

    id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    persona_id: Mapped[str] = mapped_column(
        sa.String, sa.ForeignKey("sidecar_personas.id"), nullable=False, index=True
    )
    tenant_id: Mapped[str] = mapped_column(sa.String, nullable=False, index=True)
    request_id: Mapped[str | None] = mapped_column(sa.String, index=True)
    checkpoint: Mapped[str] = mapped_column(sa.String, nullable=False)
    verdict: Mapped[str] = mapped_column(sa.String, nullable=False)  # approve | reject | hold
    battery_scores: Mapped[dict] = mapped_column(JSONB, default=dict)
    drift_score: Mapped[float | None] = mapped_column(sa.Float)
    yard_match_score: Mapped[float | None] = mapped_column(sa.Float)
    yard_match_id: Mapped[str | None] = mapped_column(sa.String)
    reasoning: Mapped[str | None] = mapped_column(sa.Text)
    # shadow_mode=True: logged but not enforced (default until explicitly disabled)
    shadow_mode: Mapped[bool] = mapped_column(sa.Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.utcnow)


class SidecarBloodsVault(Base):
    __tablename__ = "sidecar_bloods_vault"

    id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    persona_id: Mapped[str] = mapped_column(
        sa.String, sa.ForeignKey("sidecar_personas.id"), nullable=False, index=True
    )
    owner_tenant: Mapped[str] = mapped_column(sa.String, nullable=False, index=True)
    transcript_encrypted: Mapped[bytes | None] = mapped_column(sa.LargeBinary)
    probe_type: Mapped[str | None] = mapped_column(sa.String)
    result: Mapped[str | None] = mapped_column(sa.String)  # pass | fail | inconclusive
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.utcnow)


class SidecarBenchmarkCache(Base):
    __tablename__ = "sidecar_benchmark_cache"

    id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    battery: Mapped[str] = mapped_column(sa.String, nullable=False, unique=True)
    baseline: Mapped[dict] = mapped_column(JSONB, nullable=False)
    version: Mapped[str | None] = mapped_column(sa.String)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.utcnow)


class SidecarAuditLog(Base):
    # Append-only — never UPDATE or DELETE rows from this table
    __tablename__ = "sidecar_audit_log"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    request_id: Mapped[str | None] = mapped_column(sa.String, index=True)
    persona_id: Mapped[str | None] = mapped_column(sa.String, index=True)
    tenant_id: Mapped[str | None] = mapped_column(sa.String, index=True)
    action: Mapped[str] = mapped_column(sa.String, nullable=False)
    old_state: Mapped[str | None] = mapped_column(sa.String)
    new_state: Mapped[str | None] = mapped_column(sa.String)
    audit_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.utcnow)
