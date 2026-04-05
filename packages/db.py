"""
Database session management — shared across all services.
Provides get_db dependency for FastAPI services.
Implements: Build Rules §3 — No service defines its own DB connection logic.
"""

from __future__ import annotations

import os
from typing import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from packages.models.base import Base


def get_database_url() -> str:
    """Get database URL from environment with test fallback."""
    app_env = os.getenv("APP_ENV", "development")

    if app_env == "test":
        return os.getenv("DATABASE_URL", "sqlite:///:memory:")

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError(
            "DATABASE_URL environment variable is required. "
            "Set it to a valid database connection string (e.g., postgresql://user:pass@host:5432/dbname). "
            "For testing, set APP_ENV=test."
        )
    return db_url


# Engine and SessionLocal are created lazily on first use
_engine = None
_SessionLocal = None


def get_engine():
    """Get or create the SQLAlchemy engine."""
    global _engine
    if _engine is None:
        db_url = get_database_url()
        if db_url.startswith("sqlite"):
            _engine = create_engine(
                db_url,
                connect_args={"check_same_thread": False},
            )
        else:
            _engine = create_engine(db_url)
    return _engine


def get_session_local():
    """Get or create the SessionLocal factory."""
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionLocal


def init_db() -> None:
    """Initialize database tables. Use with caution in production."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a database session.

    Usage in routers:
        @router.get("/items")
        def list_items(db: Session = Depends(get_db)):
            ...
    """
    db = get_session_local()()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def transactional_session():
    """
    Context manager for transactional database operations.

    Usage:
        with transactional_session() as db:
            db.add(obj)
            db.commit()
    """
    db = get_session_local()()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
