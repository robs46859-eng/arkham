"""
Gateway service settings.
Implements: Build Rules §4 — No untyped environment access.
All config via typed pydantic-settings, sourced from environment / .env file.
"""

from packages.config.base import BaseServiceSettings, build_settings


class Settings(BaseServiceSettings):
    service_name: str = "gateway"

    # Signing key for tenant auth tokens
    # Production: Must be set via environment variable or Secret Manager
    signing_key: str | None = None

    # Admin token — guards /v1/tenants/* routes
    # Production: Must be set via environment variable or Secret Manager
    admin_token: str | None = None
    
    orchestration_url: str = "http://localhost:8002"
    core_service_url: str = "http://core:3000"
    billing_service_url: str = "http://localhost:3020"
    email_provider: str | None = None
    email_from: str | None = None
    email_reply_to: str | None = None
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    automation_dry_run: bool = True

    # Feature flags
    enable_premium_escalation: bool = False
    enable_semantic_cache: bool = False
    enable_privacy_proxy: bool = False
    privacy_restore_responses: bool = True
    privacy_fail_closed: bool = False
    privacy_service_url: str = "http://localhost:3010"
    privacy_service_token: str | None = None
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
    gemini_api_key: str | None = None
    gemini_base_url: str | None = None
    gemini_mid_tier_model: str = "gemini-1.5-flash"
    gemini_premium_model: str = "gemini-1.5-pro"

    # Vector Store / Semantic Cache
    vector_store_path: str = "./.local/lancedb"
    embedding_provider: str = "ollama"  # ollama | openai
    embedding_model: str = "nomic-embed-text"
    cache_threshold: float = 0.85

    @property
    def effective_admin_token(self) -> str:
        """Get admin token with test-mode fallback."""
        if self.admin_token:
            return self.admin_token
        if self.is_test:
            return "test-admin-token-not-for-production"
        raise ValueError("ADMIN_TOKEN is required in non-test environments")

    @property
    def effective_signing_key(self) -> str:
        """Get signing key with test-mode fallback."""
        if self.signing_key:
            return self.signing_key
        if self.is_test:
            return "test-signing-key-not-for-production"
        raise ValueError("SIGNING_KEY is required in non-test environments")

    @property
    def effective_privacy_service_token(self) -> str:
        """Get privacy service token with test-mode fallback."""
        if self.privacy_service_token:
            return self.privacy_service_token
        if self.is_test:
            return "test-privacy-token"
        raise ValueError("PRIVACY_SERVICE_TOKEN is required in non-test environments")

    def require_runtime_config(self) -> None:
        """Validate required configuration for non-test environments."""
        if self.is_test:
            return

        missing: list[str] = []

        if not self.signing_key:
            missing.append("SIGNING_KEY")
        if not self.admin_token:
            missing.append("ADMIN_TOKEN")
        if not self.privacy_service_token:
            missing.append("PRIVACY_SERVICE_TOKEN")

        if missing:
            raise ValueError(
                f"Missing required environment variables for {self.service_name}: {', '.join(missing)}"
            )


settings: Settings = build_settings(Settings)  # type: ignore[assignment]
settings.require_runtime_config()
