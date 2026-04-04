from packages.config.base import BaseServiceSettings, build_settings


class Settings(BaseServiceSettings):
    service_name: str = "bim-ingestion"


settings = build_settings(Settings)
