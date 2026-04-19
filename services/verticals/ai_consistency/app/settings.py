from packages.config.base import BaseServiceSettings, build_settings


class Settings(BaseServiceSettings):
    """AI Consistency Lab Settings."""

    gateway_service_url: str = "http://gateway:8000"


get_settings = build_settings(Settings)
