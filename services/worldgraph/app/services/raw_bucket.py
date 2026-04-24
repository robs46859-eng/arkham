"""GCS raw object storage helpers for worldgraph."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from google.cloud import storage

from ..settings import settings


def _storage_client() -> storage.Client:
    return storage.Client()


def upload_raw_blob(namespace: str, source_name: str, filename: str, content: str) -> tuple[str, str]:
    checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()
    client = _storage_client()
    bucket = client.bucket(settings.raw_bucket_name)
    object_path = f"{namespace}/{source_name}/{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}/{filename}"
    blob = bucket.blob(object_path)
    blob.upload_from_string(content, content_type="text/plain")
    return f"gs://{settings.raw_bucket_name}/{object_path}", checksum


def upload_manifest(namespace: str, source_name: str, payload: dict[str, Any]) -> str:
    client = _storage_client()
    bucket = client.bucket(settings.raw_bucket_name)
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    object_path = f"{namespace}/{source_name}/manifests/{ts}.json"
    blob = bucket.blob(object_path)
    blob.upload_from_string(json.dumps(payload, default=str), content_type="application/json")
    return f"gs://{settings.raw_bucket_name}/{object_path}"

