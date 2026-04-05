"""Core service application settings."""

from packages.config.base import BaseServiceSettings, build_settings


class Settings(BaseServiceSettings):
    service_name: str = "core"

    # Service configuration
    host: str = "0.0.0.0"
    port: int = 3000

    # Registry and event bus configuration
    registry_ttl: int = 30  # seconds

    # redis_url inherited from BaseServiceSettings

    @property
    def effective_redis_url(self) -> str:
        """Get Redis URL with test-mode fallback."""
        if self.redis_url:
            return self.redis_url
        if self.is_test:
            return "redis://localhost:6379/0"
        raise ValueError("REDIS_URL is required in non-test environments")

    def require_runtime_config(self) -> None:
        """Validate required configuration for non-test environments."""
        if self.is_test:
            return

        missing: list[str] = []

        if not self.redis_url:
            missing.append("REDIS_URL")

        if missing:
            raise ValueError(
                f"Missing required environment variables for {self.service_name}: {', '.join(missing)}"
            )


settings: Settings = build_settings(Settings)  # type: ignore[assignment]
settings.require_runtime_config()
