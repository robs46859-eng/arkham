"""
BIM Ingestion service settings.
Implements: Build Rules §4 — No untyped environment access.
"""

from packages.config.base import BaseServiceSettings, build_settings


class Settings(BaseServiceSettings):
    service_name: str = "bim-ingestion"

    # Object storage (MinIO / S3-compatible)
    storage_endpoint: str = "http://localhost:9000"
    storage_access_key: str = "robco"
    storage_secret_key: str = "password123"
    storage_bucket: str = "bim-files"

    # File ingestion limits
    max_file_size_mb: int = 500


settings: Settings = build_settings(Settings)  # type: ignore[assignment]
