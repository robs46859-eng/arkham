"""OpenFlights source ingestion helpers."""

from __future__ import annotations

import csv
import socket
from io import StringIO
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from google.cloud import storage

from ..settings import settings

OPENFLIGHTS_AIRPORTS_URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat"
OPENFLIGHTS_AIRLINES_URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airlines.dat"
OPENFLIGHTS_ROUTES_URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/routes.dat"
OPENFLIGHTS_FILES = ("airports.dat", "airlines.dat", "routes.dat")


def _parse_float(raw: str) -> float | None:
    if raw in ("", "\\N"):
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _parse_int(raw: str) -> int | None:
    if raw in ("", "\\N"):
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _read_csv(content: str) -> list[list[str]]:
    reader = csv.reader(StringIO(content))
    return [row for row in reader]


async def fetch_openflights_snapshot(timeout_seconds: float = 60.0) -> dict[str, str]:
    timeout = httpx.Timeout(timeout_seconds)
    url_map = {
        "airports.dat": OPENFLIGHTS_AIRPORTS_URL,
        "airlines.dat": OPENFLIGHTS_AIRLINES_URL,
        "routes.dat": OPENFLIGHTS_ROUTES_URL,
    }
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            responses: dict[str, httpx.Response] = {}
            for filename, url in url_map.items():
                responses[filename] = await client.get(url)
        for response in responses.values():
            response.raise_for_status()
        return {filename: responses[filename].text for filename in OPENFLIGHTS_FILES}
    except Exception:
        host = urlparse(OPENFLIGHTS_AIRPORTS_URL).hostname or "raw.githubusercontent.com"
        diagnosis = diagnose_host_reachability(host=host, port=443, timeout_seconds=timeout_seconds)
        raise RuntimeError(
            "OpenFlights fetch failed"
            f" host={host}"
            f" timeout_seconds={timeout_seconds}"
            f" urls={url_map}"
            f" diagnosis={diagnosis}"
        ) from None


def load_fixture_snapshot(fixture_dir: str | Path) -> dict[str, str]:
    base = Path(fixture_dir)
    snapshot: dict[str, str] = {}
    for filename in OPENFLIGHTS_FILES:
        snapshot[filename] = (base / filename).read_text(encoding="utf-8")
    return snapshot


def load_gcs_snapshot(prefix: str) -> dict[str, str]:
    if not prefix.startswith("gs://"):
        raise ValueError("openflights_gcs_prefix must start with gs://")
    without_scheme = prefix.removeprefix("gs://").strip("/")
    if "/" not in without_scheme:
        raise ValueError("openflights_gcs_prefix must include bucket and path")
    bucket_name, object_prefix = without_scheme.split("/", 1)
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    snapshot: dict[str, str] = {}
    for filename in OPENFLIGHTS_FILES:
        blob = bucket.blob(f"{object_prefix}/{filename}")
        snapshot[filename] = blob.download_as_text()
    return snapshot


def diagnose_host_reachability(host: str, port: int = 443, timeout_seconds: float = 10.0) -> dict[str, Any]:
    diagnostics: dict[str, Any] = {"host": host, "port": port, "timeout_seconds": timeout_seconds}
    try:
        addrinfo = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
        ips = sorted({item[4][0] for item in addrinfo})
        diagnostics["dns"] = {"ok": True, "ip_count": len(ips), "ips": ips[:5]}
    except Exception as exc:
        diagnostics["dns"] = {"ok": False, "error": repr(exc)}
        return diagnostics

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout_seconds)
    try:
        sock.connect((host, port))
        diagnostics["tcp"] = {"ok": True}
    except Exception as exc:
        diagnostics["tcp"] = {"ok": False, "error": repr(exc)}
        return diagnostics
    finally:
        sock.close()

    try:
        response = httpx.get(
            f"https://{host}/",
            timeout=httpx.Timeout(timeout_seconds),
            follow_redirects=False,
        )
        diagnostics["https"] = {
            "ok": True,
            "status_code": response.status_code,
            "server": response.headers.get("server"),
        }
    except Exception as exc:
        diagnostics["https"] = {"ok": False, "error": repr(exc)}
    return diagnostics


async def get_openflights_snapshot() -> dict[str, str]:
    mode = settings.openflights_source_mode.lower().strip()
    if mode == "http":
        return await fetch_openflights_snapshot(timeout_seconds=settings.openflights_fetch_timeout_seconds)
    if mode == "fixture":
        return load_fixture_snapshot(settings.openflights_fixture_dir)
    if mode == "gcs":
        if not settings.openflights_gcs_prefix:
            raise RuntimeError("openflights_gcs_prefix is required when openflights_source_mode=gcs")
        return load_gcs_snapshot(settings.openflights_gcs_prefix)
    raise RuntimeError(f"Unsupported openflights_source_mode={settings.openflights_source_mode}")


def parse_airports(content: str) -> list[dict[str, Any]]:
    rows = _read_csv(content)
    out: list[dict[str, Any]] = []
    for row in rows:
        if len(row) < 14:
            continue
        out.append(
            {
                "airport_id": row[0],
                "name": row[1],
                "city": row[2],
                "country": row[3],
                "iata": row[4],
                "icao": row[5],
                "latitude": _parse_float(row[6]),
                "longitude": _parse_float(row[7]),
                "altitude_ft": _parse_float(row[8]),
                "timezone_offset": _parse_float(row[9]),
                "dst": row[10],
                "tz_database": row[11],
                "airport_type": row[12],
                "source": row[13],
            }
        )
    return out


def parse_airlines(content: str) -> list[dict[str, Any]]:
    rows = _read_csv(content)
    out: list[dict[str, Any]] = []
    for row in rows:
        if len(row) < 8:
            continue
        out.append(
            {
                "airline_id": row[0],
                "name": row[1],
                "alias": row[2],
                "iata": row[3],
                "icao": row[4],
                "callsign": row[5],
                "country": row[6],
                "active": row[7],
            }
        )
    return out


def parse_routes(content: str) -> list[dict[str, Any]]:
    rows = _read_csv(content)
    out: list[dict[str, Any]] = []
    for row in rows:
        if len(row) < 9:
            continue
        route_key = f"{row[2]}:{row[4]}:{row[6]}:{row[0]}"
        out.append(
            {
                "airline_code": row[0],
                "airline_id": row[1],
                "source_airport": row[2],
                "source_airport_id": row[3],
                "destination_airport": row[4],
                "destination_airport_id": row[5],
                "codeshare": row[6],
                "stops": _parse_int(row[7]),
                "equipment": row[8] if len(row) > 8 else None,
                "route_key": route_key,
            }
        )
    return out

