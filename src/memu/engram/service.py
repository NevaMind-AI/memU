"""
Engram Memory Service

This module provides the main service interface for Engram memory retrieval,
integrating hash mapping, embedding storage, and gating mechanisms.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Sequence

import numpy as np

from memu.engram.embedding import MultiHeadEmbeddingTable, EmbeddingLookupResult
from memu.engram.gating import EngramGating, SimpleGating, ShortConv1D, GatingResult
from memu.engram.hash_mapping import NgramHashMapping, NgramHashResult
from memu.engram.normalizer import TextNormalizer, TokenNormalizer
from memu.engram.settings import EngramConfig, StorageBackend

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# ============================================================================
# Result Types
# ============================================================================

@dataclass
class EngramRetrievalResult:
    """Result of Engram memory retrieval.
    
    Attributes:
        memory_embeddings: Retrieved memory embeddings [batch, seq_len, dim]
        gate_values: Gate activation values [batch, seq_len, num_channels]
        gated_output: Final gated output [batch, seq_len, num_channels, output_dim]
        raw_scores: Raw similarity scores before gating
        hash_result: Hash computation result
        metadata: Additional metadata
    """
    memory_embeddings: np.ndarray
    gate_values: np.ndarray
    gated_output: np.ndarray
    raw_scores: np.ndarray
    hash_result: NgramHashResult
    metadata: dict[str, Any] = field(default_factory=dict)
    
    @property
    def flat_output(self) -> np.ndarray:
        """Get flattened output [batch, seq_len, total_dim]."""
        if self.gated_output.ndim == 4:
            batch, seq_len, num_ch, dim = self.gated_output.shape
            return self.gated_output.reshape(batch, seq_len, num_ch * dim)
        return self.gated_output


@dataclass  
class EngramMemoryItem:
    """A single memory item for Engram storage.
    
    Attributes:
        text: Text content of the memory
        embedding: Optional pre-computed embedding
        metadata: Additional metadata
    """
    text: str
    embedding: np.ndarray | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EngramQueryResult:
    """Result of a text-based Engram query.
    
    Attributes:
        query_text: Original query text
        memory_scores: Scores for each retrieved memory
        top_k_indices: Indices of top-k memories
        top_k_embeddings: Embeddings of top-k memories
        metadata: Additional metadata
    """
    query_text: str
    memory_scores: np.ndarray
    top_k_indices: np.ndarray
    top_k_embeddings: np.ndarray
    metadata: dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Metrics Collection
# ============================================================================

@dataclass
class EngramMetrics:
    """Metrics for Engram operations."""
    
    hash_time_ms: float = 0.0
    lookup_time_ms: float = 0.0
    gating_time_ms: float = 0.0
    total_time_ms: float = 0.0
    batch_size: int = 0
    seq_len: int = 0
    cache_hits: int = 0
    cache_misses: int = 0


class MetricsCollector:
    """Collects and aggregates Engram metrics."""
    
    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._history: list[EngramMetrics] = []
    
    def record(self, metrics: EngramMetrics) -> None:
        """Record a metrics entry."""
        if self.enabled:
            self._history.append(metrics)
    
    def get_summary(self) -> dict[str, Any]:
        """Get summary statistics."""
        if not self._history:
            return {}
        
        return {
            "num_calls": len(self._history),
            "avg_hash_time_ms": np.mean([m.hash_time_ms for m in self._history]),
            "avg_lookup_time_ms": np.mean([m.lookup_time_ms for m in self._history]),
            "avg_gating_time_ms": np.mean([m.gating_time_ms for m in self._history]),
            "avg_total_time_ms": np.mean([m.total_time_ms for m in self._history]),
            "total_cache_hits": sum(m.cache_hits for m in self._history),
            "total_cache_misses": sum(m.cache_misses for m in self._history),
        }
    
    def clear(self) -> None:
        """Clear metrics history."""
        self._history.clear()


# ============================================================================
# Main Engram Service
# ============================================================================

class EngramService:
    """Main service for Engram memory retrieval.
    
    This class integrates all Engram components into a unified interface
    for memory storage and retrieval with storage-compute separation.
    
    Features:
        - N-gram hashing for O(1) memory lookup
        - Multi-head embedding tables with various storage backends
        - Gating mechanism for memory fusion
        - Text normalization for consistent hashing
        - Optional short convolution for local enhancement
        - Comprehensive metrics collection
    
    Example:
        ```python
        from memu.engram import EngramService, EngramConfig
        
        # Create service with custom config
        config = EngramConfig(
            embedding=EmbeddingConfig(
                storage_backend=StorageBackend.MMAP,
                storage_path="./engram_data.bin",
                cpu_offload=True,
            ),
        )
        service = EngramService(config)
        
        # Retrieve memories for token sequences
        token_ids = [[1, 2, 3, 4, 5], [6, 7, 8, 9, 10]]
        result = service.retrieve(token_ids)
        print(result.gated_output.shape)
        ```
    """
    
    def __init__(
        self,
        config: EngramConfig | None = None,
        layer_id: int = 0,
    ) -> None:
        """Initialize the Engram service.
        
        Args:
            config: Engram configuration. If None, uses default.
            layer_id: Layer identifier for layer-specific hashing.
        """
        if config is None:
            config = EngramConfig()
        
        self.config = config
        self.layer_id = layer_id
        
        # Initialize components
        self._init_normalizer()
        self._init_hash_mapping()
        self._init_embedding_table()
        self._init_gating()
        self._init_convolution()
        
        # Metrics
        self._metrics = MetricsCollector(enabled=config.collect_metrics)
        
        logger.info(
            f"Initialized EngramService: layer_id={layer_id}, "
            f"storage={config.embedding.storage_backend}, "
            f"memory_usage={config.estimate_memory_usage_human()}"
        )
    
    def _init_normalizer(self) -> None:
        """Initialize text normalizer."""
        self.text_normalizer = TextNormalizer(self.config.normalizer)
        self.token_normalizer: TokenNormalizer | None = None
    
    def _init_hash_mapping(self) -> None:
        """Initialize hash mapping."""
        self.hash_mapping = NgramHashMapping(
            config=self.config.hash,
            layer_id=self.layer_id,
        )
    
    def _init_embedding_table(self) -> None:
        """Initialize embedding table."""
        # Get vocabulary sizes for all heads
        head_vocab_sizes = []
        for level_sizes in self.hash_mapping.head_vocab_sizes:
            head_vocab_sizes.extend(level_sizes)
        
        self.embedding_table = MultiHeadEmbeddingTable(
            head_vocab_sizes=head_vocab_sizes,
            embedding_dim=self.config.embedding.embedding_dim,
            config=self.config.embedding,
        )
    
    def _init_gating(self) -> None:
        """Initialize gating mechanism."""
        # Calculate memory dimension from embedding table
        memory_dim = (
            self.hash_mapping.total_heads *
            self.config.embedding.embedding_dim
        )
        
        self.gating = SimpleGating(
            memory_dim=memory_dim,
            output_dim=self.config.gating.hidden_dim,
            config=self.config.gating,
        )
    
    def _init_convolution(self) -> None:
        """Initialize optional short convolution."""
        self.short_conv: ShortConv1D | None = None
        # Can be enabled for local enhancement
    
    def retrieve(
        self,
        token_ids: np.ndarray | Sequence[Sequence[int]],
        return_raw_embeddings: bool = False,
    ) -> EngramRetrievalResult:
        """Retrieve Engram memories for token sequences.
        
        This is the main retrieval method that:
        1. Computes N-gram hashes for the input tokens
        2. Looks up embeddings from the table
        3. Applies gating to produce the final output
        
        Args:
            token_ids: Token IDs of shape [batch, seq_len] or list of lists
            return_raw_embeddings: Whether to include raw embeddings in result
            
        Returns:
            EngramRetrievalResult with gated memory output
        """
        start_time = time.time()
        metrics = EngramMetrics()
        
        # Convert to numpy
        arr = np.asarray(token_ids, dtype=np.int64)
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        
        metrics.batch_size = arr.shape[0]
        metrics.seq_len = arr.shape[1]
        
        # Step 1: Hash computation
        hash_start = time.time()
        hash_result = self.hash_mapping.hash(arr)
        metrics.hash_time_ms = (time.time() - hash_start) * 1000
        
        # Step 2: Embedding lookup
        lookup_start = time.time()
        embedding_result = self.embedding_table.lookup(hash_result.hash_ids)
        metrics.lookup_time_ms = (time.time() - lookup_start) * 1000
        
        # Get cache stats if available
        if hasattr(self.embedding_table.storage, "get_cache_stats"):
            cache_stats = self.embedding_table.storage.get_cache_stats()
            metrics.cache_hits = cache_stats.get("hits", 0)
            metrics.cache_misses = cache_stats.get("misses", 0)
        
        # Step 3: Gating
        gating_start = time.time()
        gating_result = self.gating(embedding_result.flat_embeddings)
        metrics.gating_time_ms = (time.time() - gating_start) * 1000
        
        # Optional: Apply short convolution
        if self.short_conv is not None:
            gating_result.gated_memory = self.short_conv(gating_result.gated_memory)
        
        metrics.total_time_ms = (time.time() - start_time) * 1000
        self._metrics.record(metrics)
        
        return EngramRetrievalResult(
            memory_embeddings=embedding_result.flat_embeddings if return_raw_embeddings else np.array([]),
            gate_values=gating_result.gates,
            gated_output=gating_result.gated_memory,
            raw_scores=gating_result.raw_scores,
            hash_result=hash_result,
            metadata={
                "metrics": metrics.__dict__,
                "layer_id": self.layer_id,
            },
        )
    
    async def retrieve_async(
        self,
        token_ids: np.ndarray | Sequence[Sequence[int]],
        return_raw_embeddings: bool = False,
    ) -> EngramRetrievalResult:
        """Async version of retrieve for concurrent access."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.retrieve(token_ids, return_raw_embeddings),
        )
    
    def retrieve_with_query(
        self,
        token_ids: np.ndarray,
        query: np.ndarray,
        num_channels: int = 1,
    ) -> EngramRetrievalResult:
        """Retrieve memories with query-based gating.
        
        This method uses the provided query to compute gate values,
        allowing for query-dependent memory selection.
        
        Args:
            token_ids: Token IDs [batch, seq_len]
            query: Query features [batch, seq_len, query_dim] or
                   [batch, seq_len, num_channels, channel_dim]
            num_channels: Number of gating channels
            
        Returns:
            EngramRetrievalResult with query-gated output
        """
        start_time = time.time()
        
        # Convert to numpy
        arr = np.asarray(token_ids, dtype=np.int64)
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        
        # Step 1: Hash
        hash_result = self.hash_mapping.hash(arr)
        
        # Step 2: Lookup
        embedding_result = self.embedding_table.lookup(hash_result.hash_ids)
        
        # Step 3: Query-based gating
        # Create query gating if not exists
        if not hasattr(self, "_query_gating") or self._query_gating is None:
            memory_dim = (
                self.hash_mapping.total_heads *
                self.config.embedding.embedding_dim
            )
            self._query_gating = EngramGating(
                input_dim=query.shape[-1],
                memory_dim=memory_dim,
                output_dim=self.config.gating.hidden_dim,
                num_channels=num_channels,
                config=self.config.gating,
            )
        
        gating_result = self._query_gating(query, embedding_result.flat_embeddings)
        
        return EngramRetrievalResult(
            memory_embeddings=embedding_result.flat_embeddings,
            gate_values=gating_result.gates,
            gated_output=gating_result.gated_memory,
            raw_scores=gating_result.raw_scores,
            hash_result=hash_result,
            metadata={
                "total_time_ms": (time.time() - start_time) * 1000,
                "layer_id": self.layer_id,
                "num_channels": num_channels,
            },
        )
    
    def get_embedding_by_hash(
        self,
        hash_ids: np.ndarray,
    ) -> np.ndarray:
        """Get embeddings directly by hash indices.
        
        Args:
            hash_ids: Hash indices [batch, seq_len, num_heads]
            
        Returns:
            Embeddings [batch, seq_len, num_heads, dim]
        """
        result = self.embedding_table.lookup(hash_ids)
        return result.embeddings
    
    def update_embeddings(
        self,
        indices: np.ndarray,
        embeddings: np.ndarray,
    ) -> None:
        """Update embeddings at specific indices.
        
        Args:
            indices: Global indices to update
            embeddings: New embedding values
        """
        self.embedding_table.update_embeddings(indices, embeddings)
    
    def save(self, path: Path | str) -> None:
        """Save Engram state to disk.
        
        Args:
            path: Output directory path
        """
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        
        # Save embeddings
        self.embedding_table.save(path / "embeddings.npy")
        
        # Save gating parameters
        import json
        gating_params = self.gating.get_parameters() if hasattr(self.gating, "get_parameters") else {}
        np.savez(path / "gating_params.npz", **gating_params)
        
        # Save config
        with open(path / "config.json", "w") as f:
            json.dump(self.config.to_dict(), f, indent=2, default=str)
        
        logger.info(f"Saved EngramService to {path}")
    
    def load(self, path: Path | str) -> None:
        """Load Engram state from disk.
        
        Args:
            path: Input directory path
        """
        path = Path(path)
        
        # Load embeddings
        self.embedding_table.load(path / "embeddings.npy")
        
        # Load gating parameters
        gating_path = path / "gating_params.npz"
        if gating_path.exists():
            params = dict(np.load(gating_path))
            if hasattr(self.gating, "set_parameters"):
                self.gating.set_parameters(params)
        
        logger.info(f"Loaded EngramService from {path}")
    
    def close(self) -> None:
        """Close resources and release memory."""
        self.embedding_table.close()
        logger.info("Closed EngramService")
    
    def get_stats(self) -> dict[str, Any]:
        """Get comprehensive statistics.
        
        Returns:
            Dictionary with configuration and runtime statistics
        """
        stats = {
            "config": {
                "layer_id": self.layer_id,
                "storage_backend": self.config.embedding.storage_backend.value,
                "quantization": self.config.embedding.quantization.value,
                "max_ngram_size": self.config.hash.max_ngram_size,
                "num_heads": self.config.hash.num_heads,
                "embedding_dim": self.config.embedding.embedding_dim,
            },
            "memory": {
                "total_entries": self.embedding_table.total_vocab_size,
                "estimated_bytes": self.config.estimate_memory_usage_bytes(),
                "estimated_human": self.config.estimate_memory_usage_human(),
            },
            "hash_mapping": self.hash_mapping.get_stats(),
            "embedding_table": self.embedding_table.get_stats(),
        }
        
        if self.config.collect_metrics:
            stats["metrics"] = self._metrics.get_summary()
        
        return stats
    
    def __enter__(self) -> "EngramService":
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()


# ============================================================================
# Text-based Engram Service
# ============================================================================

class TextEngramService:
    """Engram service with text-based interface.
    
    This class provides a higher-level interface for working with
    text inputs directly, handling tokenization internally.
    
    Example:
        ```python
        from memu.engram import TextEngramService
        
        service = TextEngramService()
        
        # Store memories
        service.add_memory("The capital of France is Paris")
        service.add_memory("Python is a programming language")
        
        # Query memories
        result = service.query("What is the capital of France?")
        print(result.top_k_embeddings)
        ```
    """
    
    def __init__(
        self,
        config: EngramConfig | None = None,
        tokenizer: Any = None,
    ) -> None:
        """Initialize text-based Engram service.
        
        Args:
            config: Engram configuration
            tokenizer: HuggingFace tokenizer instance
        """
        self.config = config or EngramConfig()
        self.tokenizer = tokenizer
        
        # Core Engram service
        self.engram = EngramService(config)
        
        # Memory storage
        self._memories: list[EngramMemoryItem] = []
        self._memory_hashes: list[np.ndarray] = []
        self._memory_embeddings: list[np.ndarray] = []
    
    def set_tokenizer(self, tokenizer: Any) -> None:
        """Set the tokenizer for text processing.
        
        Args:
            tokenizer: HuggingFace tokenizer instance
        """
        self.tokenizer = tokenizer
        
        # Build token normalizer
        self.engram.token_normalizer = TokenNormalizer(self.engram.text_normalizer)
        self.engram.token_normalizer.build_from_tokenizer(tokenizer)
    
    def tokenize(self, text: str) -> np.ndarray:
        """Tokenize text to token IDs.
        
        Args:
            text: Input text
            
        Returns:
            Token IDs array
        """
        if self.tokenizer is None:
            # Simple character-level tokenization fallback
            return np.array([ord(c) for c in text], dtype=np.int64)
        
        tokens = self.tokenizer(text, return_tensors="np")
        return tokens["input_ids"][0]
    
    def add_memory(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Add a memory item.
        
        Args:
            text: Text content
            metadata: Optional metadata
            
        Returns:
            Index of the added memory
        """
        # Tokenize
        token_ids = self.tokenize(text)
        
        # Compute hash
        hash_result = self.engram.hash_mapping.hash(token_ids.reshape(1, -1))
        
        # Get embedding
        embedding_result = self.engram.embedding_table.lookup(hash_result.hash_ids)
        
        # Aggregate embedding (mean over sequence)
        aggregated = embedding_result.flat_embeddings[0].mean(axis=0)
        
        # Store
        item = EngramMemoryItem(
            text=text,
            embedding=aggregated,
            metadata=metadata or {},
        )
        self._memories.append(item)
        self._memory_hashes.append(hash_result.hash_ids[0])
        self._memory_embeddings.append(aggregated)
        
        return len(self._memories) - 1
    
    def query(
        self,
        text: str,
        top_k: int | None = None,
    ) -> EngramQueryResult:
        """Query memories with text.
        
        Args:
            text: Query text
            top_k: Number of results to return
            
        Returns:
            Query result with top-k matches
        """
        if not self._memories:
            return EngramQueryResult(
                query_text=text,
                memory_scores=np.array([]),
                top_k_indices=np.array([]),
                top_k_embeddings=np.array([]),
            )
        
        top_k = top_k or self.config.retrieval.top_k
        
        # Tokenize query
        token_ids = self.tokenize(text)
        
        # Get query embedding
        result = self.engram.retrieve(token_ids.reshape(1, -1))
        query_embedding = result.gated_output[0].mean(axis=0).flatten()
        
        # Compute scores against all memories
        memory_matrix = np.stack(self._memory_embeddings)
        
        # Cosine similarity
        query_norm = np.linalg.norm(query_embedding)
        memory_norms = np.linalg.norm(memory_matrix, axis=1)
        
        if query_norm > 0 and np.all(memory_norms > 0):
            scores = np.dot(memory_matrix, query_embedding) / (memory_norms * query_norm)
        else:
            scores = np.zeros(len(self._memories))
        
        # Get top-k
        k = min(top_k, len(self._memories))
        top_indices = np.argsort(scores)[-k:][::-1]
        
        return EngramQueryResult(
            query_text=text,
            memory_scores=scores,
            top_k_indices=top_indices,
            top_k_embeddings=memory_matrix[top_indices],
            metadata={
                "num_memories": len(self._memories),
                "top_k": k,
            },
        )
    
    def get_memory(self, index: int) -> EngramMemoryItem:
        """Get a memory item by index.
        
        Args:
            index: Memory index
            
        Returns:
            Memory item
        """
        return self._memories[index]
    
    def clear_memories(self) -> None:
        """Clear all stored memories."""
        self._memories.clear()
        self._memory_hashes.clear()
        self._memory_embeddings.clear()
    
    def close(self) -> None:
        """Close resources."""
        self.engram.close()


# ============================================================================
# Factory Functions
# ============================================================================

def create_engram_service(
    storage_path: Path | str | None = None,
    storage_backend: str = "memory",
    max_ngram_size: int = 3,
    num_heads: int = 8,
    vocab_sizes: list[int] | None = None,
    embedding_dim: int = 64,
    layer_id: int = 0,
    **kwargs,
) -> EngramService:
    """Create an Engram service with common configurations.
    
    Args:
        storage_path: Path for persistent storage
        storage_backend: Storage backend ("memory", "mmap", "hybrid")
        max_ngram_size: Maximum N-gram size
        num_heads: Number of hash heads
        vocab_sizes: Vocabulary sizes per N-gram level
        embedding_dim: Embedding dimension
        layer_id: Layer identifier
        **kwargs: Additional config options
        
    Returns:
        Configured EngramService
    """
    from memu.engram.settings import (
        HashConfig,
        EmbeddingConfig,
        GatingConfig,
        EngramConfig,
        StorageBackend,
    )
    
    # Default vocab sizes
    if vocab_sizes is None:
        vocab_sizes = [640_000] * (max_ngram_size - 1)
    
    # Map storage backend string to enum
    backend_map = {
        "memory": StorageBackend.MEMORY,
        "mmap": StorageBackend.MMAP,
        "hybrid": StorageBackend.HYBRID,
        "disk": StorageBackend.DISK,
    }
    backend = backend_map.get(storage_backend, StorageBackend.MEMORY)
    
    config = EngramConfig(
        hash=HashConfig(
            max_ngram_size=max_ngram_size,
            num_heads=num_heads,
            vocab_sizes=vocab_sizes,
        ),
        embedding=EmbeddingConfig(
            embedding_dim=embedding_dim,
            storage_backend=backend,
            storage_path=storage_path,
        ),
        gating=GatingConfig(
            hidden_dim=kwargs.get("hidden_dim", 512),
        ),
        collect_metrics=kwargs.get("collect_metrics", False),
    )
    
    return EngramService(config, layer_id=layer_id)


__all__ = [
    "EngramService",
    "TextEngramService",
    "EngramRetrievalResult",
    "EngramMemoryItem",
    "EngramQueryResult",
    "EngramMetrics",
    "MetricsCollector",
    "create_engram_service",
]
