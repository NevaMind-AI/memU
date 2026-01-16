"""
Engram Configuration Module

This module defines all configuration classes for the Engram memory system,
supporting production-ready deployment with storage-compute separation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Literal


class StorageBackend(str, Enum):
    """Storage backend options for Engram embeddings."""
    
    MEMORY = "memory"       # In-memory storage (fastest, volatile)
    MMAP = "mmap"           # Memory-mapped file (persistent, efficient)
    DISK = "disk"           # On-disk storage (slowest, largest capacity)
    HYBRID = "hybrid"       # Hot embeddings in memory, cold on disk


class QuantizationType(str, Enum):
    """Quantization options for embedding storage."""
    
    NONE = "none"           # Full precision (float32)
    FP16 = "fp16"           # Half precision (float16)
    INT8 = "int8"           # 8-bit quantization
    INT4 = "int4"           # 4-bit quantization (experimental)


@dataclass
class NormalizerConfig:
    """Configuration for text normalization.
    
    Controls how input text is preprocessed before hashing.
    """
    
    # Unicode normalization form
    unicode_form: Literal["NFC", "NFD", "NFKC", "NFKD"] = "NFKC"
    
    # Whether to convert to lowercase
    lowercase: bool = True
    
    # Whether to strip accents
    strip_accents: bool = True
    
    # Whether to collapse whitespace
    collapse_whitespace: bool = True
    
    # Custom character replacements (dict of pattern -> replacement)
    custom_replacements: dict[str, str] = field(default_factory=dict)


@dataclass
class HashConfig:
    """Configuration for N-gram hashing.
    
    Controls how token sequences are mapped to hash indices.
    """
    
    # Maximum N-gram size (e.g., 3 means 2-gram and 3-gram)
    max_ngram_size: int = 3
    
    # Number of hash heads per N-gram (for collision reduction)
    num_heads: int = 8
    
    # Vocabulary size per N-gram level (list of sizes for each n-gram type)
    vocab_sizes: list[int] = field(default_factory=lambda: [640_000, 640_000])
    
    # Random seed for hash multiplier generation
    seed: int = 42
    
    # Padding token ID (for handling sequence boundaries)
    pad_id: int = 0
    
    # Whether to use prime numbers for modulo operations (better distribution)
    use_prime_modulo: bool = True


@dataclass
class EmbeddingConfig:
    """Configuration for embedding storage and retrieval.
    
    Controls the embedding table structure and storage-compute separation.
    """
    
    # Embedding dimension per head
    embedding_dim: int = 64
    
    # Storage backend for embeddings
    storage_backend: StorageBackend = StorageBackend.MEMORY
    
    # Quantization type for storage efficiency
    quantization: QuantizationType = QuantizationType.FP16
    
    # Path for persistent storage (required for mmap/disk backends)
    storage_path: Path | str | None = None
    
    # Whether to enable CPU offloading
    cpu_offload: bool = False
    
    # Prefetch buffer size (number of embeddings to prefetch)
    prefetch_buffer_size: int = 10000
    
    # Cache size for hot embeddings (only for hybrid backend)
    hot_cache_size: int = 100000
    
    # Whether to enable async prefetching
    async_prefetch: bool = True
    
    # Initialization method for embeddings
    init_method: Literal["normal", "uniform", "xavier", "kaiming"] = "normal"
    
    # Initialization scale factor
    init_scale: float = 0.02


@dataclass
class GatingConfig:
    """Configuration for gating mechanism.
    
    Controls how Engram memories are fused with query states.
    """
    
    # Hidden dimension for gating projections
    hidden_dim: int = 512
    
    # Whether to use layer normalization in gating
    use_layer_norm: bool = True
    
    # Layer normalization epsilon
    norm_eps: float = 1e-6
    
    # Activation function for gating
    activation: Literal["sigmoid", "softmax", "gelu", "silu"] = "sigmoid"
    
    # Temperature for gating computation
    temperature: float = 1.0
    
    # Minimum gate value (for numerical stability)
    gate_min: float = 1e-6
    
    # Whether to apply sqrt scaling (as in original Engram)
    sqrt_scaling: bool = True


@dataclass
class RetrievalConfig:
    """Configuration for Engram retrieval behavior.
    
    Controls how memories are retrieved and ranked.
    """
    
    # Maximum number of memories to retrieve
    top_k: int = 10
    
    # Minimum similarity threshold for retrieval
    similarity_threshold: float = 0.0
    
    # Whether to use weighted aggregation across heads
    weighted_aggregation: bool = True
    
    # Whether to enable batch retrieval optimization
    batch_optimization: bool = True
    
    # Retrieval timeout in seconds (0 = no timeout)
    timeout_seconds: float = 0.0


@dataclass
class EngramConfig:
    """Main configuration class for Engram module.
    
    This is the primary configuration interface that combines all sub-configurations.
    
    Example:
        ```python
        config = EngramConfig(
            normalizer=NormalizerConfig(lowercase=True),
            hash=HashConfig(max_ngram_size=3, num_heads=8),
            embedding=EmbeddingConfig(
                storage_backend=StorageBackend.MMAP,
                storage_path="./engram_embeddings.bin",
                cpu_offload=True,
            ),
            gating=GatingConfig(hidden_dim=512),
            retrieval=RetrievalConfig(top_k=10),
        )
        ```
    """
    
    # Sub-configurations
    normalizer: NormalizerConfig = field(default_factory=NormalizerConfig)
    hash: HashConfig = field(default_factory=HashConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    gating: GatingConfig = field(default_factory=GatingConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    
    # Global settings
    enabled: bool = True
    device: str = "cpu"  # Target device for computations
    dtype: str = "float32"  # Default data type
    
    # Logging and debugging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    collect_metrics: bool = False
    
    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        self._validate()
    
    def _validate(self) -> None:
        """Validate configuration consistency."""
        # Validate hash config
        if len(self.hash.vocab_sizes) != self.hash.max_ngram_size - 1:
            msg = (
                f"Number of vocab_sizes ({len(self.hash.vocab_sizes)}) must equal "
                f"max_ngram_size - 1 ({self.hash.max_ngram_size - 1})"
            )
            raise ValueError(msg)
        
        # Validate embedding storage path
        if self.embedding.storage_backend in (StorageBackend.MMAP, StorageBackend.DISK):
            if self.embedding.storage_path is None:
                msg = f"storage_path is required for {self.embedding.storage_backend} backend"
                raise ValueError(msg)
        
        # Validate gating dimension consistency
        total_embedding_dim = (
            (self.hash.max_ngram_size - 1) *
            self.hash.num_heads *
            self.embedding.embedding_dim
        )
        if self.gating.hidden_dim < 1:
            msg = f"gating.hidden_dim must be positive, got {self.gating.hidden_dim}"
            raise ValueError(msg)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EngramConfig":
        """Create configuration from a dictionary.
        
        Args:
            data: Dictionary with configuration values
            
        Returns:
            EngramConfig instance
        """
        normalizer = NormalizerConfig(**data.get("normalizer", {}))
        hash_cfg = HashConfig(**data.get("hash", {}))
        embedding = EmbeddingConfig(**data.get("embedding", {}))
        gating = GatingConfig(**data.get("gating", {}))
        retrieval = RetrievalConfig(**data.get("retrieval", {}))
        
        return cls(
            normalizer=normalizer,
            hash=hash_cfg,
            embedding=embedding,
            gating=gating,
            retrieval=retrieval,
            enabled=data.get("enabled", True),
            device=data.get("device", "cpu"),
            dtype=data.get("dtype", "float32"),
            log_level=data.get("log_level", "INFO"),
            collect_metrics=data.get("collect_metrics", False),
        )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to a dictionary.
        
        Returns:
            Dictionary representation of the configuration
        """
        from dataclasses import asdict
        return asdict(self)
    
    def get_total_embedding_entries(self) -> int:
        """Calculate total number of embedding entries.
        
        Returns:
            Total number of embedding entries across all N-gram levels
        """
        total = 0
        for vocab_size in self.hash.vocab_sizes:
            total += vocab_size * self.hash.num_heads
        return total
    
    def estimate_memory_usage_bytes(self) -> int:
        """Estimate memory usage for embeddings.
        
        Returns:
            Estimated memory usage in bytes
        """
        total_entries = self.get_total_embedding_entries()
        bytes_per_element = {
            QuantizationType.NONE: 4,
            QuantizationType.FP16: 2,
            QuantizationType.INT8: 1,
            QuantizationType.INT4: 0.5,
        }[self.embedding.quantization]
        
        return int(total_entries * self.embedding.embedding_dim * bytes_per_element)
    
    def estimate_memory_usage_human(self) -> str:
        """Get human-readable memory usage estimate.
        
        Returns:
            Human-readable memory usage string (e.g., "2.5 GB")
        """
        bytes_usage = self.estimate_memory_usage_bytes()
        
        if bytes_usage >= 1e12:
            return f"{bytes_usage / 1e12:.2f} TB"
        elif bytes_usage >= 1e9:
            return f"{bytes_usage / 1e9:.2f} GB"
        elif bytes_usage >= 1e6:
            return f"{bytes_usage / 1e6:.2f} MB"
        elif bytes_usage >= 1e3:
            return f"{bytes_usage / 1e3:.2f} KB"
        else:
            return f"{bytes_usage} bytes"


# Preset configurations for common use cases
def get_lightweight_config() -> EngramConfig:
    """Get lightweight configuration for development/testing.
    
    Memory usage: ~50 MB
    """
    return EngramConfig(
        hash=HashConfig(
            max_ngram_size=2,
            num_heads=4,
            vocab_sizes=[100_000],
        ),
        embedding=EmbeddingConfig(
            embedding_dim=32,
            quantization=QuantizationType.FP16,
        ),
        gating=GatingConfig(hidden_dim=128),
    )


def get_standard_config() -> EngramConfig:
    """Get standard configuration for production use.
    
    Memory usage: ~2 GB
    """
    return EngramConfig(
        hash=HashConfig(
            max_ngram_size=3,
            num_heads=8,
            vocab_sizes=[640_000, 640_000],
        ),
        embedding=EmbeddingConfig(
            embedding_dim=64,
            quantization=QuantizationType.FP16,
        ),
        gating=GatingConfig(hidden_dim=512),
    )


def get_large_config(storage_path: str | Path) -> EngramConfig:
    """Get large configuration for maximum performance.
    
    Memory usage: ~20 GB (with CPU offload)
    
    Args:
        storage_path: Path for memory-mapped storage
    """
    return EngramConfig(
        hash=HashConfig(
            max_ngram_size=4,
            num_heads=16,
            vocab_sizes=[2_000_000, 2_000_000, 2_000_000],
        ),
        embedding=EmbeddingConfig(
            embedding_dim=128,
            storage_backend=StorageBackend.MMAP,
            storage_path=storage_path,
            quantization=QuantizationType.FP16,
            cpu_offload=True,
        ),
        gating=GatingConfig(hidden_dim=1024),
    )


__all__ = [
    "EngramConfig",
    "NormalizerConfig",
    "HashConfig",
    "EmbeddingConfig",
    "GatingConfig",
    "RetrievalConfig",
    "StorageBackend",
    "QuantizationType",
    "get_lightweight_config",
    "get_standard_config",
    "get_large_config",
]
