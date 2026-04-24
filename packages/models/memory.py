"""Memory note ORM model. Assistive context only — not authoritative over domain records."""

from datetime import datetime
from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

from .base import Base


class MemoryNoteRecord(Base):
    __tablename__ = "memory_notes"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # format: mem_<ulid>
    tenant_id: Mapped[str] = mapped_column(String, nullable=False)
    project_id: Mapped[str] = mapped_column(String, nullable=False)
    note_type: Mapped[str] = mapped_column(String, nullable=False, default="business")  # technical | business
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    links: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    note_metadata: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
