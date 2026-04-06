"""
Shared Vertical SDK
Every vertical imports this to get automatic registration with Core,
event subscription, event publishing, and a receive endpoint.

Usage:
    from packages.vertical_base import VerticalBase

    vertical = VerticalBase(
        service_id="omniscale",
        service_type="vertical",
        port=3040,
        capabilities=["dashboard", "metrics"],
        event_subscriptions=["service.registered", "workflow.completed"],
    )
    app = vertical.app

    # Define your routes on app as usual
    @app.get("/my-endpoint")
    async def my_endpoint():
        return {"hello": "world"}

    # Publish events from anywhere
    await vertical.publish_event("metric.updated", {"metric": "cpu", "value": 42})
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Callable

import httpx
from fastapi import FastAPI, Request
from pydantic import BaseModel

logger = logging.getLogger("vertical_base")


class EventPayload(BaseModel):
    """Inbound event delivered by Core's event bus."""
    event_type: str
    source_service: str
    payload: dict[str, Any]
    timestamp: str | None = None


class VerticalBase:
    """
    Base harness for a hub-and-spoke vertical.

    On startup:
      1. Registers with Core's service registry
      2. Subscribes to requested event types (with callback URL)

    On shutdown:
      1. Unsubscribes from events
      2. Unregisters from Core

    Provides:
      - self.app: the FastAPI instance (use for adding routes)
      - self.publish_event(): fire an event through Core's bus
      - POST /events/receive: auto-mounted handler for inbound events
    """

    def __init__(
        self,
        *,
        service_id: str,
        service_type: str = "vertical",
        title: str | None = None,
        version: str = "0.1.0",
        port: int = 8000,
        capabilities: list[str] | None = None,
        event_subscriptions: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.service_id = service_id
        self.service_type = service_type
        self.version = version
        self.port = port
        self.capabilities = capabilities or []
        self.event_subscriptions = event_subscriptions or []
        self.metadata = metadata or {}

        self._core_url = os.environ.get("CORE_SERVICE_URL", "http://core:8000")
        self._event_handlers: dict[str, list[Callable]] = {}

        self.app = FastAPI(
            title=title or service_id.replace("_", " ").title(),
            version=version,
            lifespan=self._lifespan,
        )

        # Mount built-in routes
        self._mount_builtins()

    # ── Lifecycle ────────────────────────────────────────────────────────────

    @asynccontextmanager
    async def _lifespan(self, app: FastAPI):
        """Register with Core on startup, clean up on shutdown."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            self._client = client
            await self._register()
            if self.event_subscriptions:
                await self._subscribe()
            yield
            await self._unsubscribe()
            await self._unregister()

    async def _register(self) -> None:
        """Register this service in Core's service registry."""
        payload = {
            "service_id": self.service_id,
            "service_type": self.service_type,
            "endpoint": f"http://{self.service_id}:{self.port}",
            "port": self.port,
            "version": self.version,
            "capabilities": self.capabilities,
            "metadata": self.metadata,
        }
        try:
            resp = await self._client.post(
                f"{self._core_url}/registry/register", json=payload
            )
            resp.raise_for_status()
            logger.info("Registered with Core: %s", self.service_id)
        except Exception:
            logger.warning(
                "Failed to register with Core (service will still start): %s",
                self.service_id,
                exc_info=True,
            )

    async def _unregister(self) -> None:
        try:
            resp = await self._client.delete(
                f"{self._core_url}/registry/services/{self.service_id}"
            )
            resp.raise_for_status()
            logger.info("Unregistered from Core: %s", self.service_id)
        except Exception:
            logger.warning("Failed to unregister from Core", exc_info=True)

    async def _subscribe(self) -> None:
        """Subscribe to event types with a callback URL."""
        callback_url = f"http://{self.service_id}:{self.port}/events/receive"
        payload = {
            "service_id": self.service_id,
            "event_types": self.event_subscriptions,
            "callback_url": callback_url,
        }
        try:
            resp = await self._client.post(
                f"{self._core_url}/events/subscribe", json=payload
            )
            resp.raise_for_status()
            logger.info(
                "Subscribed to events %s: %s",
                self.event_subscriptions,
                self.service_id,
            )
        except Exception:
            logger.warning("Failed to subscribe to events", exc_info=True)

    async def _unsubscribe(self) -> None:
        try:
            resp = await self._client.delete(
                f"{self._core_url}/events/unsubscribe/{self.service_id}"
            )
            resp.raise_for_status()
            logger.info("Unsubscribed from events: %s", self.service_id)
        except Exception:
            logger.warning("Failed to unsubscribe from events", exc_info=True)

    # ── Event Publishing ─────────────────────────────────────────────────────

    async def publish_event(
        self, event_type: str, payload: dict[str, Any]
    ) -> dict | None:
        """Publish an event through Core's event bus."""
        event = {
            "event_type": event_type,
            "source_service": self.service_id,
            "payload": payload,
        }
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    f"{self._core_url}/events/publish", json=event
                )
                resp.raise_for_status()
                return resp.json()
        except Exception:
            logger.warning("Failed to publish event %s", event_type, exc_info=True)
            return None

    # ── Event Handling ───────────────────────────────────────────────────────

    def on_event(self, event_type: str):
        """
        Decorator to register an event handler.

        @vertical.on_event("workflow.completed")
        async def handle_workflow(event: EventPayload):
            print(event.payload)
        """
        def decorator(func: Callable):
            self._event_handlers.setdefault(event_type, []).append(func)
            return func
        return decorator

    async def _dispatch_event(self, event: EventPayload) -> None:
        """Route an inbound event to registered handlers."""
        handlers = self._event_handlers.get(event.event_type, [])
        wildcard = self._event_handlers.get("*", [])
        for handler in handlers + wildcard:
            try:
                await handler(event)
            except Exception:
                logger.error(
                    "Event handler error for %s", event.event_type, exc_info=True
                )

    # ── Built-in Routes ──────────────────────────────────────────────────────

    def _mount_builtins(self) -> None:
        """Mount health check and event receive endpoints."""

        @self.app.get("/health")
        async def health_check():
            return {"status": "ok", "service": self.service_id}

        @self.app.post("/events/receive")
        async def receive_event(event: EventPayload):
            await self._dispatch_event(event)
            return {"status": "received", "event_type": event.event_type}
