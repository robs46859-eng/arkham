"""Query smoke verification checkpoints for worldgraph travel ingest."""

from __future__ import annotations

from packages.db import get_session_local
from packages.models import (
    WorldgraphEntityRecord,
    WorldgraphIngestJobRecord,
    WorldgraphRawObjectRecord,
    WorldgraphRawRecordRecord,
    WorldgraphSearchDocumentRecord,
)
from services.worldgraph.app.services import store


def main() -> None:
    db = get_session_local()()
    try:
        jobs = (
            db.query(WorldgraphIngestJobRecord)
            .filter(WorldgraphIngestJobRecord.namespace == "travel")
            .filter(WorldgraphIngestJobRecord.source_name == "openflights")
            .order_by(WorldgraphIngestJobRecord.started_at.desc())
            .limit(5)
            .all()
        )
        print("jobs=", [(j.job_id, j.status, str(j.finished_at)) for j in jobs])
        print("raw_objects=", db.query(WorldgraphRawObjectRecord).count())
        print("raw_records=", db.query(WorldgraphRawRecordRecord).count())
        print(
            "entities_total=",
            db.query(WorldgraphEntityRecord)
            .filter(WorldgraphEntityRecord.namespace == "travel")
            .count(),
        )
        print(
            "entities_airports=",
            db.query(WorldgraphEntityRecord)
            .filter(WorldgraphEntityRecord.namespace == "travel")
            .filter(WorldgraphEntityRecord.entity_type == "airport")
            .count(),
        )
        print(
            "entities_airlines=",
            db.query(WorldgraphEntityRecord)
            .filter(WorldgraphEntityRecord.namespace == "travel")
            .filter(WorldgraphEntityRecord.entity_type == "airline")
            .count(),
        )
        print(
            "entities_routes=",
            db.query(WorldgraphEntityRecord)
            .filter(WorldgraphEntityRecord.namespace == "travel")
            .filter(WorldgraphEntityRecord.entity_type == "route")
            .count(),
        )
        print("search_docs=", db.query(WorldgraphSearchDocumentRecord).count())
        delta = store.list_entities(db, namespace="travel", query_text="delta", entity_type=None, limit=10)
        print("search_delta_count=", len(delta))
        print("search_delta_first=", delta[0].display_name if delta else None)
    finally:
        db.close()


if __name__ == "__main__":
    main()

