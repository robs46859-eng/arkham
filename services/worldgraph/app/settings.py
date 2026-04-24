"""Worldgraph service settings."""

from packages.config.base import BaseServiceSettings, build_settings


class Settings(BaseServiceSettings):
    service_name: str = "worldgraph"
    host: str = "0.0.0.0"
    port: int = 8050

    core_service_url: str = "http://core:3000"
    raw_bucket_name: str = "arkham-worldgraph-raw"
    redis_queue_key: str = "worldgraph:jobs"
    openflights_source_mode: str = "http"
    openflights_fetch_timeout_seconds: float = 60.0
    openflights_fixture_dir: str = "/app/services/worldgraph/app/fixtures/openflights"
    openflights_gcs_prefix: str | None = None

    enable_travel_auto_promotion: bool = True
    travel_auto_promotion_threshold: float = 0.9
    property_requires_human_approval: bool = True

    ollama_host: str = "http://localhost:11434"
    local_normalizer_model: str = "qwen2.5:7b"
    local_dedupe_model: str = "llama3.1:8b"
    openai_api_key: str | None = None
    openai_fallback_model: str = "gpt-4o-mini"

    embedding_provider: str = "ollama"
    embedding_model: str = "nomic-embed-text"
    embedding_version: str = "travel-v1"
    semantic_similarity_threshold: float = 0.85
    dedupe_candidate_threshold: float = 0.8


settings: Settings = build_settings(Settings)  # type: ignore[assignment]

