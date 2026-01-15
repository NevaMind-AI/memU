"""
N-gram Hash Mapping Module

This module provides efficient N-gram hashing for Engram memory retrieval.
It maps token sequences to fixed-size hash indices using multi-head hashing.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from functools import cached_property
from typing import TYPE_CHECKING, Any, Sequence

import numpy as np

if TYPE_CHECKING:
    from memu.engram.settings import HashConfig


def is_prime(n: int) -> bool:
    """Check if a number is prime using trial division.
    
    Args:
        n: Number to check
        
    Returns:
        True if n is prime
    """
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    for i in range(3, int(n**0.5) + 1, 2):
        if n % i == 0:
            return False
    return True


def find_next_prime(start: int, exclude: set[int] | None = None) -> int:
    """Find the next prime number after start.
    
    Args:
        start: Starting number
        exclude: Set of primes to exclude
        
    Returns:
        Next prime number
    """
    exclude = exclude or set()
    candidate = start + 1
    while True:
        if is_prime(candidate) and candidate not in exclude:
            return candidate
        candidate += 1


@dataclass
class NgramHashResult:
    """Result of N-gram hash computation.
    
    Attributes:
        hash_ids: Hash indices array of shape [batch, seq_len, num_heads_total]
        ngram_ranges: List of (start, end) tuples for each N-gram level in hash_ids
        metadata: Optional metadata dictionary
    """
    hash_ids: np.ndarray
    ngram_ranges: list[tuple[int, int]]
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def get_ngram_hashes(self, n: int) -> np.ndarray:
        """Get hash indices for specific N-gram level.
        
        Args:
            n: N-gram level (2 for bigram, 3 for trigram, etc.)
            
        Returns:
            Hash indices for the specified N-gram level
        """
        if n < 2 or n > len(self.ngram_ranges) + 1:
            raise ValueError(f"Invalid N-gram level: {n}")
        
        start, end = self.ngram_ranges[n - 2]
        return self.hash_ids[..., start:end]


class NgramHashMapping:
    """N-gram hash mapping for Engram memory retrieval.
    
    This class computes hash indices for N-gram token sequences using
    a multi-head polynomial rolling hash with XOR mixing. The hash
    values are computed to minimize collisions while maintaining O(1)
    lookup complexity.
    
    Features:
        - Multi-head hashing for collision reduction
        - Prime modulo for uniform distribution
        - Layer-specific hash multipliers
        - Efficient NumPy vectorization
    
    Example:
        ```python
        from memu.engram.hash_mapping import NgramHashMapping
        from memu.engram.settings import HashConfig
        
        config = HashConfig(max_ngram_size=3, num_heads=8)
        hasher = NgramHashMapping(config)
        
        # Hash a batch of token sequences
        token_ids = np.array([[1, 2, 3, 4, 5], [6, 7, 8, 9, 10]])
        result = hasher.hash(token_ids)
        print(result.hash_ids.shape)  # (2, 5, 16)  # 2 ngram levels * 8 heads
        ```
    """
    
    def __init__(
        self,
        config: HashConfig | None = None,
        layer_id: int = 0,
    ) -> None:
        """Initialize the N-gram hash mapping.
        
        Args:
            config: Hash configuration. If None, uses default.
            layer_id: Layer identifier for layer-specific hashing.
        """
        if config is None:
            from memu.engram.settings import HashConfig
            config = HashConfig()
        
        self.config = config
        self.layer_id = layer_id
        
        # Validate configuration
        if len(config.vocab_sizes) != config.max_ngram_size - 1:
            raise ValueError(
                f"vocab_sizes length ({len(config.vocab_sizes)}) must equal "
                f"max_ngram_size - 1 ({config.max_ngram_size - 1})"
            )
        
        # Initialize hash parameters
        self._init_hash_multipliers()
        self._init_vocab_sizes()
    
    def _init_hash_multipliers(self) -> None:
        """Initialize layer-specific hash multipliers."""
        PRIME_SEED = 10007
        base_seed = self.config.seed + PRIME_SEED * self.layer_id
        
        rng = np.random.default_rng(base_seed)
        
        # Compute safe range for multipliers to avoid overflow
        max_int64 = np.iinfo(np.int64).max
        estimated_vocab = max(self.config.vocab_sizes) * 10  # Safety margin
        max_multiplier = max(1, max_int64 // estimated_vocab // 2)
        
        # Generate odd multipliers (better distribution properties)
        raw_values = rng.integers(
            low=1,
            high=max_multiplier,
            size=(self.config.max_ngram_size,),
            dtype=np.int64
        )
        self.multipliers = raw_values * 2 + 1
    
    def _init_vocab_sizes(self) -> None:
        """Initialize vocabulary sizes with prime moduli."""
        if not self.config.use_prime_modulo:
            # Use configured sizes directly
            self.head_vocab_sizes: list[list[int]] = []
            for vocab_size in self.config.vocab_sizes:
                self.head_vocab_sizes.append([vocab_size] * self.config.num_heads)
            return
        
        # Find prime moduli for each head
        seen_primes: set[int] = set()
        self.head_vocab_sizes = []
        
        for vocab_size in self.config.vocab_sizes:
            heads = []
            search_start = vocab_size - 1
            
            for _ in range(self.config.num_heads):
                prime = find_next_prime(search_start, seen_primes)
                seen_primes.add(prime)
                heads.append(prime)
                search_start = prime
            
            self.head_vocab_sizes.append(heads)
    
    @cached_property
    def total_heads(self) -> int:
        """Total number of hash heads across all N-gram levels."""
        return (self.config.max_ngram_size - 1) * self.config.num_heads
    
    @cached_property
    def ngram_ranges(self) -> list[tuple[int, int]]:
        """Get index ranges for each N-gram level in the hash output."""
        ranges = []
        start = 0
        for _ in range(self.config.max_ngram_size - 1):
            end = start + self.config.num_heads
            ranges.append((start, end))
            start = end
        return ranges
    
    def _create_shifted_views(
        self,
        token_ids: np.ndarray,
    ) -> list[np.ndarray]:
        """Create shifted views for N-gram computation.
        
        Args:
            token_ids: Input token IDs of shape [batch, seq_len]
            
        Returns:
            List of shifted arrays for each position in the N-gram
        """
        batch_size, seq_len = token_ids.shape
        pad_id = self.config.pad_id
        
        views = [token_ids]  # Position 0 (no shift)
        
        for k in range(1, self.config.max_ngram_size):
            # Left-pad with pad_id and truncate to original length
            padded = np.pad(
                token_ids,
                ((0, 0), (k, 0)),
                mode="constant",
                constant_values=pad_id,
            )[:, :seq_len]
            views.append(padded)
        
        return views
    
    def _compute_ngram_hash(
        self,
        views: list[np.ndarray],
        n: int,
    ) -> list[np.ndarray]:
        """Compute hash values for a specific N-gram level.
        
        Uses polynomial rolling hash with XOR mixing:
        hash = (t[0] * m[0]) XOR (t[1] * m[1]) XOR ... XOR (t[n-1] * m[n-1])
        
        Args:
            views: List of shifted token arrays
            n: N-gram level (2, 3, etc.)
            
        Returns:
            List of hash arrays for each head
        """
        # Compute XOR-mixed hash
        mixed = views[0].astype(np.int64) * self.multipliers[0]
        for k in range(1, n):
            mixed = np.bitwise_xor(mixed, views[k].astype(np.int64) * self.multipliers[k])
        
        # Apply modulo for each head
        ngram_idx = n - 2  # 2-gram -> index 0, 3-gram -> index 1
        head_sizes = self.head_vocab_sizes[ngram_idx]
        
        head_hashes = []
        for head_idx, mod_value in enumerate(head_sizes):
            head_hash = np.mod(mixed, mod_value).astype(np.int64)
            head_hashes.append(head_hash)
        
        return head_hashes
    
    def hash(
        self,
        token_ids: np.ndarray | Sequence[Sequence[int]],
    ) -> NgramHashResult:
        """Compute N-gram hash indices for token sequences.
        
        Args:
            token_ids: Token IDs of shape [batch, seq_len] or list of lists
            
        Returns:
            NgramHashResult with hash indices and metadata
        """
        # Convert to numpy array
        arr = np.asarray(token_ids, dtype=np.int64)
        
        # Handle 1D input
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        
        batch_size, seq_len = arr.shape
        
        # Create shifted views
        views = self._create_shifted_views(arr)
        
        # Compute hashes for each N-gram level
        all_hashes = []
        for n in range(2, self.config.max_ngram_size + 1):
            head_hashes = self._compute_ngram_hash(views, n)
            all_hashes.extend(head_hashes)
        
        # Stack all hashes: [batch, seq_len, total_heads]
        hash_ids = np.stack(all_hashes, axis=-1)
        
        return NgramHashResult(
            hash_ids=hash_ids,
            ngram_ranges=self.ngram_ranges,
            metadata={
                "batch_size": batch_size,
                "seq_len": seq_len,
                "layer_id": self.layer_id,
                "max_ngram": self.config.max_ngram_size,
                "num_heads": self.config.num_heads,
            },
        )
    
    def hash_single(self, token_ids: Sequence[int]) -> np.ndarray:
        """Hash a single sequence of token IDs.
        
        Args:
            token_ids: Single sequence of token IDs
            
        Returns:
            Hash indices of shape [seq_len, total_heads]
        """
        result = self.hash([token_ids])
        return result.hash_ids[0]
    
    def get_embedding_offsets(self) -> list[int]:
        """Get embedding table offsets for each head.
        
        These offsets are used to map hash indices to positions in
        a unified embedding table.
        
        Returns:
            List of offsets for each head
        """
        offsets = [0]
        for ngram_idx, heads in enumerate(self.head_vocab_sizes):
            for head_size in heads:
                offsets.append(offsets[-1] + head_size)
        return offsets[:-1]  # Remove last (represents total size)
    
    def get_total_vocab_size(self) -> int:
        """Get total vocabulary size across all heads.
        
        Returns:
            Total number of unique hash buckets
        """
        total = 0
        for heads in self.head_vocab_sizes:
            total += sum(heads)
        return total
    
    def get_stats(self) -> dict[str, Any]:
        """Get hash mapping statistics.
        
        Returns:
            Dictionary with configuration and statistics
        """
        return {
            "layer_id": self.layer_id,
            "max_ngram_size": self.config.max_ngram_size,
            "num_heads": self.config.num_heads,
            "total_heads": self.total_heads,
            "vocab_sizes_per_ngram": self.head_vocab_sizes,
            "total_vocab_size": self.get_total_vocab_size(),
            "multipliers": self.multipliers.tolist(),
            "use_prime_modulo": self.config.use_prime_modulo,
        }


class MultiLayerHashMapping:
    """Hash mapping across multiple layers.
    
    Manages separate hash mappings for each layer, ensuring
    different hash functions per layer to reduce inter-layer collisions.
    """
    
    def __init__(
        self,
        config: HashConfig,
        layer_ids: list[int],
    ) -> None:
        """Initialize multi-layer hash mapping.
        
        Args:
            config: Hash configuration
            layer_ids: List of layer IDs to create mappings for
        """
        self.config = config
        self.layer_ids = layer_ids
        
        self.mappings: dict[int, NgramHashMapping] = {}
        for layer_id in layer_ids:
            self.mappings[layer_id] = NgramHashMapping(config, layer_id=layer_id)
    
    def hash(
        self,
        token_ids: np.ndarray,
        layer_id: int | None = None,
    ) -> dict[int, NgramHashResult] | NgramHashResult:
        """Compute hashes for one or all layers.
        
        Args:
            token_ids: Token IDs of shape [batch, seq_len]
            layer_id: Specific layer ID, or None for all layers
            
        Returns:
            Single result if layer_id specified, else dict of results
        """
        if layer_id is not None:
            if layer_id not in self.mappings:
                raise ValueError(f"Layer ID {layer_id} not in mappings")
            return self.mappings[layer_id].hash(token_ids)
        
        return {
            lid: mapping.hash(token_ids)
            for lid, mapping in self.mappings.items()
        }
    
    def get_layer_mapping(self, layer_id: int) -> NgramHashMapping:
        """Get hash mapping for a specific layer.
        
        Args:
            layer_id: Layer ID
            
        Returns:
            NgramHashMapping for the layer
        """
        if layer_id not in self.mappings:
            raise ValueError(f"Layer ID {layer_id} not in mappings")
        return self.mappings[layer_id]
    
    def __getitem__(self, layer_id: int) -> NgramHashMapping:
        """Get hash mapping by layer ID."""
        return self.get_layer_mapping(layer_id)


class TextHashMapping:
    """Direct text-to-hash mapping without tokenization.
    
    This class provides a simpler interface for hashing raw text
    using character-level N-grams.
    """
    
    def __init__(
        self,
        config: HashConfig | None = None,
        char_vocab_size: int = 256,
    ) -> None:
        """Initialize text hash mapping.
        
        Args:
            config: Hash configuration
            char_vocab_size: Size of character vocabulary (default: 256 for ASCII/UTF-8 bytes)
        """
        if config is None:
            from memu.engram.settings import HashConfig
            config = HashConfig()
        
        self.config = config
        self.char_vocab_size = char_vocab_size
        self.hash_mapping = NgramHashMapping(config)
    
    def text_to_ids(self, text: str) -> np.ndarray:
        """Convert text to character IDs.
        
        Args:
            text: Input text
            
        Returns:
            Array of character IDs
        """
        # Use UTF-8 byte representation
        bytes_data = text.encode("utf-8")
        return np.array(list(bytes_data), dtype=np.int64)
    
    def hash_text(self, text: str) -> NgramHashResult:
        """Hash a text string directly.
        
        Args:
            text: Input text
            
        Returns:
            Hash result
        """
        char_ids = self.text_to_ids(text)
        return self.hash_mapping.hash(char_ids.reshape(1, -1))
    
    def hash_texts(self, texts: list[str]) -> list[NgramHashResult]:
        """Hash multiple text strings.
        
        Args:
            texts: List of input texts
            
        Returns:
            List of hash results
        """
        return [self.hash_text(text) for text in texts]


__all__ = [
    "NgramHashMapping",
    "NgramHashResult",
    "MultiLayerHashMapping",
    "TextHashMapping",
    "is_prime",
    "find_next_prime",
]
