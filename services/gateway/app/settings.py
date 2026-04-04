import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    service_name: str = os.getenv("SERVICE_NAME", "robco-gateway")
    app_env: str = os.getenv("APP_ENV", "development")
    database_url: str = os.getenv("DATABASE_URL", "postgresql://robco:password@postgres:5432/robco_db")
    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
