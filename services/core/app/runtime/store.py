"""Redis-backed durable control-plane state for core service."""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from datetime import datetime
from typing import Any

import redis

from ..settings import settings

_TEST_STATE: dict[str, Any] = {
    "registry": {},
    "config": {
        "core": {
            "enabled_verticals": [],
            "max_concurrent_workflows": 10,
            "default_privacy_tier": "dev",
        },
        "verticals": {},
    },
    "events": [],
    "subscriptions": {},
}


def _is_test_env() -> bool:
    return os.environ.get("APP_ENV", "").lower() == "test"


def _redis() -> redis.Redis:
    return redis.Redis.from_url(settings.redis_url, decode_responses=True)


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Unsupported JSON value: {type(value)!r}")


def _json_loads(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    return json.loads(value)


def list_registry() -> list[dict[str, Any]]:
    if _is_test_env():
        return list(_TEST_STATE["registry"].values())
    client = _redis()
    return [json.loads(value) for value in client.hvals("core:registry")]


def get_registry(service_id: str) -> dict[str, Any] | None:
    if _is_test_env():
        return _TEST_STATE["registry"].get(service_id)
    client = _redis()
    return _json_loads(client.hget("core:registry", service_id), None)


def put_registry(service_id: str, payload: dict[str, Any]) -> None:
    if _is_test_env():
        _TEST_STATE["registry"][service_id] = payload
        return
    client = _redis()
    client.hset("core:registry", service_id, json.dumps(payload, default=_json_default))


def delete_registry(service_id: str) -> bool:
    if _is_test_env():
        return _TEST_STATE["registry"].pop(service_id, None) is not None
    client = _redis()
    return bool(client.hdel("core:registry", service_id))


def list_subscriptions() -> dict[str, list[str]]:
    if _is_test_env():
        return dict(_TEST_STATE["subscriptions"])
    client = _redis()
    return {
        key: json.loads(value)
        for key, value in client.hgetall("core:subscriptions").items()
    }


def put_subscription(
    service_id: str, event_types: list[str], *, callback_url: str | None = None
) -> None:
    sub_data = {"event_types": event_types, "callback_url": callback_url}
    if _is_test_env():
        _TEST_STATE["subscriptions"][service_id] = sub_data
        return
    client = _redis()
    client.hset("core:subscriptions", service_id, json.dumps(sub_data))


def delete_subscription(service_id: str) -> bool:
    if _is_test_env():
        return _TEST_STATE["subscriptions"].pop(service_id, None) is not None
    client = _redis()
    return bool(client.hdel("core:subscriptions", service_id))


def append_event(event: dict[str, Any]) -> int:
    if _is_test_env():
        _TEST_STATE["events"].append(event)
        return len(_TEST_STATE["events"]) - 1
    client = _redis()
    payload = json.dumps(event, default=_json_default)
    return client.rpush("core:events", payload) - 1


def list_events() -> list[dict[str, Any]]:
    if _is_test_env():
        return list(_TEST_STATE["events"])
    client = _redis()
    return [json.loads(item) for item in client.lrange("core:events", 0, -1)]


def get_config_store() -> dict[str, Any]:
    if _is_test_env():
        return _TEST_STATE["config"]
    client = _redis()
    return _json_loads(client.get("core:config"), _TEST_STATE["config"])


def save_config_store(payload: dict[str, Any]) -> None:
    if _is_test_env():
        _TEST_STATE["config"] = payload
        return
    client = _redis()
    client.set("core:config", json.dumps(payload, default=_json_default))


def notified_subscribers(event_type: str, subscriptions: dict[str, Any]) -> list[str]:
    matched: list[str] = []
    for service_id, sub_data in subscriptions.items():
        # Support both new dict shape and legacy list shape
        if isinstance(sub_data, dict):
            event_types = sub_data.get("event_types", [])
        else:
            event_types = sub_data
        if event_type in event_types or "*" in event_types:
            matched.append(service_id)
    return matched


def filter_events(
    events: Iterable[dict[str, Any]],
    *,
    event_type: str | None = None,
    source_service: str | None = None,
) -> list[dict[str, Any]]:
    filtered = list(events)
    if event_type:
        filtered = [event for event in filtered if event.get("event_type") == event_type]
    if source_service:
        filtered = [event for event in filtered if event.get("source_service") == source_service]
    return filtered
