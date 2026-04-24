"""Print worldgraph migration diagnostics for the active DATABASE_URL."""

from __future__ import annotations

from sqlalchemy import text

from packages.db import get_session_local


def main() -> None:
    db = get_session_local()()
    try:
        revision_rows = db.execute(text("select version_num from alembic_version")).fetchall()
        table_rows = db.execute(
            text(
                """
                select schemaname, tablename
                from pg_tables
                where schemaname = 'worldgraph'
                order by tablename
                """
            )
        ).fetchall()
        ingest_job_count = db.execute(text("select count(*) from worldgraph.wg_ingest_jobs")).scalar_one()

        print("alembic_version=", [row[0] for row in revision_rows])
        print("worldgraph_tables=", [(row[0], row[1]) for row in table_rows])
        print("wg_ingest_jobs_count=", ingest_job_count)
    finally:
        db.close()


if __name__ == "__main__":
    main()
