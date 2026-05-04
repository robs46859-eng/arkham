"""
13-Entity Shared Data Models

SQLAlchemy models for the Unified AI Command Center data model.
Used across all verticals: Studio, E-commerce, SaaS, Staffing, Media.
"""

from sqlalchemy import Column, String, Integer, Float, Boolean, ForeignKey, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP, DATE
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime, date
import uuid

Base = declarative_base()


class Account(Base):
    """Account (Customer/Employer contacts - All businesses)"""
    __tablename__ = 'accounts'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    vertical = Column(String(50), nullable=False)  # studio, ecom, saas, staffing, media
    name = Column(String(255), nullable=False)
    type = Column(String(50))  # client, buyer, subscriber, employer, advertiser
    email = Column(String(255))
    phone = Column(String(50))
    status = Column(String(50), default='active')
    ltv = Column(Float, default=0)
    metadata_ = Column(JSONB, default=dict)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_accounts_tenant', 'tenant_id'),
        Index('idx_accounts_vertical', 'vertical'),
        Index('idx_accounts_type', 'type'),
    )


class Lead(Base):
    """Lead (Source, score, stage - All businesses)"""
    __tablename__ = 'leads'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    account_id = Column(UUID(as_uuid=True), ForeignKey('accounts.id'))
    vertical = Column(String(50), nullable=False)
    source = Column(String(100))
    source_url = Column(Text)
    score = Column(Integer, default=0)
    stage = Column(String(50), default='new')
    intent_signals = Column(JSONB, default=list)
    metadata_ = Column(JSONB, default=dict)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_leads_tenant', 'tenant_id'),
        Index('idx_leads_vertical', 'vertical'),
        Index('idx_leads_stage', 'stage'),
        Index('idx_leads_score', 'score', postgresql_using='btree', postgresql_ops={'score': 'DESC'}),
    )


class Deal(Base):
    """Deal (Pricing, probability, contract link - Studio, Staffing, SaaS)"""
    __tablename__ = 'deals'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    lead_id = Column(UUID(as_uuid=True), ForeignKey('leads.id'))
    vertical = Column(String(50), nullable=False)
    name = Column(String(255))
    value = Column(Float)
    probability = Column(Float, default=0)
    contract_url = Column(Text)
    margin_target = Column(Float, default=0.23)
    metadata_ = Column(JSONB, default=dict)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)


class Order(Base):
    """Order (Cart, SKU, fulfillment status - E-commerce, Media)"""
    __tablename__ = 'orders'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    account_id = Column(UUID(as_uuid=True), ForeignKey('accounts.id'))
    vertical = Column(String(50), nullable=False)
    status = Column(String(50), default='pending')
    total = Column(Float)
    items = Column(JSONB, default=list)
    fulfillment_data = Column(JSONB, default=dict)
    metadata_ = Column(JSONB, default=dict)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)


class Subscription(Base):
    """Subscription (SaaS Access Model - SaaS, Media)"""
    __tablename__ = 'subscriptions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    account_id = Column(UUID(as_uuid=True), ForeignKey('accounts.id'))
    vertical = Column(String(50), nullable=False)
    plan = Column(String(100))
    status = Column(String(50), default='active')
    mrr = Column(Float, default=0)
    start_date = Column(DATE)
    end_date = Column(DATE)
    cancel_reason = Column(Text)
    metadata_ = Column(JSONB, default=dict)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)


class Project(Base):
    """Project (Creative Projects, Implementation - Studio, SaaS)"""
    __tablename__ = 'projects'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    account_id = Column(UUID(as_uuid=True), ForeignKey('accounts.id'))
    vertical = Column(String(50), nullable=False)
    name = Column(String(255))
    status = Column(String(50), default='planning')
    start_date = Column(DATE)
    end_date = Column(DATE)
    budget = Column(Float)
    metadata_ = Column(JSONB, default=dict)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)


class Placement(Base):
    """Placement (Staffing shifts, Media ad placements)"""
    __tablename__ = 'placements'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    account_id = Column(UUID(as_uuid=True), ForeignKey('accounts.id'))
    candidate_id = Column(UUID(as_uuid=True))
    vertical = Column(String(50), nullable=False)
    type = Column(String(50))
    status = Column(String(50), default='pending')
    start_date = Column(TIMESTAMP)
    end_date = Column(TIMESTAMP)
    metadata_ = Column(JSONB, default=dict)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)


class Candidate(Base):
    """Candidate (Talent, Influencers, Trial Users)"""
    __tablename__ = 'candidates'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    vertical = Column(String(50), nullable=False)
    name = Column(String(255))
    email = Column(String(255))
    skills = Column(Text)  # Stored as array
    experience_years = Column(Integer)
    score = Column(Integer, default=0)
    status = Column(String(50), default='active')
    metadata_ = Column(JSONB, default=dict)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)


class ContentAsset(Base):
    """Content Asset (Articles, Videos, Ads, Social - Media, E-commerce, Studio)"""
    __tablename__ = 'content_assets'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    vertical = Column(String(50), nullable=False)
    type = Column(String(50))
    title = Column(String(255))
    topic = Column(String(100))
    keywords = Column(Text)  # Stored as array
    url = Column(Text)
    status = Column(String(50), default='draft')
    performance = Column(JSONB, default=dict)  # {views, clicks, conversions, epc, revenue}
    affiliate_placements = Column(JSONB, default=list)
    metadata_ = Column(JSONB, default=dict)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)


class Task(Base):
    """Task (Work Items - All verticals)"""
    __tablename__ = 'tasks'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    vertical = Column(String(50), nullable=False)
    type = Column(String(50))  # ai_autonomous, human_approval_required, ai_assisted
    status = Column(String(50), default='pending')
    assigned_to = Column(String(100))
    priority = Column(String(20), default='medium')
    due_date = Column(TIMESTAMP)
    metadata_ = Column(JSONB, default=dict)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)


class Event(Base):
    """Event (Analytics Events - All verticals)"""
    __tablename__ = 'events'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    vertical = Column(String(50), nullable=False)
    event_type = Column(String(100))
    account_id = Column(UUID(as_uuid=True))
    lead_id = Column(UUID(as_uuid=True))
    candidate_id = Column(UUID(as_uuid=True))
    content_asset_id = Column(UUID(as_uuid=True))
    event_data = Column(JSONB, default=dict)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)


class Ledger(Base):
    """Ledger (Transactions - All verticals)"""
    __tablename__ = 'ledger'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    vertical = Column(String(50), nullable=False)
    account_id = Column(UUID(as_uuid=True), ForeignKey('accounts.id'))
    amount = Column(Float)
    type = Column(String(50))  # revenue, cost, refund, adjustment
    description = Column(Text)
    reference_id = Column(UUID(as_uuid=True))
    metadata_ = Column(JSONB, default=dict)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)


class Policy(Base):
    """Policy (Guardrails - All verticals)"""
    __tablename__ = 'policies'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'))
    vertical = Column(String(50))
    name = Column(String(255), nullable=False)
    description = Column(Text)
    rules = Column(JSONB, nullable=False)
    enabled = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
