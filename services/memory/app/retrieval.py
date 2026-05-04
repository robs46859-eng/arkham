"""
Memory Retrieval

Hybrid retrieval combining keyword, semantic, and link-based search.
"""

import logging
from typing import Dict, Any, List, Optional

import asyncpg
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class MemoryRetriever:
    """Hybrid memory retrieval"""
    
    def __init__(self, database_url: str, redis_url: str):
        self.database_url = database_url
        self.redis_url = redis_url
        self.db_pool: Optional[asyncpg.Pool] = None
        self.redis_client: Optional[redis.Redis] = None
    
    async def initialize(self):
        """Initialize connections"""
        self.db_pool = await asyncpg.create_pool(self.database_url)
        self.redis_client = redis.from_url(self.redis_url)
        logger.info("Memory retriever initialized")
    
    async def close(self):
        """Close connections"""
        if self.db_pool:
            await self.db_pool.close()
        if self.redis_client:
            await self.redis_client.close()
    
    async def retrieve(
        self,
        query: str,
        tenant_id: str,
        note_types: Optional[List[str]] = None,
        max_results: int = 10,
        min_importance: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant memory notes using hybrid approach
        
        1. Keyword match on tags and titles
        2. Filter by tenant, type, importance
        3. Boost by access count and recency
        4. Return top results
        """
        async with self.db_pool.acquire() as conn:
            # Build query with optional type filter
            type_filter = ""
            params = [tenant_id, min_importance, max_results]
            
            if note_types:
                placeholders = ",".join([f"${i}" for i in range(3, 3 + len(note_types))])
                type_filter = f"AND note_type IN ({placeholders})"
                params = [tenant_id, min_importance] + note_types + [max_results]
            
            # Hybrid scoring:
            # - Keyword match on title and tags (full-text search)
            # - Importance weighting
            # - Access count boost
            # - Recency boost
            rows = await conn.fetch(f"""
                SELECT *,
                    (
                        0.5 * importance +
                        0.3 * (CASE WHEN accessed_count > 0 THEN LN(accessed_count + 1) / 10 ELSE 0 END) +
                        0.2 * (CASE 
                            WHEN created_at > NOW() - INTERVAL '7 days' THEN 1.0
                            WHEN created_at > NOW() - INTERVAL '30 days' THEN 0.7
                            WHEN created_at > NOW() - INTERVAL '90 days' THEN 0.4
                            ELSE 0.2
                        END)
                    ) as relevance_score
                FROM memory_notes
                WHERE tenant_id = $1
                AND importance >= $2
                AND (
                    title ILIKE $3 OR
                    content ILIKE $4 OR
                    tags && $5
                )
                {type_filter}
                ORDER BY relevance_score DESC
                LIMIT $6
            """, tenant_id, min_importance, f"%{query}%", f"%{query}%", [query], *([max_results] if not note_types else []))
            
            # Simpler query for now - can be enhanced with proper full-text search
            simple_rows = await conn.fetch("""
                SELECT * FROM memory_notes
                WHERE tenant_id = $1
                AND importance >= $2
                AND (
                    title ILIKE $3 OR
                    content ILIKE $4 OR
                    $5 = ANY(tags)
                )
                ORDER BY importance DESC, accessed_count DESC, created_at DESC
                LIMIT $6
            """, tenant_id, min_importance, f"%{query}%", f"%{query}%", query, max_results)
            
            return [
                {
                    "id": str(row["id"]),
                    "tenant_id": str(row["tenant_id"]),
                    "note_type": row["note_type"],
                    "title": row["title"],
                    "content": row["content"],
                    "tags": list(row["tags"]),
                    "links": list(row["links"]),
                    "importance": row["importance"],
                    "accessed_count": row["accessed_count"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
                for row in simple_rows
            ]
    
    async def retrieve_by_workflow(
        self,
        tenant_id: str,
        workflow_id: str,
    ) -> List[Dict[str, Any]]:
        """Get all memory notes linked to a workflow"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM memory_notes
                WHERE tenant_id = $1
                AND workflow_id = $2
                ORDER BY created_at ASC
            """, tenant_id, workflow_id)
            
            return [
                {
                    "id": str(row["id"]),
                    "note_type": row["note_type"],
                    "title": row["title"],
                    "content": row["content"],
                    "importance": row["importance"],
                }
                for row in rows
            ]
    
    async def retrieve_by_user(
        self,
        tenant_id: str,
        user_id: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get memory notes for a specific user"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM memory_notes
                WHERE tenant_id = $1
                AND user_id = $2
                ORDER BY importance DESC, accessed_count DESC
                LIMIT $3
            """, tenant_id, user_id, limit)
            
            return [
                {
                    "id": str(row["id"]),
                    "note_type": row["note_type"],
                    "title": row["title"],
                    "content": row["content"],
                    "importance": row["importance"],
                }
                for row in rows
            ]
    
    async def get_linked_notes(
        self,
        note_id: str,
        max_hops: int = 2,
    ) -> List[Dict[str, Any]]:
        """
        Traverse links to find related notes
        
        Uses BFS to find notes within max_hops distance.
        """
        # Get starting note
        async with self.db_pool.acquire() as conn:
            start = await conn.fetchrow(
                "SELECT * FROM memory_notes WHERE id = $1", note_id
            )
            
            if not start:
                return []
            
            visited = {note_id}
            to_visit = [start]
            result = []
            
            for hop in range(max_hops):
                next_visit = []
                
                for note in to_visit:
                    links = list(note["links"]) if note["links"] else []
                    
                    for linked_id in links:
                        if linked_id not in visited:
                            visited.add(linked_id)
                            linked_note = await conn.fetchrow(
                                "SELECT * FROM memory_notes WHERE id = $1", linked_id
                            )
                            
                            if linked_note:
                                result.append({
                                    "id": str(linked_note["id"]),
                                    "title": linked_note["title"],
                                    "note_type": linked_note["note_type"],
                                    "importance": linked_note["importance"],
                                    "hop": hop + 1,
                                })
                                next_visit.append(linked_note)
                
                to_visit = next_visit
            
            return result
