"""Semantic Cache Service Settings"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Service
    service_name: str = "semantic-cache"
    host: str = "0.0.0.0"
    port: int = 8084
    log_level: str = "info"
    
    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/fullstackarkham"
    database_pool_size: int = 10
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # Embeddings
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384
    
    # Cache
    default_threshold: float = 0.90
    cache_ttl_days: int = 30
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
