from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    service_name: str = "robco-core"
    app_env: str = "development"
    redis_url: str = "redis://redis:6379/0"
    registry_ttl: int = 30  # seconds
    
    class Config:
        env_file = ".env"


settings = Settings()
