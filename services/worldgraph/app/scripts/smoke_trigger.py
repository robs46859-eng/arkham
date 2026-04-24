"""Queue an OpenFlights ingest job for staging smoke tests."""

from __future__ import annotations

from packages.db import get_session_local

from services.worldgraph.app.services import queue, store


def main() -> None:
    db = get_session_local()()
    try:
        job = store.create_ingest_job(db, namespace="travel", source_name="openflights")
        queue.enqueue_job(
            "ingest_openflights",
            {"job_id": job.job_id, "namespace": "travel", "source_name": "openflights"},
        )
        print(f"triggered_job_id={job.job_id}")
    finally:
        db.close()


if __name__ == "__main__":
    main()

