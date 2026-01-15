"""
Hybrid Storage Backend for Engram

Combines hot in-memory cache with cold disk storage using LRU eviction.
"""

from __future__ import annotations

import logging
import threading
from collections import OrderedDict
from pathlib import Path
from typing import Any

import numpy as np

from memu.engram.storage.base import EmbeddingStorage
from memu.engram.storage.mmap import MMapStorage

logger = logging.getLogger(__name__)


class HybridStorage(EmbeddingStorage):
    """Hybrid storage with hot cache and cold storage.
    
    This backend provides a balance between speed and memory efficiency:
    - Hot cache: Frequently accessed embeddings in RAM (fast)
    - Cold storage: Full table on disk via mmap (persistent)
    - LRU eviction: Automatic cache management
    
    Use when:
    - Embedding table is too large for full in-memory storage
    - Access patterns show locality (some embeddings accessed frequently)
    - Need persistence without sacrificing too much performance
    """
    
    def __init__(
        self,
        path: Path | str,
        num_embeddings: int,
        embedding_dim: int,
        hot_cache_size: int = 100000,
        dtype: np.dtype = np.float32,
        init_method: str = "normal",
        init_scale: float = 0.02,
    ) -> None:
        """Initialize hybrid storage.
        
        Args:
            path: Path to cold storage file
            num_embeddings: Total number of embeddings
            embedding_dim: Embedding dimension
            hot_cache_size: Maximum number of embeddings in hot cache
            dtype: Data type for storage
            init_method: Initialization method
            init_scale: Scale factor for initialization
        """
        self._hot_cache_size = hot_cache_size
        self._dtype = dtype
        
        # Cold storage (disk-backed mmap)
        self._cold = MMapStorage(
            path=path,
            num_embeddings=num_embeddings,
            embedding_dim=embedding_dim,
            dtype=dtype,
            mode="w+",
            init_method=init_method,
            init_scale=init_scale,
        )
        
        # Hot cache (memory) with LRU eviction
        self._hot_cache: OrderedDict[int, np.ndarray] = OrderedDict()
        self._cache_lock = threading.Lock()
        
        # Statistics
        self._hits = 0
        self._misses = 0
        
        logger.info(
            f"Initialized HybridStorage: {num_embeddings} embeddings, "
            f"hot_cache_size={hot_cache_size}"
        )
    
    def _get_from_cache(self, idx: int) -> np.ndarray | None:
        """Get embedding from hot cache.
        
        Args:
            idx: Embedding index
            
        Returns:
            Cached embedding or None if not in cache
        """
        with self._cache_lock:
            if idx in self._hot_cache:
                # Move to end (most recently used)
                self._hot_cache.move_to_end(idx)
                self._hits += 1
                return self._hot_cache[idx]
            self._misses += 1
            return None
    
    def _add_to_cache(self, idx: int, embedding: np.ndarray) -> None:
        """Add embedding to hot cache with LRU eviction.
        
        Args:
            idx: Embedding index
            embedding: Embedding to cache
        """
        with self._cache_lock:
            if idx in self._hot_cache:
                self._hot_cache.move_to_end(idx)
                return
            
            # Evict least recently used if cache is full
            while len(self._hot_cache) >= self._hot_cache_size:
                self._hot_cache.popitem(last=False)
            
            self._hot_cache[idx] = embedding.copy()
    
    def store(self, embeddings: np.ndarray) -> None:
        """Store embeddings to cold storage.
        
        Args:
            embeddings: Full embedding table to store
        """
        self._cold.store(embeddings)
        # Clear hot cache as data changed
        with self._cache_lock:
            self._hot_cache.clear()
    
    def load(self, indices: np.ndarray) -> np.ndarray:
        """Load embeddings with caching.
        
        Checks hot cache first, then loads from cold storage
        and populates cache for future access.
        
        Args:
            indices: Indices to load
            
        Returns:
            Embeddings at specified indices
        """
        indices = np.asarray(indices).flatten()
        result = np.zeros((len(indices), self._cold.shape[1]), dtype=self._dtype)
        
        # Check cache first
        cold_indices = []
        cold_positions = []
        
        for i, idx in enumerate(indices):
            cached = self._get_from_cache(int(idx))
            if cached is not None:
                result[i] = cached
            else:
                cold_indices.append(idx)
                cold_positions.append(i)
        
        # Load from cold storage if needed
        if cold_indices:
            cold_data = self._cold.load(np.array(cold_indices))
            for i, (pos, idx) in enumerate(zip(cold_positions, cold_indices)):
                result[pos] = cold_data[i]
                self._add_to_cache(int(idx), cold_data[i])
        
        return result
    
    def load_all(self) -> np.ndarray:
        """Load all embeddings from cold storage.
        
        Returns:
            Full embedding table
        """
        return self._cold.load_all()
    
    def update(self, indices: np.ndarray, embeddings: np.ndarray) -> None:
        """Update embeddings in both cache and cold storage.
        
        Args:
            indices: Indices to update
            embeddings: New embedding values
        """
        self._cold.update(indices, embeddings)
        
        # Update cache
        with self._cache_lock:
            for i, idx in enumerate(indices.flatten()):
                if int(idx) in self._hot_cache:
                    self._hot_cache[int(idx)] = embeddings[i].copy()
    
    def close(self) -> None:
        """Close storage and release resources."""
        self._cold.close()
        with self._cache_lock:
            self._hot_cache.clear()
    
    @property
    def shape(self) -> tuple[int, int]:
        """Get shape of the embedding table.
        
        Returns:
            Tuple of (num_embeddings, embedding_dim)
        """
        return self._cold.shape
    
    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary with hits, misses, hit_rate, cache_size, max_cache_size
        """
        total = self._hits + self._misses
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / total if total > 0 else 0.0,
            "cache_size": len(self._hot_cache),
            "max_cache_size": self._hot_cache_size,
        }


__all__ = ["HybridStorage"]
