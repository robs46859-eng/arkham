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

    # Feature flags
    enable_premium_escalation: bool = False
    enable_semantic_cache: bool = False


settings: Settings = build_settings(Settings)  # type: ignore[assignment]
