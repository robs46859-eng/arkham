"""Probe outbound reachability for OpenFlights fetch path."""

from __future__ import annotations

import asyncio
from urllib.parse import urlparse

from services.worldgraph.app.services import openflights
from services.worldgraph.app.settings import settings


async def main() -> None:
    host = urlparse(openflights.OPENFLIGHTS_AIRPORTS_URL).hostname or "raw.githubusercontent.com"
    print("openflights_url=", openflights.OPENFLIGHTS_AIRPORTS_URL)
    print("openflights_source_mode=", settings.openflights_source_mode)
    print("openflights_fetch_timeout_seconds=", settings.openflights_fetch_timeout_seconds)
    diagnostics = openflights.diagnose_host_reachability(
        host=host,
        port=443,
        timeout_seconds=settings.openflights_fetch_timeout_seconds,
    )
    print("reachability=", diagnostics)
    try:
        snapshot = await openflights.fetch_openflights_snapshot(settings.openflights_fetch_timeout_seconds)
        print("fetch_status=ok")
        print("snapshot_sizes=", {name: len(content) for name, content in snapshot.items()})
    except Exception as exc:
        print("fetch_status=error")
        print("fetch_error=", repr(exc))
        raise


if __name__ == "__main__":
    asyncio.run(main())
