"""Media & Commerce Service Settings"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Service
    service_name: str = "media-commerce"
    host: str = "0.0.0.0"
    port: int = 8087
    log_level: str = "info"
    
    # Database
    database_url: str = "postgresql://postgres:postgres@postgres:5432/fullstackarkham"
    database_pool_size: int = 10
    
    # Gateway
    gateway_url: str = "http://gateway:8080"

    # Horizontal orchestration
    orchestration_url: str = "http://orchestration:8083"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
