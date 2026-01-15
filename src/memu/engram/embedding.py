"""
Engram Multi-Head Embedding Table

This module provides the multi-head embedding table implementation
that coordinates with different storage backends.
"""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

from memu.engram.storage import (
    EmbeddingStorage,
    HybridStorage,
    InMemoryStorage,
    MMapStorage,
    QuantizationHandler,
)

if TYPE_CHECKING:
    from memu.engram.settings import EmbeddingConfig

logger = logging.getLogger(__name__)


# ============================================================================
# Multi-Head Embedding Table
# ============================================================================

@dataclass
class EmbeddingLookupResult:
    """Result of embedding lookup.
    
    Attributes:
        embeddings: Retrieved embeddings [batch, seq_len, num_heads, dim]
        flat_embeddings: Flattened embeddings [batch, seq_len, total_dim]
        metadata: Optional metadata
    """
    embeddings: np.ndarray
    flat_embeddings: np.ndarray
    metadata: dict[str, Any] = field(default_factory=dict)


class MultiHeadEmbeddingTable:
    """Multi-head embedding table for Engram.
    
    This class manages a unified embedding table for multiple heads,
    using offsets to partition the table across heads.
    
    Features:
        - Unified storage for memory efficiency
        - Head-specific offsets for correct lookup
        - Support for multiple storage backends
        - Async prefetching for performance
    """
    
    def __init__(
        self,
        head_vocab_sizes: list[int],
        embedding_dim: int,
        config: "EmbeddingConfig | None" = None,
    ) -> None:
        """Initialize the multi-head embedding table.
        
        Args:
            head_vocab_sizes: Vocabulary size for each head
            embedding_dim: Embedding dimension
            config: Embedding configuration
        """
        if config is None:
            from memu.engram.settings import EmbeddingConfig
            config = EmbeddingConfig()
        
        self.config = config
        self.head_vocab_sizes = head_vocab_sizes
        self.embedding_dim = embedding_dim
        self.num_heads = len(head_vocab_sizes)
        
        # Compute offsets
        self.offsets = self._compute_offsets()
        self.total_vocab_size = sum(head_vocab_sizes)
        
        # Initialize storage
        self.storage = self._init_storage()
        
        # Prefetch executor
        self._executor: ThreadPoolExecutor | None = None
        if config.async_prefetch:
            self._executor = ThreadPoolExecutor(max_workers=2)
        
        # Quantization metadata
        self._quant_metadata: dict[str, Any] = {}
        
        logger.info(
            f"Initialized MultiHeadEmbeddingTable: "
            f"{self.num_heads} heads, {self.total_vocab_size} total entries, "
            f"dim={embedding_dim}, storage={config.storage_backend}"
        )
    
    def _compute_offsets(self) -> np.ndarray:
        """Compute embedding table offsets for each head."""
        offsets = [0]
        for size in self.head_vocab_sizes[:-1]:
            offsets.append(offsets[-1] + size)
        return np.array(offsets, dtype=np.int64)
    
    def _init_storage(self) -> EmbeddingStorage:
        """Initialize the storage backend."""
        from memu.engram.settings import StorageBackend
        
        backend = self.config.storage_backend
        
        # Determine dtype based on quantization
        dtype = self._get_storage_dtype()
        
        if backend == StorageBackend.MEMORY:
            return InMemoryStorage(
                num_embeddings=self.total_vocab_size,
                embedding_dim=self.embedding_dim,
                dtype=dtype,
                init_method=self.config.init_method,
                init_scale=self.config.init_scale,
            )
        
        elif backend == StorageBackend.MMAP:
            path = self.config.storage_path
            if path is None:
                raise ValueError("storage_path required for MMAP backend")
            return MMapStorage(
                path=path,
                num_embeddings=self.total_vocab_size,
                embedding_dim=self.embedding_dim,
                dtype=dtype,
                mode="w+",
                init_method=self.config.init_method,
                init_scale=self.config.init_scale,
            )
        
        elif backend == StorageBackend.HYBRID:
            path = self.config.storage_path
            if path is None:
                raise ValueError("storage_path required for HYBRID backend")
            return HybridStorage(
                path=path,
                num_embeddings=self.total_vocab_size,
                embedding_dim=self.embedding_dim,
                hot_cache_size=self.config.hot_cache_size,
                dtype=dtype,
                init_method=self.config.init_method,
                init_scale=self.config.init_scale,
            )
        
        else:
            raise ValueError(f"Unknown storage backend: {backend}")
    
    def _get_storage_dtype(self) -> np.dtype:
        """Get numpy dtype for storage."""
        from memu.engram.settings import QuantizationType
        
        dtype_map = {
            QuantizationType.NONE: np.float32,
            QuantizationType.FP16: np.float16,
            QuantizationType.INT8: np.int8,
            QuantizationType.INT4: np.uint8,
        }
        return dtype_map[self.config.quantization]
    
    def lookup(
        self,
        hash_ids: np.ndarray,
    ) -> EmbeddingLookupResult:
        """Look up embeddings by hash indices.
        
        Args:
            hash_ids: Hash indices of shape [batch, seq_len, num_heads]
            
        Returns:
            EmbeddingLookupResult with retrieved embeddings
        """
        batch_size, seq_len, num_heads = hash_ids.shape
        assert num_heads == self.num_heads, f"Expected {self.num_heads} heads"
        
        # Add offsets to get global indices
        # offsets shape: [num_heads] -> broadcast to [1, 1, num_heads]
        global_indices = hash_ids + self.offsets.reshape(1, 1, -1)
        
        # Flatten for batch lookup
        flat_indices = global_indices.reshape(-1)
        
        # Load from storage
        flat_embeddings = self.storage.load(flat_indices)
        
        # Dequantize if needed
        from memu.engram.settings import QuantizationType
        if self.config.quantization not in (QuantizationType.NONE, QuantizationType.FP16):
            flat_embeddings = QuantizationHandler.dequantize(
                flat_embeddings,
                self.config.quantization,
                self._quant_metadata,
            )
        
        # Reshape to [batch, seq_len, num_heads, embedding_dim]
        embeddings = flat_embeddings.reshape(
            batch_size, seq_len, num_heads, self.embedding_dim
        )
        
        # Create flattened version [batch, seq_len, num_heads * embedding_dim]
        flat = embeddings.reshape(
            batch_size, seq_len, num_heads * self.embedding_dim
        )
        
        return EmbeddingLookupResult(
            embeddings=embeddings,
            flat_embeddings=flat,
            metadata={
                "batch_size": batch_size,
                "seq_len": seq_len,
                "num_heads": num_heads,
            },
        )
    
    async def lookup_async(
        self,
        hash_ids: np.ndarray,
    ) -> EmbeddingLookupResult:
        """Async version of lookup for concurrent access."""
        loop = asyncio.get_event_loop()
        if self._executor:
            result = await loop.run_in_executor(
                self._executor,
                self.lookup,
                hash_ids,
            )
            return result
        else:
            return self.lookup(hash_ids)
    
    def update_embeddings(
        self,
        indices: np.ndarray,
        embeddings: np.ndarray,
    ) -> None:
        """Update specific embeddings.
        
        Args:
            indices: Global indices to update
            embeddings: New embedding values
        """
        # Quantize if needed
        from memu.engram.settings import QuantizationType
        if self.config.quantization not in (QuantizationType.NONE, QuantizationType.FP16):
            embeddings, self._quant_metadata = QuantizationHandler.quantize(
                embeddings,
                self.config.quantization,
            )
        
        self.storage.update(indices, embeddings)
    
    def save(self, path: Path | str) -> None:
        """Save embeddings to file.
        
        Args:
            path: Output path
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        data = self.storage.load_all()
        np.save(path, data)
        
        # Save metadata
        import json
        meta_path = path.with_suffix(".json")
        with open(meta_path, "w") as f:
            json.dump({
                "head_vocab_sizes": self.head_vocab_sizes,
                "embedding_dim": self.embedding_dim,
                "offsets": self.offsets.tolist(),
                "quant_metadata": self._quant_metadata,
            }, f)
    
    def load(self, path: Path | str) -> None:
        """Load embeddings from file.
        
        Args:
            path: Input path
        """
        path = Path(path)
        
        data = np.load(path)
        self.storage.store(data)
        
        # Load metadata
        import json
        meta_path = path.with_suffix(".json")
        if meta_path.exists():
            with open(meta_path) as f:
                meta = json.load(f)
                self._quant_metadata = meta.get("quant_metadata", {})
    
    def close(self) -> None:
        """Close storage and release resources."""
        self.storage.close()
        if self._executor:
            self._executor.shutdown(wait=False)
    
    def get_stats(self) -> dict[str, Any]:
        """Get embedding table statistics."""
        stats = {
            "num_heads": self.num_heads,
            "head_vocab_sizes": self.head_vocab_sizes,
            "embedding_dim": self.embedding_dim,
            "total_vocab_size": self.total_vocab_size,
            "storage_backend": self.config.storage_backend.value,
            "quantization": self.config.quantization.value,
            "memory_bytes": self.total_vocab_size * self.embedding_dim * 
                           np.dtype(self._get_storage_dtype()).itemsize,
        }
        
        # Add cache stats if available
        if hasattr(self.storage, "get_cache_stats"):
            stats["cache"] = self.storage.get_cache_stats()
        
        return stats


__all__ = [
    "MultiHeadEmbeddingTable",
    "EmbeddingLookupResult",
]
