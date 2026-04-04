"""Memory note ORM model. Assistive context only — not authoritative over domain records."""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

from .base import Base


class MemoryNoteRecord(Base):
    __tablename__ = "memory_notes"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # format: mem_<ulid>
    tenant_id: Mapped[str] = mapped_column(String, nullable=False)
    project_id: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    links: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
