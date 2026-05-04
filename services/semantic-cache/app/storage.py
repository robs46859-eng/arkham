"""
Cache Storage

PostgreSQL storage for semantic cache with vector similarity search.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

import asyncpg
from orjson import dumps, loads

logger = logging.getLogger(__name__)


class CacheStorage:
    """PostgreSQL-backed semantic cache storage"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool: Optional[asyncpg.Pool] = None
    
    async def initialize(self):
        """Initialize database connection pool"""
        self.pool = await asyncpg.create_pool(
            self.database_url,
            min_size=5,
            max_size=20,
        )
        logger.info("Cache storage initialized")
    
    async def close(self):
        """Close database connections"""
        if self.pool:
            await self.pool.close()
    
    async def store(
        self,
        tenant_id: str,
        request_hash: str,
        request_embedding: List[float],
        response: Dict[str, Any],
        model: str,
        task_type: Optional[str] = None,
        similarity_threshold: float = 0.95,
    ):
        """Store a response in the cache"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO semantic_cache (
                    id, tenant_id, request_hash, request_embedding,
                    response, model, task_type, similarity_threshold,
                    hit_count, cached_at, expires_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 0, NOW(), NOW() + INTERVAL '30 days')
                ON CONFLICT (tenant_id, request_hash) DO UPDATE SET
                    response = EXCLUDED.response,
                    model = EXCLUDED.model,
                    task_type = EXCLUDED.task_type,
                    expires_at = NOW() + INTERVAL '30 days'
            """,
                str(__import__("uuid").uuid4()),
                tenant_id,
                request_hash,
                request_embedding,
                dumps(response),
                model,
                task_type,
                similarity_threshold,
            )
    
    async def lookup(
        self,
        tenant_id: str,
        embedding: List[float],
        threshold: float,
        model: Optional[str] = None,
        limit: int = 1,
    ) -> Optional[Dict[str, Any]]:
        """
        Look up similar cached responses
        
        Uses cosine similarity on the embedding vector.
        """
        async with self.pool.acquire() as conn:
            # Build query - filter by model if specified
            model_filter = "AND model = $4" if model else ""
            params = [tenant_id, threshold, limit]
            if model:
                params.append(model)
            
            # Cosine similarity using vector extension
            # Note: Requires pgvector extension for production
            # For now, using simplified approach
            rows = await conn.fetch(f"""
                SELECT id, request_hash, response, model, task_type,
                    similarity_threshold, hit_count, cached_at,
                    1.0 - (request_embedding <-> $2::vector) as similarity
                FROM semantic_cache
                WHERE tenant_id = $1
                AND similarity_threshold <= $3
                AND (expires_at IS NULL OR expires_at > NOW())
                {model_filter}
                ORDER BY similarity DESC
                LIMIT $4
            """, tenant_id, f"[{','.join(map(str, embedding))}]", threshold, limit)
            
            if not rows:
                return None
            
            # Return best match above threshold
            for row in rows:
                similarity = float(row["similarity"]) if row["similarity"] else 0
                if similarity >= threshold:
                    return {
                        "id": str(row["id"]),
                        "response": loads(row["response"]),
                        "similarity": similarity,
                        "cached_at": row["cached_at"].isoformat() if row["cached_at"] else None,
                    }
            
            return None
    
    async def record_hit(self, cache_id: str):
        """Increment hit count for a cache entry"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE semantic_cache
                SET hit_count = hit_count + 1
                WHERE id = $1
            """, cache_id)
    
    async def delete_by_hash(
        self,
        tenant_id: str,
        request_hash: str,
    ) -> int:
        """Delete cache entry by hash"""
        async with self.pool.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM semantic_cache
                WHERE tenant_id = $1 AND request_hash = $2
            """, tenant_id, request_hash)
            return int(result.split()[-1]) if result else 0
    
    async def delete_by_model(
        self,
        tenant_id: str,
        model: str,
    ) -> int:
        """Delete cache entries by model"""
        async with self.pool.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM semantic_cache
                WHERE tenant_id = $1 AND model = $2
            """, tenant_id, model)
            return int(result.split()[-1]) if result else 0
    
    async def delete_by_tenant(self, tenant_id: str) -> int:
        """Delete all cache entries for a tenant"""
        async with self.pool.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM semantic_cache
                WHERE tenant_id = $1
            """, tenant_id)
            return int(result.split()[-1]) if result else 0
    
    async def get_stats(self, tenant_id: str) -> Dict[str, Any]:
        """Get cache statistics"""
        async with self.pool.acquire() as conn:
            # Total and hits
            stats_row = await conn.fetchrow("""
                SELECT
                    COUNT(*) as total,
                    SUM(hit_count) as total_hits,
                    AVG(hit_count) as avg_hits
                FROM semantic_cache
                WHERE tenant_id = $1
            """, tenant_id)
            
            # By model
            model_rows = await conn.fetch("""
                SELECT model, COUNT(*) as count, SUM(hit_count) as hits
                FROM semantic_cache
                WHERE tenant_id = $1
                GROUP BY model
            """, tenant_id)
            
            # By task type
            task_rows = await conn.fetch("""
                SELECT task_type, COUNT(*) as count, SUM(hit_count) as hits
                FROM semantic_cache
                WHERE tenant_id = $1
                GROUP BY task_type
            """, tenant_id)
            
            # Date range
            date_row = await conn.fetchrow("""
                SELECT MIN(cached_at) as oldest, MAX(cached_at) as newest
                FROM semantic_cache
                WHERE tenant_id = $1
            """, tenant_id)
            
            total = stats_row["total"] or 0
            total_hits = stats_row["total_hits"] or 0
            
            return {
                "total": total,
                "total_hits": total_hits,
                "hit_rate": total_hits / total if total > 0 else 0,
                "by_model": {r["model"]: {"count": r["count"], "hits": r["hits"] or 0} for r in model_rows},
                "by_task_type": {r["task_type"]: {"count": r["count"], "hits": r["hits"] or 0} for r in task_rows},
                "avg_similarity": float(stats_row["avg_hits"]) if stats_row["avg_hits"] else 0,
                "oldest_entry": date_row["oldest"],
                "newest_entry": date_row["newest"],
            }
    
    async def list_entries(
        self,
        tenant_id: str,
        model: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List cache entries"""
        async with self.pool.acquire() as conn:
            if model:
                rows = await conn.fetch("""
                    SELECT id, request_hash, model, task_type, hit_count, cached_at
                    FROM semantic_cache
                    WHERE tenant_id = $1 AND model = $2
                    ORDER BY cached_at DESC
                    LIMIT $3 OFFSET $4
                """, tenant_id, model, limit, offset)
            else:
                rows = await conn.fetch("""
                    SELECT id, request_hash, model, task_type, hit_count, cached_at
                    FROM semantic_cache
                    WHERE tenant_id = $1
                    ORDER BY cached_at DESC
                    LIMIT $2 OFFSET $3
                """, tenant_id, limit, offset)
            
            return [
                {
                    "id": str(row["id"]),
                    "request_hash": row["request_hash"],
                    "model": row["model"],
                    "task_type": row["task_type"],
                    "hit_count": row["hit_count"],
                    "cached_at": row["cached_at"],
                }
                for row in rows
            ]
    
    async def cleanup_expired(self) -> int:
        """Remove expired cache entries"""
        async with self.pool.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM semantic_cache
                WHERE expires_at IS NOT NULL AND expires_at < NOW()
            """)
            return int(result.split()[-1]) if result else 0
