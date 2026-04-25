"""Semantic cache provider backed by LanceDB with cosine similarity."""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Optional

import httpx
from pydantic import BaseModel

try:
    import lancedb
except ModuleNotFoundError:  # pragma: no cover
    lancedb = None

from ..settings import settings

logger = logging.getLogger(__name__)

_SAFE_FILTER_VALUE = re.compile(r"^[\w\-]+$")


class CacheEntry(BaseModel):
    vector: list[float]
    input_text: str
    output: dict[str, Any]
    tenant_id: str
    task_type: str


class SemanticCache:
    """Semantic cache lookup and persistence using cosine similarity."""

    def __init__(self) -> None:
        self._db = None
        self._table = None
        self._table_name = "semantic_cache"

    def _get_db(self):
        if lancedb is None:
            return None
        if self._db is None:
            os.makedirs(settings.vector_store_path, exist_ok=True)
            self._db = lancedb.connect(settings.vector_store_path)
        return self._db

    def _get_table(self):
        if self._table is not None:
            return self._table
        db = self._get_db()
        if db is None:
            return None
        if self._table_name in db.table_names():
            self._table = db.open_table(self._table_name)
        return self._table

    async def _get_embedding(self, text: str) -> list[float]:
        if settings.embedding_provider == "ollama":
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{settings.ollama_host}/api/embeddings",
                    json={"model": settings.embedding_model, "prompt": text},
                )
                resp.raise_for_status()
                return resp.json()["embedding"]

        if settings.embedding_provider == "openai":
            if not settings.openai_api_key:
                raise ValueError("openai_api_key required for openai embeddings")
            base = settings.openai_base_url or "https://api.openai.com/v1"
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{base}/embeddings",
                    headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                    json={"model": settings.embedding_model, "input": text},
                )
                resp.raise_for_status()
                return resp.json()["data"][0]["embedding"]

        raise ValueError(f"Unsupported embedding provider: {settings.embedding_provider}")

    @staticmethod
    def _validate_filter_value(value: str, field: str) -> str:
        if not _SAFE_FILTER_VALUE.match(value):
            raise ValueError(f"Invalid characters in cache filter field '{field}': {value!r}")
        return value

    async def get(
        self,
        tenant_id: str,
        task_type: str,
        input_text: str,
        threshold: float | None = None,
        *,
        enabled: bool | None = None,
    ) -> Optional[dict[str, Any]]:
        """Return a cached result when cosine similarity exceeds threshold, else None."""
        cache_enabled = settings.enable_semantic_cache if enabled is None else enabled
        if not cache_enabled or lancedb is None:
            return None

        table = self._get_table()
        if table is None:
            return None

        try:
            tenant_id = self._validate_filter_value(tenant_id, "tenant_id")
            task_type = self._validate_filter_value(task_type, "task_type")
            vector = await self._get_embedding(input_text)
            cutoff = threshold if threshold is not None else settings.cache_threshold

            results = (
                table.search(vector)
                .metric("cosine")
                .where(f"tenant_id = '{tenant_id}' AND task_type = '{task_type}'")
                .limit(1)
                .to_list()
            )

            if results:
                # LanceDB cosine distance is 1 - cosine_similarity (range [0, 1] for
                # unit-normalised embeddings).  A hit requires similarity > cutoff,
                # i.e. distance < 1 - cutoff.
                if results[0]["_distance"] < (1.0 - cutoff):
                    logger.debug(
                        "cache hit tenant=%s task=%s distance=%.4f",
                        tenant_id,
                        task_type,
                        results[0]["_distance"],
                    )
                    return results[0]["output"]

            logger.debug("cache miss tenant=%s task=%s", tenant_id, task_type)
        except ValueError:
            raise
        except Exception:
            logger.warning("cache read failed", exc_info=True)

        return None

    async def set(
        self,
        tenant_id: str,
        task_type: str,
        input_text: str,
        output: dict[str, Any],
        *,
        enabled: bool | None = None,
    ) -> None:
        """Persist an inference result for future semantic lookups."""
        cache_enabled = settings.enable_semantic_cache if enabled is None else enabled
        if not cache_enabled or lancedb is None:
            return

        try:
            vector = await self._get_embedding(input_text)
            db = self._get_db()
            row = [
                {
                    "vector": vector,
                    "input_text": input_text,
                    "output": output,
                    "tenant_id": tenant_id,
                    "task_type": task_type,
                }
            ]
            if self._table_name not in db.table_names():
                self._table = db.create_table(self._table_name, data=row, metric="cosine")
            else:
                table = self._get_table()
                table.add(row)
        except Exception:
            logger.warning("cache write failed", exc_info=True)


semantic_cache = SemanticCache()
