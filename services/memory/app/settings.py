"""Memory Service Settings"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Service
    service_name: str = "memory"
    host: str = "0.0.0.0"
    port: int = 8085
    log_level: str = "info"
    
    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/fullstackarkham"
    database_pool_size: int = 10
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # Embeddings
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384
    
    # Memory decay
    default_decay_rate: float = 0.01
    min_importance: float = 0.1
    max_importance: float = 1.0
    
    # Retrieval
    default_max_results: int = 10
    similarity_threshold: float = 0.7
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
