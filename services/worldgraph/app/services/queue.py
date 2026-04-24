"""Redis queue helpers for worldgraph worker jobs."""

from __future__ import annotations

import json
from typing import Any

import redis

from ..settings import settings


def _redis() -> redis.Redis:
    return redis.Redis.from_url(settings.redis_url, decode_responses=True)


def enqueue_job(job_type: str, payload: dict[str, Any]) -> None:
    envelope = {"job_type": job_type, "payload": payload}
    _redis().rpush(settings.redis_queue_key, json.dumps(envelope))


def pop_job(timeout_seconds: int = 3) -> dict[str, Any] | None:
    item = _redis().blpop(settings.redis_queue_key, timeout=timeout_seconds)
    if item is None:
        return None
    _, raw = item
    return json.loads(raw)

