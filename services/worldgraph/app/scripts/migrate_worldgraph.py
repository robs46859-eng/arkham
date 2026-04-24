"""Run targeted worldgraph migration DDL without relying on alembic env config."""

from __future__ import annotations

from packages.db import get_session_local

from services.worldgraph.app.services.schema_init import ensure_worldgraph_schema


def main() -> None:
    db = get_session_local()()
    try:
        ensure_worldgraph_schema(db)
        print("worldgraph_schema_bootstrap=ok")
    finally:
        db.close()


if __name__ == "__main__":
    main()

