"""
Memory Note Store

PostgreSQL storage for memory notes with embedding support.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

import asyncpg
from orjson import dumps, loads

logger = logging.getLogger(__name__)


class MemoryNoteStore:
    """PostgreSQL-backed memory note storage"""
    
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
        logger.info("Memory note store initialized")
    
    async def close(self):
        """Close database connections"""
        if self.pool:
            await self.pool.close()
    
    async def save(self, note: Dict[str, Any]):
        """Save or update a memory note"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO memory_notes (
                    id, tenant_id, user_id, workflow_id, note_type,
                    title, content, tags, links, importance, decay_rate,
                    accessed_count, last_accessed_at, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, NOW(), NOW())
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    content = EXCLUDED.content,
                    tags = EXCLUDED.tags,
                    links = EXCLUDED.links,
                    importance = EXCLUDED.importance,
                    decay_rate = EXCLUDED.decay_rate,
                    updated_at = NOW()
            """,
                note["id"],
                note["tenant_id"],
                note.get("user_id"),
                note.get("workflow_id"),
                note["note_type"],
                note["title"],
                note["content"],
                note.get("tags", []),
                note.get("links", []),
                note.get("importance", 0.5),
                note.get("decay_rate", 0.01),
                note.get("accessed_count", 0),
                note.get("last_accessed_at"),
            )
    
    async def get_by_id(self, note_id: str) -> Optional[Dict[str, Any]]:
        """Get a note by ID"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM memory_notes WHERE id = $1
            """, note_id)
            
            if not row:
                return None
            
            return {
                "id": str(row["id"]),
                "tenant_id": str(row["tenant_id"]),
                "user_id": str(row["user_id"]) if row["user_id"] else None,
                "workflow_id": str(row["workflow_id"]) if row["workflow_id"] else None,
                "note_type": row["note_type"],
                "title": row["title"],
                "content": row["content"],
                "tags": list(row["tags"]) if row["tags"] else [],
                "links": list(row["links"]) if row["links"] else [],
                "importance": row["importance"],
                "decay_rate": row["decay_rate"],
                "accessed_count": row["accessed_count"],
                "last_accessed_at": row["last_accessed_at"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
    
    async def find_related(
        self,
        tenant_id: str,
        note_type: str,
        tags: List[str],
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Find notes related by type and tags"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM memory_notes
                WHERE tenant_id = $1
                AND note_type = $2
                AND tags && $3
                AND importance > 0.3
                ORDER BY importance DESC, created_at DESC
                LIMIT $4
            """, tenant_id, note_type, tags, limit)
            
            return [
                {
                    "id": str(row["id"]),
                    "note_type": row["note_type"],
                    "title": row["title"],
                    "tags": list(row["tags"]),
                    "importance": row["importance"],
                }
                for row in rows
            ]
    
    async def list_by_tenant(
        self,
        tenant_id: str,
        note_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List notes for a tenant"""
        async with self.pool.acquire() as conn:
            if note_type:
                rows = await conn.fetch("""
                    SELECT * FROM memory_notes
                    WHERE tenant_id = $1 AND note_type = $2
                    ORDER BY created_at DESC
                    LIMIT $3 OFFSET $4
                """, tenant_id, note_type, limit, offset)
            else:
                rows = await conn.fetch("""
                    SELECT * FROM memory_notes
                    WHERE tenant_id = $1
                    ORDER BY created_at DESC
                    LIMIT $2 OFFSET $3
                """, tenant_id, limit, offset)
            
            return [
                {
                    "id": str(row["id"]),
                    "note_type": row["note_type"],
                    "title": row["title"],
                    "tags": list(row["tags"]),
                    "importance": row["importance"],
                    "created_at": row["created_at"],
                }
                for row in rows
            ]
    
    async def increment_access(self, note_id: str):
        """Increment access count and update last accessed time"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE memory_notes SET
                    accessed_count = accessed_count + 1,
                    last_accessed_at = NOW(),
                    updated_at = NOW()
                WHERE id = $1
            """, note_id)
    
    async def prune(
        self,
        tenant_id: str,
        max_age_days: int = 90,
        min_importance: float = 0.2,
        dry_run: bool = True,
    ) -> List[Dict[str, Any]]:
        """Find notes to prune based on age and importance"""
        cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM memory_notes
                WHERE tenant_id = $1
                AND (
                    (importance < $2)
                    OR (created_at < $3 AND accessed_count = 0)
                )
                ORDER BY importance ASC, created_at ASC
            """, tenant_id, min_importance, cutoff_date)
            
            pruned = [
                {
                    "id": str(row["id"]),
                    "title": row["title"],
                    "importance": row["importance"],
                    "created_at": row["created_at"],
                }
                for row in rows
            ]
            
            if not dry_run:
                # Actually delete
                await conn.execute("""
                    DELETE FROM memory_notes
                    WHERE tenant_id = $1
                    AND id = ANY($2)
                """, tenant_id, [n["id"] for n in pruned])
            
            return pruned
    
    async def get_stats(self, tenant_id: str) -> Dict[str, Any]:
        """Get memory statistics for a tenant"""
        async with self.pool.acquire() as conn:
            # Total count
            total_row = await conn.fetchrow("""
                SELECT COUNT(*) as count FROM memory_notes
                WHERE tenant_id = $1
            """, tenant_id)
            
            # Count by type
            type_rows = await conn.fetch("""
                SELECT note_type, COUNT(*) as count
                FROM memory_notes
                WHERE tenant_id = $1
                GROUP BY note_type
            """, tenant_id)
            
            # Average importance
            avg_row = await conn.fetchrow("""
                SELECT AVG(importance) as avg_imp FROM memory_notes
                WHERE tenant_id = $1
            """, tenant_id)
            
            # Oldest and newest
            date_row = await conn.fetchrow("""
                SELECT MIN(created_at) as oldest, MAX(created_at) as newest
                FROM memory_notes
                WHERE tenant_id = $1
            """, tenant_id)
            
            return {
                "total": total_row["count"] if total_row else 0,
                "by_type": {r["note_type"]: r["count"] for r in type_rows},
                "avg_importance": float(avg_row["avg_imp"]) if avg_row and avg_row["avg_imp"] else 0,
                "oldest_note": date_row["oldest"] if date_row else None,
                "newest_note": date_row["newest"] if date_row else None,
            }
    
    async def delete(self, note_id: str):
        """Delete a note"""
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM memory_notes WHERE id = $1", note_id)
