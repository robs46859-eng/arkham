"""
Semantic Cache Service

Reduces repeated model spend and latency by serving prior responses
when query intent is sufficiently similar.

Features:
- Normalize incoming requests
- Generate embeddings for cacheable requests
- Perform vector similarity lookup
- Apply threshold policy by task type
- Track hit rate, drift, and savings
"""

import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.settings import settings
from app.lookup import CacheLookup
from app.embeddings import EmbeddingService
from app.storage import CacheStorage

logger = logging.getLogger(__name__)


class CacheRequest(BaseModel):
    """Request to check/store in cache"""
    tenant_id: str
    request_text: str
    model: str
    task_type: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CacheResponse(BaseModel):
    """Cache response"""
    hit: bool
    response: Optional[Dict[str, Any]] = None
    similarity: Optional[float] = None
    cached_at: Optional[str] = None
    message: str


class CacheStoreRequest(BaseModel):
    """Store a response in cache"""
    tenant_id: str
    request_text: str
    request_embedding: List[float]
    response: Dict[str, Any]
    model: str
    task_type: Optional[str] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    logger.info("Starting Semantic Cache Service")
    
    app.state.embedding_service = EmbeddingService()
    app.state.cache_storage = CacheStorage(settings.database_url)
    app.state.cache_lookup = CacheLookup(
        redis_url=settings.redis_url,
        database_url=settings.database_url,
    )
    
    await app.state.cache_storage.initialize()
    await app.state.cache_lookup.initialize()
    
    yield
    
    # Shutdown
    logger.info("Shutting down Semantic Cache Service")
    await app.state.cache_storage.close()
    await app.state.cache_lookup.close()


app = FastAPI(
    title="Semantic Cache Service",
    description="Semantic caching for inference requests",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "semantic-cache"}


@app.get("/ready")
async def ready_check():
    """Readiness check endpoint"""
    if not hasattr(app.state, "cache_storage"):
        return {"status": "not ready", "reason": "cache storage not initialized"}
    return {"status": "ready"}


@app.post("/api/v1/cache/lookup", response_model=CacheResponse)
async def lookup_cache(request_data: CacheRequest):
    """
    Look up a cached response
    
    1. Generate embedding for request
    2. Search for similar cached requests
    3. Apply threshold based on task type
    4. Return cached response if hit
    """
    embedding_service = app.state.embedding_service
    cache_lookup = app.state.cache_lookup
    
    # Get threshold for task type
    threshold = get_threshold_for_task(request_data.task_type)
    
    # Generate embedding
    embedding = await embedding_service.embed(request_data.request_text)
    
    # Look up in cache
    result = await cache_lookup.lookup(
        tenant_id=request_data.tenant_id,
        embedding=embedding,
        threshold=threshold,
        model=request_data.model,
    )
    
    if result:
        logger.info(
            f"Cache HIT: similarity={result['similarity']:.3f} "
            f"tenant={request_data.tenant_id}"
        )
        
        # Update hit count
        await cache_lookup.record_hit(result["id"])
        
        return CacheResponse(
            hit=True,
            response=result["response"],
            similarity=result["similarity"],
            cached_at=result["cached_at"],
            message="Cache hit",
        )
    
    logger.info(f"Cache MISS: tenant={request_data.tenant_id}")
    
    return CacheResponse(
        hit=False,
        message="Cache miss",
    )


@app.post("/api/v1/cache/store")
async def store_in_cache(request_data: CacheStoreRequest):
    """
    Store a response in the cache
    
    1. Validate request
    2. Store embedding and response
    3. Index for retrieval
    """
    cache_storage = app.state.cache_storage
    
    # Generate ID from request hash
    import hashlib
    request_hash = hashlib.sha256(
        request_data.request_text.encode()
    ).hexdigest()
    
    # Store in database
    await cache_storage.store(
        tenant_id=request_data.tenant_id,
        request_hash=request_hash,
        request_embedding=request_data.request_embedding,
        response=request_data.response,
        model=request_data.model,
        task_type=request_data.task_type,
    )
    
    logger.info(f"Stored in cache: hash={request_hash[:16]}...")
    
    return {
        "status": "stored",
        "request_hash": request_hash,
    }


@app.post("/api/v1/cache/invalidate")
async def invalidate_cache(
    tenant_id: str,
    request_hash: Optional[str] = None,
    model: Optional[str] = None,
    all: bool = False,
):
    """Invalidate cached responses"""
    cache_storage = app.state.cache_storage
    
    if all:
        count = await cache_storage.delete_by_tenant(tenant_id)
        return {"status": "deleted", "count": count}
    
    if request_hash:
        count = await cache_storage.delete_by_hash(tenant_id, request_hash)
        return {"status": "deleted", "count": count}
    
    if model:
        count = await cache_storage.delete_by_model(tenant_id, model)
        return {"status": "deleted", "count": count}
    
    raise HTTPException(status_code=400, detail="Must specify hash, model, or all=true")


@app.get("/api/v1/cache/stats")
async def get_cache_stats(tenant_id: str):
    """Get cache statistics for a tenant"""
    cache_storage = app.state.cache_storage
    
    stats = await cache_storage.get_stats(tenant_id)
    
    return {
        "tenant_id": tenant_id,
        "total_entries": stats.get("total", 0),
        "total_hits": stats.get("total_hits", 0),
        "hit_rate": stats.get("hit_rate", 0),
        "by_model": stats.get("by_model", {}),
        "by_task_type": stats.get("by_task_type", {}),
        "avg_similarity": stats.get("avg_similarity", 0),
        "oldest_entry": stats.get("oldest_entry"),
        "newest_entry": stats.get("newest_entry"),
    }


@app.get("/api/v1/cache/entries")
async def list_cache_entries(
    tenant_id: str,
    model: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """List cache entries for a tenant"""
    cache_storage = app.state.cache_storage
    
    entries = await cache_storage.list_entries(
        tenant_id=tenant_id,
        model=model,
        limit=limit,
        offset=offset,
    )
    
    return {
        "entries": [
            {
                "id": e["id"],
                "request_hash": e["request_hash"][:16] + "...",
                "model": e["model"],
                "task_type": e.get("task_type"),
                "hit_count": e["hit_count"],
                "cached_at": e["cached_at"],
            }
            for e in entries
        ],
        "total": len(entries),
    }


def get_threshold_for_task(task_type: Optional[str]) -> float:
    """
    Get similarity threshold for task type
    
    Conservative thresholds for technical or regulated tasks.
    More permissive for FAQ, support, repeated conversational work.
    """
    thresholds = {
        # Conservative - need high similarity
        "compliance": 0.98,
        "legal": 0.98,
        "medical": 0.97,
        "financial": 0.97,
        "code_generation": 0.95,
        
        # Moderate
        "analysis": 0.92,
        "extraction": 0.90,
        "classification": 0.88,
        
        # Permissive - safe to reuse
        "faq": 0.85,
        "support": 0.85,
        "chat": 0.82,
        "summarization": 0.80,
    }
    
    return thresholds.get(task_type, 0.90)  # Default threshold


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8084,
        reload=True,
    )
