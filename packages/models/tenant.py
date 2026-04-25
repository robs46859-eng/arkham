"""Tenant model. All data is tenant-scoped per system contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # format: tenant_<ulid>
    name: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Billing and Subscription
    plan: Mapped[str] = mapped_column(String, nullable=False, default="free", server_default="free")
    enable_premium_escalation: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    enable_semantic_cache: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    cache_similarity_threshold: Mapped[float] = mapped_column(Float, default=0.92, server_default="0.92")
    max_requests_per_day: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    entitlements: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, server_default="{}")
    
    # Stripe Integration
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, unique=True, index=True)
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, unique=True, index=True)
    stripe_price_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    subscription_status: Mapped[str] = mapped_column(String, default="inactive", server_default="inactive")
    subscription_current_period_end: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    subscription_cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
