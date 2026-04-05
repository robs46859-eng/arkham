"""
Semantic Cache provider using LanceDB and Ollama/OpenAI embeddings.
Implements: Master Architecture §4.4 — Semantic Cache.
"""

from __future__ import annotations

import os
from typing import Any, Optional

import httpx
import lancedb
from pydantic import BaseModel

from ..settings import settings


class CacheEntry(BaseModel):
    vector: list[float]
    input_text: str
    output: dict[str, Any]
    tenant_id: str
    task_type: str


class SemanticCache:
    """
    Handles semantic cache lookup and persistence.
    Reduces redundant inference by serving similar past requests.
    """

    def __init__(self):
        self._db = None
        self._table = None
        self._table_name = "semantic_cache"

    def _get_db(self):
        if self._db is None:
            os.makedirs(settings.vector_store_path, exist_ok=True)
            self._db = lancedb.connect(settings.vector_store_path)
        return self._db

    def _get_table(self):
        if self._table is None:
            db = self._get_db()
            if self._table_name not in db.table_names():
                # Lazy initialization: schema will be inferred from first insert
                self._table = None
            else:
                self._table = db.open_table(self._table_name)
        return self._table

    async def _get_embedding(self, text: str) -> list[float]:
        """Fetch embeddings from the configured provider."""
        if settings.embedding_provider == "ollama":
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{settings.ollama_host}/api/embeddings",
                    json={
                        "model": settings.embedding_model,
                        "prompt": text,
                    },
                )
                response.raise_for_status()
                return response.json()["embedding"]
        elif settings.embedding_provider == "openai":
            if not settings.openai_api_key:
                raise ValueError("openai_api_key is required for openai embeddings")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{settings.openai_base_url or 'https://api.openai.com/v1'}/embeddings",
                    headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                    json={
                        "model": settings.embedding_model,
                        "input": text,
                    },
                )
                response.raise_for_status()
                return response.json()["data"][0]["embedding"]
        else:
            raise ValueError(f"Unsupported embedding provider: {settings.embedding_provider}")

    async def get(
        self,
        tenant_id: str,
        task_type: str,
        input_text: str,
        threshold: float | None = None,
    ) -> Optional[dict[str, Any]]:
        """
        Perform a semantic lookup for a similar past request.
        Only returns if similarity > threshold and tenant_id matches.
        """
        if not settings.enable_semantic_cache:
            return None

        table = self._get_table()
        if table is None:
            return None

        try:
            vector = await self._get_embedding(input_text)
            # threshold in lancedb distance is usually L2 or Cosine.
            # We want similarity > threshold, so distance < (1 - threshold) for cosine.
            # LanceDB default is L2.
            results = (
                table.search(vector)
                .where(f"tenant_id = '{tenant_id}' AND task_type = '{task_type}'")
                .limit(1)
                .to_list()
            )

            if results:
                match = results[0]
                # Rough distance-to-similarity conversion for L2 (simplified)
                # For more accuracy, we'd use cosine distance.
                # If distance is very small, it's a hit.
                actual_threshold = threshold if threshold is not None else settings.cache_threshold
                # LanceDB results include _distance.
                # Smaller distance = more similar.
                if match["_distance"] < (1.0 - actual_threshold) * 2:  # heuristic for L2 approx
                    return match["output"]
        except Exception:
            # Silent fail for cache reads to avoid breaking the main flow
            return None

        return None

    async def set(
        self,
        tenant_id: str,
        task_type: str,
        input_text: str,
        output: dict[str, Any],
    ) -> None:
        """Store a new inference result in the cache."""
        if not settings.enable_semantic_cache:
            return

        try:
            vector = await self._get_embedding(input_text)
            db = self._get_db()
            data = [
                {
                    "vector": vector,
                    "input_text": input_text,
                    "output": output,
                    "tenant_id": tenant_id,
                    "task_type": task_type,
                }
            ]

            if self._table_name not in db.table_names():
                self._table = db.create_table(self._table_name, data=data)
            else:
                table = db.open_table(self._table_name)
                table.add(data)
        except Exception:
            # Silent fail for cache writes
            pass


semantic_cache = SemanticCache()
