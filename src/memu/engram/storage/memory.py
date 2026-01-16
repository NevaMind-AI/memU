"""
In-Memory Storage Backend for Engram

Provides fast in-memory storage for embedding tables with various
initialization strategies.
"""

from __future__ import annotations

import logging

import numpy as np

from memu.engram.storage.base import EmbeddingStorage

logger = logging.getLogger(__name__)


class InMemoryStorage(EmbeddingStorage):
    """In-memory embedding storage for maximum speed.
    
    This backend keeps the entire embedding table in RAM for
    O(1) access with minimal latency. Best for small to medium
    sized tables where memory is not a constraint.
    """
    
    def __init__(
        self,
        num_embeddings: int,
        embedding_dim: int,
        dtype: np.dtype = np.float32,
        init_method: str = "normal",
        init_scale: float = 0.02,
    ) -> None:
        """Initialize in-memory storage.
        
        Args:
            num_embeddings: Number of embeddings to store
            embedding_dim: Dimension of each embedding
            dtype: Data type for storage (default: float32)
            init_method: Initialization method ('normal', 'uniform', 'xavier', 'kaiming', 'zeros')
            init_scale: Scale factor for initialization
        """
        self._num_embeddings = num_embeddings
        self._embedding_dim = embedding_dim
        self._dtype = dtype
        
        # Initialize embeddings
        self._embeddings = self._initialize(init_method, init_scale)
        logger.info(
            f"Initialized InMemoryStorage: {num_embeddings} x {embedding_dim}, "
            f"dtype={dtype}, size={self._embeddings.nbytes / 1e6:.2f} MB"
        )
    
    def _initialize(self, method: str, scale: float) -> np.ndarray:
        """Initialize embedding values.
        
        Args:
            method: Initialization method
            scale: Scale factor
            
        Returns:
            Initialized embedding array
        """
        shape = (self._num_embeddings, self._embedding_dim)
        
        if method == "normal":
            # Normal distribution with specified scale
            data = np.random.randn(*shape).astype(np.float32) * scale
        elif method == "uniform":
            # Uniform distribution in [-scale, scale]
            data = np.random.uniform(-scale, scale, shape).astype(np.float32)
        elif method == "xavier":
            # Xavier/Glorot initialization
            fan = self._embedding_dim
            bound = np.sqrt(6.0 / fan)
            data = np.random.uniform(-bound, bound, shape).astype(np.float32)
        elif method == "kaiming":
            # Kaiming/He initialization
            std = np.sqrt(2.0 / self._embedding_dim)
            data = np.random.randn(*shape).astype(np.float32) * std
        elif method == "zeros":
            # Zero initialization
            data = np.zeros(shape, dtype=np.float32)
        else:
            raise ValueError(f"Unknown initialization method: {method}")
        
        return data.astype(self._dtype)
    
    def store(self, embeddings: np.ndarray) -> None:
        """Store embeddings (replace entire table).
        
        Args:
            embeddings: Full embedding table to store
        """
        if embeddings.shape != self._embeddings.shape:
            raise ValueError(
                f"Shape mismatch: expected {self._embeddings.shape}, "
                f"got {embeddings.shape}"
            )
        self._embeddings = embeddings.astype(self._dtype)
    
    def load(self, indices: np.ndarray) -> np.ndarray:
        """Load embeddings by indices.
        
        Args:
            indices: Indices to load
            
        Returns:
            Embeddings at specified indices
        """
        return self._embeddings[indices]
    
    def load_all(self) -> np.ndarray:
        """Load all embeddings.
        
        Returns:
            Full embedding table
        """
        return self._embeddings
    
    def update(self, indices: np.ndarray, embeddings: np.ndarray) -> None:
        """Update specific embeddings.
        
        Args:
            indices: Indices to update
            embeddings: New embedding values
        """
        self._embeddings[indices] = embeddings.astype(self._dtype)
    
    def close(self) -> None:
        """Release memory."""
        del self._embeddings
    
    @property
    def shape(self) -> tuple[int, int]:
        """Get shape of the embedding table.
        
        Returns:
            Tuple of (num_embeddings, embedding_dim)
        """
        return (self._num_embeddings, self._embedding_dim)


__all__ = ["InMemoryStorage"]
