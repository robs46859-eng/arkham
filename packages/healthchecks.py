"""Shared liveness/readiness helpers for services."""

from __future__ import annotations

from sqlalchemy import create_engine, text

import redis


def check_database(database_url: str) -> tuple[bool, str]:
    try:
        engine = create_engine(database_url, future=True, pool_pre_ping=True)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        engine.dispose()
        return True, "ok"
    except Exception as exc:
        return False, str(exc)


def check_redis(redis_url: str) -> tuple[bool, str]:
    try:
        client = redis.Redis.from_url(redis_url, decode_responses=True)
        client.ping()
        return True, "ok"
    except Exception as exc:
        return False, str(exc)
