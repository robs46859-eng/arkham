from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseServiceSettings(BaseSettings):
    """Common typed settings used by bootable FastAPI services."""

    service_name: str
    app_env: str = "development"
    database_url: str
    redis_url: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


def build_settings(settings_cls: type[BaseServiceSettings]) -> BaseServiceSettings:
    @lru_cache(maxsize=1)
    def _load() -> BaseServiceSettings:
        return settings_cls()

    return _load()
