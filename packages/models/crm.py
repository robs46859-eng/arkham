"""Tenant-scoped CRM models shared across all services."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class CompanyRecord(Base):
    __tablename__ = "crm_companies"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    website: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    notes: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class ContactRecord(Base):
    __tablename__ = "crm_contacts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    company_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("crm_companies.id"), nullable=True, index=True)
    first_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    title: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    linkedin_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="lead")
    notes: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class LeadRecord(Base):
    __tablename__ = "crm_leads"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    company_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("crm_companies.id"), nullable=True, index=True)
    contact_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("crm_contacts.id"), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String, nullable=False, default="manual")
    status: Mapped[str] = mapped_column(String, nullable=False, default="new")
    fit_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    record_metadata: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class DealRecord(Base):
    __tablename__ = "crm_deals"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    company_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("crm_companies.id"), nullable=True, index=True)
    contact_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("crm_contacts.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    stage: Mapped[str] = mapped_column(String, nullable=False, default="new")
    status: Mapped[str] = mapped_column(String, nullable=False, default="open")
    amount_cents: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    currency: Mapped[str] = mapped_column(String, nullable=False, default="USD")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class CRMActivityRecord(Base):
    __tablename__ = "crm_activities"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    lead_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("crm_leads.id"), nullable=True, index=True)
    deal_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("crm_deals.id"), nullable=True, index=True)
    contact_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("crm_contacts.id"), nullable=True, index=True)
    activity_type: Mapped[str] = mapped_column(String, nullable=False)
    subject: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    record_metadata: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class WorkflowMemoryDecisionRecord(Base):
    __tablename__ = "workflow_memory_decisions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    request_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    workflow_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    offer_type: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    offer_version: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    stage: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    audience: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    prompt_key: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    prompt_schema_version: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    workflow_memory_schema_version: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    task_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    cache_attempted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    recalled_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    reuse_threshold: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    decision: Mapped[str] = mapped_column(String, nullable=False, index=True)
    fallback_reason: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    stored: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    estimated_time_saved_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    decision_metadata: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)


class WorkflowReviewQueueRecord(Base):
    __tablename__ = "workflow_review_queue"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    batch_label: Mapped[str] = mapped_column(String, nullable=False, index=True)
    source_artifact: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    case_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    lead_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    company_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    contact_email: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    eligibility_status: Mapped[str] = mapped_column(String, nullable=False, default="sendable", index=True)
    system_decision: Mapped[str] = mapped_column(String, nullable=False, index=True)
    system_reason: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    review_status: Mapped[str] = mapped_column(String, nullable=False, default="pending", index=True)
    reviewer_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    reviewer_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    review_metadata: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)


class WorkflowExecutionRecord(Base):
    __tablename__ = "workflow_executions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    review_item_id: Mapped[str] = mapped_column(String, ForeignKey("workflow_review_queue.id"), nullable=False, index=True)
    request_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    batch_label: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    workflow_type: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    offer_type: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    stage: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    execution_status: Mapped[str] = mapped_column(String, nullable=False, default="queued", index=True)
    execution_metadata: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)


class WorkflowExecutionDeliveryRecord(Base):
    __tablename__ = "workflow_execution_deliveries"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    execution_id: Mapped[str] = mapped_column(String, ForeignKey("workflow_executions.id"), nullable=False, index=True)
    review_item_id: Mapped[str] = mapped_column(String, ForeignKey("workflow_review_queue.id"), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String, nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String, nullable=False, index=True)
    delivery_status: Mapped[str] = mapped_column(String, nullable=False, index=True)
    delivery_metadata: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
