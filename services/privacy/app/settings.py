"""Privacy service application settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "privacy"
    app_env: str = "development"
    
    # Service configuration
    host: str = "0.0.0.0"
    port: int = 3010
    
    # Privacy tiers and their detection sensitivity
    # dev: basic PII (email, phone)
    # growth: + names, addresses
    # pro: + all entities (SSN, credit cards, etc.)
    default_tier: str = "dev"
    
    # Token for internal service authentication
    service_token: str = "privacy-core-internal-token"
    
    # Storage for redaction mappings (in-memory for now, Redis in production)
    redis_url: str | None = None
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


settings: Settings = Settings()
