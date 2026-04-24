"""Redis-driven worker for ingest and reindex jobs."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from packages.db import transactional_session

from ..services import events
from ..services import openflights
from ..services import queue
from ..services import raw_bucket
from ..services import store

logger = logging.getLogger("worldgraph.worker")


class WorldgraphWorker:
    def __init__(self, poll_seconds: float = 1.0):
        self.poll_seconds = poll_seconds
        self.running = True

    async def run(self) -> None:
        logger.info("WorldgraphWorker starting")
        while self.running:
            try:
                item = queue.pop_job(timeout_seconds=2)
                if item is None:
                    await asyncio.sleep(self.poll_seconds)
                    continue
                await self._dispatch(item)
            except Exception:
                logger.exception("Worldgraph worker loop failed")
                await asyncio.sleep(self.poll_seconds)

    async def _dispatch(self, item: dict[str, Any]) -> None:
        job_type = item.get("job_type")
        payload = item.get("payload", {})
        if job_type == "ingest_openflights":
            await self._run_ingest_openflights(payload)
            return
        if job_type == "reindex_travel":
            await self._run_reindex(payload)
            return
        logger.warning("Unknown worldgraph job type: %s", job_type)

    async def _run_ingest_openflights(self, payload: dict[str, Any]) -> None:
        job_id = str(payload.get("job_id"))
        with transactional_session() as db:
            store.set_ingest_job_running(db, job_id)
        try:
            logger.info(
                "Fetching OpenFlights snapshot mode=%s timeout_seconds=%s",
                openflights.settings.openflights_source_mode,
                openflights.settings.openflights_fetch_timeout_seconds,
            )
            snapshot = await openflights.get_openflights_snapshot()
            uploaded: dict[str, dict[str, Any]] = {}

            with transactional_session() as db:
                for filename, content in snapshot.items():
                    uri, checksum = raw_bucket.upload_raw_blob("travel", "openflights", filename, content)
                    raw_obj = store.register_raw_object(
                        db,
                        namespace="travel",
                        source_name="openflights",
                        object_uri=uri,
                        checksum_sha256=checksum,
                        content_type="text/plain",
                        metadata_json={"filename": filename},
                    )
                    uploaded[filename] = {
                        "uri": uri,
                        "checksum_sha256": checksum,
                        "raw_object_id": raw_obj.raw_object_id,
                        "size_bytes": len(content.encode("utf-8")),
                    }

                airports = openflights.parse_airports(snapshot["airports.dat"])
                airlines = openflights.parse_airlines(snapshot["airlines.dat"])
                routes = openflights.parse_routes(snapshot["routes.dat"])

                for airport in airports:
                    store.stage_openflights_airport(
                        db,
                        job_id=job_id,
                        raw_object_id=uploaded["airports.dat"]["raw_object_id"],
                        payload=airport,
                    )
                for airline in airlines:
                    store.stage_openflights_airline(
                        db,
                        job_id=job_id,
                        raw_object_id=uploaded["airlines.dat"]["raw_object_id"],
                        payload=airline,
                    )
                for route in routes:
                    store.stage_openflights_route(
                        db,
                        job_id=job_id,
                        raw_object_id=uploaded["routes.dat"]["raw_object_id"],
                        payload=route,
                    )

                manifest = {
                    "job_id": job_id,
                    "namespace": "travel",
                    "source_name": "openflights",
                    "uploaded_objects": uploaded,
                    "row_counts": {
                        "airports": len(airports),
                        "airlines": len(airlines),
                        "routes": len(routes),
                    },
                }
                manifest_uri = raw_bucket.upload_manifest("travel", "openflights", manifest)
                store.set_ingest_job_completed(
                    db,
                    job_id,
                    manifest_uri=manifest_uri,
                    stats_json=manifest["row_counts"],
                )

            await events.publish_event(
                "worldgraph.travel.ingest.completed",
                {
                    "job_id": job_id,
                    "source": "openflights",
                    "manifest_uri": manifest_uri,
                    "ingest_mode": "trusted_seed_l2",
                },
            )
            # v1 boundary: OpenFlights ingest is trusted Layer 2 seeding.
            # Normalization proposals are not in the control path yet.
            queue.enqueue_job("reindex_travel", {"job_id": job_id, "namespace": "travel"})
        except Exception as exc:
            with transactional_session() as db:
                store.set_ingest_job_failed(db, job_id, error=str(exc))
            raise

    async def _run_reindex(self, payload: dict[str, Any]) -> None:
        namespace = str(payload.get("namespace", "travel"))
        with transactional_session() as db:
            count = store.refresh_search_documents(db, namespace=namespace)
        await events.publish_event(
            "worldgraph.travel.reindex.completed",
            {"namespace": namespace, "entity_count": count},
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(WorldgraphWorker().run())

