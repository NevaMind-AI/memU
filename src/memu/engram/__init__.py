"""
Engram Memory Module for MemU

This module provides a production-ready implementation of Engram,
a storage-compute separated memory system for efficient O(1) retrieval.

Key Features:
    - N-gram hashing for fast memory addressing
    - Multi-head embeddings for collision reduction
    - Storage-compute separation with multiple backends
    - Gating mechanism for memory fusion
    - Comprehensive configuration system

Quick Start:
    ```python
    from memu.engram import EngramService, EngramConfig
    
    # Create with default config
    service = EngramService()
    
    # Retrieve memories for token sequences
    result = service.retrieve([[1, 2, 3, 4, 5]])
    print(result.gated_output.shape)
    
    # With custom config
    config = EngramConfig(
        embedding=EmbeddingConfig(
            storage_backend=StorageBackend.MMAP,
            storage_path="./engram_data.bin",
        ),
    )
    service = EngramService(config)
    ```

Storage Backends:
    - MEMORY: In-memory storage (fastest, volatile)
    - MMAP: Memory-mapped file (persistent, efficient)
    - HYBRID: Hot cache + cold storage (balanced)
    - DISK: On-disk storage (slowest, largest capacity)

Configuration:
    - EngramConfig: Main configuration class
    - HashConfig: N-gram hashing settings
    - EmbeddingConfig: Embedding storage settings
    - GatingConfig: Gating mechanism settings

For detailed documentation, see:
    https://github.com/NevaMind-AI/memU
"""

from memu.engram.settings import (
    # Main config
    EngramConfig,
    # Sub-configs
    NormalizerConfig,
    HashConfig,
    EmbeddingConfig,
    GatingConfig,
    RetrievalConfig,
    # Enums
    StorageBackend,
    QuantizationType,
    # Preset configs
    get_lightweight_config,
    get_standard_config,
    get_large_config,
)

from memu.engram.normalizer import (
    TextNormalizer,
    TokenNormalizer,
    CharacterNormalizer,
)

from memu.engram.hash_mapping import (
    NgramHashMapping,
    NgramHashResult,
    MultiLayerHashMapping,
    TextHashMapping,
)

from memu.engram.embedding import (
    # Embedding table
    MultiHeadEmbeddingTable,
    EmbeddingLookupResult,
)

from memu.engram.storage import (
    # Storage backends
    EmbeddingStorage,
    InMemoryStorage,
    MMapStorage,
    HybridStorage,
    # Utilities
    QuantizationHandler,
)

from memu.engram.gating import (
    # Gating mechanisms
    EngramGating,
    SimpleGating,
    GatingResult,
    # Convolution
    ShortConv1D,
    # Building blocks
    Linear,
    LayerNorm,
    RMSNorm,
    Activations,
    get_activation,
)

from memu.engram.service import (
    # Main services
    EngramService,
    TextEngramService,
    # Result types
    EngramRetrievalResult,
    EngramMemoryItem,
    EngramQueryResult,
    # Metrics
    EngramMetrics,
    MetricsCollector,
    # Factory
    create_engram_service,
)

__version__ = "0.1.0"

__all__ = [
    # Version
    "__version__",
    
    # Main services
    "EngramService",
    "TextEngramService",
    "create_engram_service",
    
    # Configuration
    "EngramConfig",
    "NormalizerConfig",
    "HashConfig",
    "EmbeddingConfig",
    "GatingConfig",
    "RetrievalConfig",
    "StorageBackend",
    "QuantizationType",
    
    # Preset configs
    "get_lightweight_config",
    "get_standard_config",
    "get_large_config",
    
    # Normalizers
    "TextNormalizer",
    "TokenNormalizer",
    "CharacterNormalizer",
    
    # Hash mapping
    "NgramHashMapping",
    "NgramHashResult",
    "MultiLayerHashMapping",
    "TextHashMapping",
    
    # Embedding storage
    "EmbeddingStorage",
    "InMemoryStorage",
    "MMapStorage",
    "HybridStorage",
    "MultiHeadEmbeddingTable",
    "EmbeddingLookupResult",
    "QuantizationHandler",
    
    # Gating
    "EngramGating",
    "SimpleGating",
    "GatingResult",
    "ShortConv1D",
    "Linear",
    "LayerNorm",
    "RMSNorm",
    "Activations",
    "get_activation",
    
    # Result types
    "EngramRetrievalResult",
    "EngramMemoryItem",
    "EngramQueryResult",
    
    # Metrics
    "EngramMetrics",
    "MetricsCollector",
]
