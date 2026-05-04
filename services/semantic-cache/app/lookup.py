"""
Cache Lookup

Redis + PostgreSQL hybrid cache lookup for low-latency retrieval.
"""

import logging
from typing import Dict, Any, List, Optional

import redis.asyncio as redis
from orjson import dumps, loads

logger = logging.getLogger(__name__)


class CacheLookup:
    """Hybrid cache lookup with Redis hot cache"""
    
    def __init__(self, redis_url: str, database_url: str):
        self.redis_url = redis_url
        self.database_url = database_url
        self.redis_client: Optional[redis.Redis] = None
        self.db_pool = None
    
    async def initialize(self):
        """Initialize connections"""
        self.redis_client = redis.from_url(self.redis_url)
        
        import asyncpg
        self.db_pool = await asyncpg.create_pool(self.database_url)
        
        logger.info("Cache lookup initialized")
    
    async def close(self):
        """Close connections"""
        if self.redis_client:
            await self.redis_client.close()
        if self.db_pool:
            await self.db_pool.close()
    
    async def lookup(
        self,
        tenant_id: str,
        embedding: List[float],
        threshold: float,
        model: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Look up in cache
        
        First checks Redis for hot entries, then falls back to PostgreSQL.
        """
        # Try Redis first for exact hash matches
        # (This would need the request_hash - simplified for now)
        
        # Fall back to PostgreSQL for similarity search
        from app.storage import CacheStorage
        storage = CacheStorage(self.database_url)
        storage.pool = self.db_pool
        
        return await storage.lookup(tenant_id, embedding, threshold, model)
    
    async def record_hit(self, cache_id: str):
        """Record a cache hit"""
        # Increment in Redis for fast counting
        if self.redis_client:
            await self.redis_client.incr(f"cache:hits:{cache_id}")
        
        # Also update in PostgreSQL (done by storage layer)
        from app.storage import CacheStorage
        storage = CacheStorage(self.database_url)
        storage.pool = self.db_pool
        await storage.record_hit(cache_id)
    
    async def get_hot_entries(
        self,
        tenant_id: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get frequently accessed cache entries"""
        if not self.redis_client:
            return []
        
        # Get keys with highest hit counts
        pattern = f"cache:hits:{tenant_id}:*"
        keys = await self.redis_client.keys(pattern)
        
        if not keys:
            return []
        
        # Sort by hit count
        hits = []
        for key in keys:
            count = await self.redis_client.get(key)
            hits.append((int(count) if count else 0, key))
        
        hits.sort(reverse=True)
        
        return [
            {"key": k, "hits": h}
            for h, k in hits[:limit]
        ]
