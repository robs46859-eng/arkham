"""
Memory Service (A-MEM)

Evolving memory system that stores atomic notes, links related context,
and improves future retrieval without dumping raw transcript history.

Memory types:
- User memory: Personal preferences, interaction history
- Task memory: Specific task context and outcomes
- Workflow memory: Multi-step workflow state and learnings
- Domain memory: BIM-specific knowledge and patterns
- Operational memory: System behavior and performance data
"""

import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.settings import settings
from app.notes import MemoryNoteStore
from app.retrieval import MemoryRetriever
from app.links import MemoryLinker

logger = logging.getLogger(__name__)


class MemoryNoteCreate(BaseModel):
    """Create a new memory note"""
    note_type: str  # user, task, workflow, domain, operational
    title: str
    content: str
    tenant_id: str
    user_id: Optional[str] = None
    workflow_id: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    importance: float = 0.5


class MemoryNote(BaseModel):
    """A memory note"""
    id: str
    note_type: str
    title: str
    content: str
    tenant_id: str
    tags: List[str]
    links: List[str]
    importance: float
    created_at: str
    updated_at: str


class MemoryQuery(BaseModel):
    """Query for memory retrieval"""
    query: str
    tenant_id: str
    note_types: Optional[List[str]] = None
    max_results: int = 10
    min_importance: float = 0.3


class MemoryResponse(BaseModel):
    """Memory retrieval response"""
    notes: List[MemoryNote]
    query: str
    total: int


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    logger.info("Starting Memory Service")
    
    app.state.note_store = MemoryNoteStore(settings.database_url)
    app.state.retriever = MemoryRetriever(
        database_url=settings.database_url,
        redis_url=settings.redis_url,
    )
    app.state.linker = MemoryLinker()
    
    await app.state.note_store.initialize()
    await app.state.retriever.initialize()
    
    yield
    
    # Shutdown
    logger.info("Shutting down Memory Service")
    await app.state.note_store.close()
    await app.state.retriever.close()


app = FastAPI(
    title="Memory Service (A-MEM)",
    description="Evolving memory system for FullStackArkham",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "memory"}


@app.get("/ready")
async def ready_check():
    """Readiness check endpoint"""
    if not hasattr(app.state, "note_store"):
        return {"status": "not ready", "reason": "note store not initialized"}
    return {"status": "ready"}


@app.post("/api/v1/notes", response_model=MemoryNote)
async def create_note(note_data: MemoryNoteCreate):
    """
    Create a new memory note
    
    Converts interactions into structured notes with:
    - Tagging and summarization
    - Link creation to related notes
    - Tenant and user scoping
    """
    note_store = app.state.note_store
    linker = app.state.linker
    
    # Create the note
    note_id = str(uuid4())
    note = {
        "id": note_id,
        "note_type": note_data.note_type,
        "title": note_data.title,
        "content": note_data.content,
        "tenant_id": note_data.tenant_id,
        "user_id": note_data.user_id,
        "workflow_id": note_data.workflow_id,
        "tags": note_data.tags,
        "links": [],
        "importance": note_data.importance,
        "decay_rate": 0.01,
        "accessed_count": 0,
    }
    
    await note_store.save(note)
    
    # Find and create links to related notes
    related_notes = await note_store.find_related(
        tenant_id=note_data.tenant_id,
        note_type=note_data.note_type,
        tags=note_data.tags,
    )
    
    links = linker.create_links(note, related_notes)
    note["links"] = links
    
    # Update with links
    await note_store.save(note)
    
    logger.info(f"Created memory note {note_id} type={note_data.note_type}")
    
    return MemoryNote(
        id=note["id"],
        note_type=note["note_type"],
        title=note["title"],
        content=note["content"],
        tenant_id=note["tenant_id"],
        tags=note["tags"],
        links=note["links"],
        importance=note["importance"],
        created_at=note.get("created_at", ""),
        updated_at=note.get("updated_at", ""),
    )


@app.get("/api/v1/notes/{note_id}", response_model=MemoryNote)
async def get_note(note_id: str):
    """Get a memory note by ID"""
    note_store = app.state.note_store
    
    note = await note_store.get_by_id(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    # Increment access count
    await note_store.increment_access(note_id)
    
    return MemoryNote(**note)


@app.post("/api/v1/retrieve", response_model=MemoryResponse)
async def retrieve_memory(query_data: MemoryQuery):
    """
    Retrieve relevant memory notes
    
    Uses hybrid retrieval:
    - Keyword matching on tags and titles
    - Semantic similarity on content embeddings
    - Link-based traversal for related context
    - Importance and recency weighting
    """
    retriever = app.state.retriever
    
    notes = await retriever.retrieve(
        query=query_data.query,
        tenant_id=query_data.tenant_id,
        note_types=query_data.note_types,
        max_results=query_data.max_results,
        min_importance=query_data.min_importance,
    )
    
    return MemoryResponse(
        notes=[
            MemoryNote(
                id=n["id"],
                note_type=n["note_type"],
                title=n["title"],
                content=n["content"],
                tenant_id=n["tenant_id"],
                tags=n["tags"],
                links=n["links"],
                importance=n["importance"],
                created_at=n.get("created_at", ""),
                updated_at=n.get("updated_at", ""),
            )
            for n in notes
        ],
        query=query_data.query,
        total=len(notes),
    )


@app.post("/api/v1/notes/{note_id}/evolve")
async def evolve_note(
    note_id: str,
    new_content: Optional[str] = None,
    new_tags: Optional[List[str]] = None,
    importance_delta: float = 0.0,
):
    """
    Evolve a memory note
    
    Updates note based on new information:
    - Merges content (summarization if needed)
    - Adds new tags
    - Adjusts importance based on usage
    - Creates/updates links
    """
    note_store = app.state.note_store
    linker = app.state.linker
    
    note = await note_store.get_by_id(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    # Update content
    if new_content:
        # Simple append for now - would use summarization in production
        note["content"] = f"{note['content']}\n\n[Updated]: {new_content}"
    
    # Add tags
    if new_tags:
        existing_tags = set(note["tags"])
        note["tags"] = list(existing_tags | set(new_tags))
    
    # Adjust importance
    note["importance"] = min(1.0, max(0.0, note["importance"] + importance_delta))
    
    # Re-link based on new content
    related_notes = await note_store.find_related(
        tenant_id=note["tenant_id"],
        note_type=note["note_type"],
        tags=note["tags"],
    )
    note["links"] = linker.create_links(note, related_notes)
    
    await note_store.save(note)
    
    return {"status": "updated", "note_id": note_id}


@app.delete("/api/v1/notes/{note_id}")
async def delete_note(note_id: str):
    """Delete a memory note"""
    note_store = app.state.note_store
    await note_store.delete(note_id)
    return {"status": "deleted", "note_id": note_id}


@app.get("/api/v1/notes")
async def list_notes(
    tenant_id: str,
    note_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """List memory notes for a tenant"""
    note_store = app.state.note_store
    
    notes = await note_store.list_by_tenant(
        tenant_id=tenant_id,
        note_type=note_type,
        limit=limit,
        offset=offset,
    )
    
    return {
        "notes": [
            {
                "id": n["id"],
                "note_type": n["note_type"],
                "title": n["title"],
                "tags": n["tags"],
                "importance": n["importance"],
                "created_at": n.get("created_at", ""),
            }
            for n in notes
        ],
        "total": len(notes),
    }


@app.post("/api/v1/prune")
async def prune_memory(
    tenant_id: str,
    max_age_days: int = 90,
    min_importance: float = 0.2,
    dry_run: bool = True,
):
    """
    Prune old or low-importance memory notes
    
    Memory decay is automatic based on:
    - Time since last access
    - Importance score
    - Access frequency
    
    This endpoint allows explicit pruning.
    """
    note_store = app.state.note_store
    
    pruned = await note_store.prune(
        tenant_id=tenant_id,
        max_age_days=max_age_days,
        min_importance=min_importance,
        dry_run=dry_run,
    )
    
    return {
        "pruned_count": len(pruned),
        "pruned_ids": [n["id"] for n in pruned] if not dry_run else [],
        "dry_run": dry_run,
    }


@app.get("/api/v1/stats")
async def get_memory_stats(tenant_id: str):
    """Get memory statistics for a tenant"""
    note_store = app.state.note_store
    
    stats = await note_store.get_stats(tenant_id)
    
    return {
        "tenant_id": tenant_id,
        "total_notes": stats.get("total", 0),
        "by_type": stats.get("by_type", {}),
        "avg_importance": stats.get("avg_importance", 0),
        "oldest_note": stats.get("oldest_note"),
        "newest_note": stats.get("newest_note"),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8085,
        reload=True,
    )
