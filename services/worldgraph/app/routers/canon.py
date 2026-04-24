"""Canonical entity read routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from packages.db import get_db
from packages.schemas.worldgraph import WorldgraphEntity

from ..services import store

router = APIRouter(prefix="/v1/worldgraph", tags=["worldgraph-canonical"])


@router.get("/{namespace}/entities/{entity_id}", response_model=WorldgraphEntity)
def get_worldgraph_entity(
    namespace: str,
    entity_id: str,
    db: Session = Depends(get_db),
) -> WorldgraphEntity:
    entity = store.get_entity(db, namespace=namespace, entity_id=entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail=f"Entity {entity_id} not found")
    return entity

