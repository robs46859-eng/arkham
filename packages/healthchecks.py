"""Shared liveness/readiness helpers for services."""

from __future__ import annotations

from sqlalchemy import create_engine, text

import redis

DEFAULT_HEALTHCHECK_TIMEOUT_SECONDS = 2


def _database_connect_args(database_url: str, timeout_seconds: int) -> dict[str, int]:
    if database_url.startswith(("postgresql://", "postgresql+psycopg2://")):
        return {"connect_timeout": timeout_seconds}
    return {}


def check_database(
    database_url: str,
    timeout_seconds: int = DEFAULT_HEALTHCHECK_TIMEOUT_SECONDS,
) -> tuple[bool, str]:
    engine = None
    try:
        engine = create_engine(
            database_url,
            connect_args=_database_connect_args(database_url, timeout_seconds),
            future=True,
            pool_pre_ping=True,
            pool_timeout=timeout_seconds,
        )
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True, "ok"
    except Exception as exc:
        return False, str(exc)
    finally:
        if engine is not None:
            engine.dispose()


def check_redis(
    redis_url: str,
    timeout_seconds: int = DEFAULT_HEALTHCHECK_TIMEOUT_SECONDS,
) -> tuple[bool, str]:
    try:
        client = redis.Redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=timeout_seconds,
            socket_timeout=timeout_seconds,
        )
        client.ping()
        return True, "ok"
    except Exception as exc:
        return False, str(exc)
