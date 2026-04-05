"""Tenant schemas for API contracts."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class TenantCreate(BaseModel):
    """Request schema for creating a tenant."""

    name: str = Field(..., min_length=1, max_length=255)
    is_active: bool = True


class TenantUpdate(BaseModel):
    """Request schema for updating a tenant."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    is_active: Optional[bool] = None


class TenantResponse(BaseModel):
    """Response schema for tenant operations."""

    tenant_id: str
    name: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
