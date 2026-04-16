"""Tenant model. All data is tenant-scoped per system contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # format: tenant_<ulid>
    name: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Billing
    plan: Mapped[str] = mapped_column(String, nullable=False, server_default="free")
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, unique=True)
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, unique=True)
