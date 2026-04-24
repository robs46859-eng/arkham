"""Search routes for canonical worldgraph travel entities."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from packages.db import get_db
from packages.schemas.worldgraph import WorldgraphEntity

from ..services import store

router = APIRouter(prefix="/v1/worldgraph", tags=["worldgraph-search"])


@router.get("/{namespace}/entities", response_model=list[WorldgraphEntity])
def search_entities(
    namespace: str,
    q: Annotated[str | None, Query()] = None,
    entity_type: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    db: Session = Depends(get_db),
) -> list[WorldgraphEntity]:
    return store.list_entities(db, namespace=namespace, query_text=q, entity_type=entity_type, limit=limit)


@router.get("/{namespace}/search", response_model=list[WorldgraphEntity])
def search_entities_endpoint(
    namespace: str,
    q: Annotated[str | None, Query()] = None,
    entity_type: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    db: Session = Depends(get_db),
) -> list[WorldgraphEntity]:
    return store.list_entities(db, namespace=namespace, query_text=q, entity_type=entity_type, limit=limit)

