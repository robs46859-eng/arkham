"""
Gateway service settings.
Implements: Build Rules §4 — No untyped environment access.
All config via typed pydantic-settings, sourced from environment / .env file.
"""

from packages.config.base import BaseServiceSettings, build_settings


class Settings(BaseServiceSettings):
    service_name: str = "gateway"

    # Signing key for tenant auth tokens (stub — replace with real secret in production)
    signing_key: str = "changeme"
    orchestration_url: str = "http://localhost:8002"

    # Feature flags
    enable_premium_escalation: bool = False
    enable_semantic_cache: bool = False
    enable_privacy_proxy: bool = False
    privacy_restore_responses: bool = True
    privacy_fail_closed: bool = False
    privacy_service_url: str = "http://localhost:3010"
    privacy_service_token: str = "privacy-core-internal-token"
    privacy_default_tier: str = "dev"

    # Local Model Runtime (Ollama)
    ollama_host: str = "http://localhost:11434"
    local_router_model: str = "qwen2.5:7b"
    local_classifier_model: str = "qwen2.5:3b"
    local_summary_model: str = "qwen2.5:7b"
    local_extraction_model: str = "qwen2.5:7b"

    # External Model Providers
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_mid_tier_model: str = "gpt-4o-mini"
    openai_premium_model: str = "gpt-4o"

    # Vector Store / Semantic Cache
    vector_store_path: str = "./.local/lancedb"
    embedding_provider: str = "ollama"  # ollama | openai
    embedding_model: str = "nomic-embed-text"
    cache_threshold: float = 0.85


settings: Settings = build_settings(Settings)  # type: ignore[assignment]
