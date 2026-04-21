"""Arkham governance service settings."""
from packages.config.base import BaseServiceSettings, build_settings


class Settings(BaseServiceSettings):
    service_name: str = "arkham"

    # Redis not used by arkham — provide a default so BaseServiceSettings is satisfied
    redis_url: str = "redis://localhost:6379"

    sidecar_service_token: str | None = None
    bloods_enabled: bool = True
    bloods_vault_key: str | None = None
    shadow_mode: bool = True


settings: Settings = build_settings(Settings)  # type: ignore[assignment]
