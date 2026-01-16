"""
Text Normalizer Module

This module provides text normalization functionality for Engram,
ensuring consistent token representation for N-gram hashing.
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from memu.engram.settings import NormalizerConfig


class TextNormalizer:
    """Text normalizer for consistent N-gram representation.
    
    This normalizer processes input text to create a canonical form
    that improves hash collision rates and memory efficiency.
    
    Features:
        - Unicode normalization (NFC, NFD, NFKC, NFKD)
        - Case folding (lowercase conversion)
        - Accent stripping
        - Whitespace collapsing
        - Custom character replacements
    
    Example:
        ```python
        from memu.engram.normalizer import TextNormalizer
        from memu.engram.settings import NormalizerConfig
        
        config = NormalizerConfig(lowercase=True, strip_accents=True)
        normalizer = TextNormalizer(config)
        
        text = "  Café   RÉSUMÉ  "
        normalized = normalizer.normalize(text)
        # Result: "cafe resume"
        ```
    """
    
    # Precompiled regex patterns for performance
    _WHITESPACE_PATTERN = re.compile(r"[\s\t\r\n]+")
    _COMBINING_MARKS_PATTERN = re.compile(r"[\u0300-\u036f]")
    
    def __init__(self, config: NormalizerConfig | None = None) -> None:
        """Initialize the text normalizer.
        
        Args:
            config: Normalization configuration. If None, uses default settings.
        """
        if config is None:
            from memu.engram.settings import NormalizerConfig
            config = NormalizerConfig()
        
        self.config = config
        self._custom_patterns: list[tuple[re.Pattern, str]] = []
        
        # Compile custom replacement patterns
        for pattern, replacement in config.custom_replacements.items():
            self._custom_patterns.append((re.compile(pattern), replacement))
    
    def normalize(self, text: str) -> str:
        """Normalize a text string.
        
        Applies the following transformations in order:
        1. Unicode normalization
        2. Accent stripping (if enabled)
        3. Lowercase conversion (if enabled)
        4. Whitespace collapsing (if enabled)
        5. Custom replacements
        6. Strip leading/trailing whitespace
        
        Args:
            text: Input text to normalize
            
        Returns:
            Normalized text string
        """
        if not text:
            return ""
        
        result = text
        
        # Step 1: Unicode normalization
        result = unicodedata.normalize(self.config.unicode_form, result)
        
        # Step 2: Strip accents (decompose and remove combining marks)
        if self.config.strip_accents:
            # Decompose characters first if not already NFD/NFKD
            if self.config.unicode_form not in ("NFD", "NFKD"):
                result = unicodedata.normalize("NFD", result)
            # Remove combining marks (accents)
            result = self._COMBINING_MARKS_PATTERN.sub("", result)
            # Re-apply the configured normalization form
            result = unicodedata.normalize(self.config.unicode_form, result)
        
        # Step 3: Lowercase conversion
        if self.config.lowercase:
            result = result.lower()
        
        # Step 4: Whitespace collapsing
        if self.config.collapse_whitespace:
            result = self._WHITESPACE_PATTERN.sub(" ", result)
        
        # Step 5: Custom replacements
        for pattern, replacement in self._custom_patterns:
            result = pattern.sub(replacement, result)
        
        # Step 6: Strip leading/trailing whitespace
        result = result.strip()
        
        return result
    
    def normalize_batch(self, texts: list[str]) -> list[str]:
        """Normalize a batch of text strings.
        
        Args:
            texts: List of input texts to normalize
            
        Returns:
            List of normalized text strings
        """
        return [self.normalize(text) for text in texts]
    
    @lru_cache(maxsize=10000)
    def normalize_cached(self, text: str) -> str:
        """Normalize text with LRU caching.
        
        Use this for frequently repeated normalizations.
        
        Args:
            text: Input text to normalize
            
        Returns:
            Normalized text string
        """
        return self.normalize(text)
    
    def clear_cache(self) -> None:
        """Clear the normalization cache."""
        self.normalize_cached.cache_clear()
    
    def get_cache_info(self) -> dict[str, int]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache hits, misses, size, and max size
        """
        info = self.normalize_cached.cache_info()
        return {
            "hits": info.hits,
            "misses": info.misses,
            "current_size": info.currsize,
            "max_size": info.maxsize,
        }


class TokenNormalizer:
    """Token-level normalizer for vocabulary compression.
    
    This normalizer processes tokenized sequences to create a compressed
    vocabulary mapping, reducing collision rates in N-gram hashing.
    
    It builds a lookup table that maps original token IDs to compressed IDs,
    grouping tokens that normalize to the same text representation.
    """
    
    def __init__(
        self,
        text_normalizer: TextNormalizer | None = None,
        vocab_size: int | None = None,
    ) -> None:
        """Initialize the token normalizer.
        
        Args:
            text_normalizer: Text normalizer instance. If None, creates default.
            vocab_size: Original vocabulary size. If None, built lazily.
        """
        self.text_normalizer = text_normalizer or TextNormalizer()
        self._vocab_size = vocab_size
        self._lookup_table: dict[int, int] | None = None
        self._reverse_lookup: dict[int, list[int]] | None = None
        self._compressed_vocab_size: int = 0
    
    def build_lookup_table(
        self,
        token_to_text: dict[int, str],
    ) -> None:
        """Build the token compression lookup table.
        
        This method creates a mapping from original token IDs to compressed IDs,
        grouping tokens that normalize to the same text representation.
        
        Args:
            token_to_text: Mapping from token ID to text representation
        """
        # Maps normalized text -> compressed ID
        text_to_compressed: dict[str, int] = {}
        
        # Maps original ID -> compressed ID
        self._lookup_table = {}
        
        # Maps compressed ID -> list of original IDs
        self._reverse_lookup = {}
        
        compressed_counter = 0
        
        for token_id, text in sorted(token_to_text.items()):
            # Handle special tokens (decode errors)
            if "�" in text or not text:
                # Keep as unique entry
                normalized = f"__special_{token_id}__"
            else:
                normalized = self.text_normalizer.normalize(text)
                if not normalized:
                    normalized = text  # Fallback to original
            
            if normalized not in text_to_compressed:
                text_to_compressed[normalized] = compressed_counter
                self._reverse_lookup[compressed_counter] = []
                compressed_counter += 1
            
            compressed_id = text_to_compressed[normalized]
            self._lookup_table[token_id] = compressed_id
            self._reverse_lookup[compressed_id].append(token_id)
        
        self._compressed_vocab_size = compressed_counter
        self._vocab_size = len(token_to_text)
    
    def build_from_tokenizer(self, tokenizer: "Any") -> None:
        """Build lookup table from a HuggingFace tokenizer.
        
        Args:
            tokenizer: HuggingFace tokenizer instance
        """
        vocab_size = len(tokenizer)
        token_to_text = {}
        
        for token_id in range(vocab_size):
            try:
                text = tokenizer.decode([token_id], skip_special_tokens=False)
                token_to_text[token_id] = text
            except Exception:
                token_to_text[token_id] = f"__error_{token_id}__"
        
        self.build_lookup_table(token_to_text)
    
    def compress(self, token_id: int) -> int:
        """Compress a single token ID.
        
        Args:
            token_id: Original token ID
            
        Returns:
            Compressed token ID
            
        Raises:
            ValueError: If lookup table not built or token_id not found
        """
        if self._lookup_table is None:
            raise ValueError("Lookup table not built. Call build_lookup_table() first.")
        
        if token_id not in self._lookup_table:
            raise ValueError(f"Token ID {token_id} not in vocabulary")
        
        return self._lookup_table[token_id]
    
    def compress_batch(self, token_ids: list[int]) -> list[int]:
        """Compress a batch of token IDs.
        
        Args:
            token_ids: List of original token IDs
            
        Returns:
            List of compressed token IDs
        """
        return [self.compress(tid) for tid in token_ids]
    
    def compress_numpy(self, token_ids: "Any") -> "Any":
        """Compress token IDs using NumPy for efficiency.
        
        Args:
            token_ids: NumPy array of original token IDs
            
        Returns:
            NumPy array of compressed token IDs
        """
        import numpy as np
        
        if self._lookup_table is None:
            raise ValueError("Lookup table not built. Call build_lookup_table() first.")
        
        # Convert lookup table to numpy array for vectorized lookup
        max_id = max(self._lookup_table.keys())
        lookup_array = np.zeros(max_id + 1, dtype=np.int64)
        for orig_id, comp_id in self._lookup_table.items():
            lookup_array[orig_id] = comp_id
        
        arr = np.asarray(token_ids, dtype=np.int64)
        result = np.take(lookup_array, arr, mode="clip")
        
        return result
    
    @property
    def original_vocab_size(self) -> int:
        """Get original vocabulary size."""
        return self._vocab_size or 0
    
    @property
    def compressed_vocab_size(self) -> int:
        """Get compressed vocabulary size."""
        return self._compressed_vocab_size
    
    @property
    def compression_ratio(self) -> float:
        """Get compression ratio (original / compressed)."""
        if self._compressed_vocab_size == 0:
            return 0.0
        return self.original_vocab_size / self._compressed_vocab_size
    
    def get_stats(self) -> dict[str, int | float]:
        """Get vocabulary compression statistics.
        
        Returns:
            Dictionary with compression statistics
        """
        return {
            "original_vocab_size": self.original_vocab_size,
            "compressed_vocab_size": self.compressed_vocab_size,
            "compression_ratio": self.compression_ratio,
            "tokens_saved": self.original_vocab_size - self._compressed_vocab_size,
        }


class CharacterNormalizer:
    """Character-level normalizer for direct text processing.
    
    This normalizer works on raw character sequences without tokenization,
    useful for simple text-based N-gram hashing.
    """
    
    # Character categories to remove
    REMOVE_CATEGORIES = {"Mn", "Mc", "Me", "Cf"}  # Marks and format characters
    
    def __init__(
        self,
        lowercase: bool = True,
        remove_accents: bool = True,
        remove_punctuation: bool = False,
        max_consecutive_chars: int = 3,
    ) -> None:
        """Initialize character normalizer.
        
        Args:
            lowercase: Whether to convert to lowercase
            remove_accents: Whether to remove accent marks
            remove_punctuation: Whether to remove punctuation
            max_consecutive_chars: Maximum consecutive identical characters
        """
        self.lowercase = lowercase
        self.remove_accents = remove_accents
        self.remove_punctuation = remove_punctuation
        self.max_consecutive_chars = max_consecutive_chars
        
        # Precompile patterns
        if remove_punctuation:
            self._punct_pattern = re.compile(r"[^\w\s]", re.UNICODE)
        else:
            self._punct_pattern = None
        
        self._repeat_pattern = re.compile(r"(.)\1{" + str(max_consecutive_chars) + r",}")
    
    def normalize(self, text: str) -> str:
        """Normalize text at character level.
        
        Args:
            text: Input text
            
        Returns:
            Normalized text
        """
        if not text:
            return ""
        
        result = text
        
        # Remove accents via NFD decomposition
        if self.remove_accents:
            result = unicodedata.normalize("NFD", result)
            result = "".join(
                char for char in result
                if unicodedata.category(char) not in self.REMOVE_CATEGORIES
            )
            result = unicodedata.normalize("NFC", result)
        
        # Lowercase
        if self.lowercase:
            result = result.lower()
        
        # Remove punctuation
        if self._punct_pattern:
            result = self._punct_pattern.sub("", result)
        
        # Limit consecutive characters
        if self.max_consecutive_chars > 0:
            result = self._repeat_pattern.sub(
                r"\1" * self.max_consecutive_chars, result
            )
        
        return result


__all__ = [
    "TextNormalizer",
    "TokenNormalizer", 
    "CharacterNormalizer",
]
