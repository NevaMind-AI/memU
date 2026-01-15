"""
Engram Storage Base Classes

This module defines the abstract interface for Engram embedding storage backends.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np


class EmbeddingStorage(ABC):
    """Abstract base class for embedding storage backends.
    
    This interface defines the contract for storing and retrieving
    large embedding tables with different persistence strategies.
    """
    
    @abstractmethod
    def store(self, embeddings: np.ndarray) -> None:
        """Store embeddings to the backend (replace entire table).
        
        Args:
            embeddings: Full embedding table to store
        """
        pass
    
    @abstractmethod
    def load(self, indices: np.ndarray) -> np.ndarray:
        """Load embeddings by indices with O(1) complexity.
        
        Args:
            indices: Indices to load
            
        Returns:
            Embeddings at specified indices
        """
        pass
    
    @abstractmethod
    def load_all(self) -> np.ndarray:
        """Load all embeddings from storage.
        
        Returns:
            Full embedding table
        """
        pass
    
    @abstractmethod
    def update(self, indices: np.ndarray, embeddings: np.ndarray) -> None:
        """Update specific embeddings in place.
        
        Args:
            indices: Indices to update
            embeddings: New embedding values
        """
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Close the storage and release resources."""
        pass
    
    @property
    @abstractmethod
    def shape(self) -> tuple[int, int]:
        """Get shape of the embedding table.
        
        Returns:
            Tuple of (num_embeddings, embedding_dim)
        """
        pass


__all__ = ["EmbeddingStorage"]
