"""Privacy service application settings."""

from packages.config.base import BaseServiceSettings, build_settings


class Settings(BaseServiceSettings):
    service_name: str = "privacy"

    # Service configuration
    host: str = "0.0.0.0"
    port: int = 3010

    # Privacy tiers and their detection sensitivity
    # dev: basic PII (email, phone)
    # growth: + names, addresses
    # pro: + all entities (SSN, credit cards, etc.)
    default_tier: str = "dev"

    # Token for internal service authentication
    service_token: str | None = None

    # Storage for redaction mappings (in-memory for now, Redis in production)
    # redis_url inherited from BaseServiceSettings

    @property
    def effective_service_token(self) -> str:
        """Get service token with test-mode fallback."""
        if self.service_token:
            return self.service_token
        if self.is_test:
            return "test-privacy-token"
        raise ValueError("SERVICE_TOKEN is required in non-test environments")

    def require_runtime_config(self) -> None:
        """Validate required configuration for non-test environments."""
        if self.is_test:
            return

        missing: list[str] = []

        if not self.service_token:
            missing.append("SERVICE_TOKEN")

        if missing:
            raise ValueError(
                f"Missing required environment variables for {self.service_name}: {', '.join(missing)}"
            )


settings: Settings = build_settings(Settings)  # type: ignore[assignment]
settings.require_runtime_config()
