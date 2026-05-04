"""
Embedding Service

Generates embeddings for semantic cache lookup.
Uses sentence transformers for local embedding generation.
"""

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Local embedding generation using sentence transformers"""
    
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or "all-MiniLM-L6-v2"
        self.model = None
        self._initialized = False
    
    def _ensure_initialized(self):
        """Lazy initialization of the model"""
        if self._initialized:
            return
        
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name)
            logger.info(f"Loaded embedding model: {self.model_name}")
        except ImportError:
            logger.warning("sentence-transformers not available, using mock embeddings")
            self.model = None
        
        self._initialized = True
    
    async def embed(self, text: str) -> List[float]:
        """
        Generate embedding for text
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding
        """
        self._ensure_initialized()
        
        if self.model is None:
            # Return mock embedding for testing
            return self._mock_embed(text)
        
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    async def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 32,
    ) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        self._ensure_initialized()
        
        if self.model is None:
            return [self._mock_embed(t) for t in texts]
        
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            show_progress_bar=len(texts) > 10,
        )
        
        return embeddings.tolist()
    
    def _mock_embed(self, text: str) -> List[float]:
        """Generate a deterministic mock embedding"""
        # Simple hash-based mock embedding for testing
        import hashlib
        
        embedding_dim = 384
        hash_bytes = hashlib.sha256(text.encode()).digest()
        
        # Expand hash to embedding dimension
        embedding = []
        for i in range(embedding_dim):
            byte_idx = i % len(hash_bytes)
            # Normalize to [-1, 1] range
            value = (hash_bytes[byte_idx] / 127.5) - 1.0
            embedding.append(float(value))
        
        # Normalize
        norm = sum(x * x for x in embedding) ** 0.5
        if norm > 0:
            embedding = [x / norm for x in embedding]
        
        return embedding
