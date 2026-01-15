"""
Engram Module Tests

Comprehensive test suite for the Engram memory system.
Run with: python -m pytest tests/test_engram.py -v
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import numpy as np
import pytest


# ============================================================================
# Test Configuration
# ============================================================================

class TestEngramConfig:
    """Tests for Engram configuration classes."""
    
    def test_default_config(self):
        """Test default configuration creation."""
        from memu.engram import EngramConfig
        
        config = EngramConfig()
        
        assert config.enabled is True
        assert config.hash.max_ngram_size == 3
        assert config.hash.num_heads == 8
        assert len(config.hash.vocab_sizes) == 2
        assert config.embedding.embedding_dim == 64
    
    def test_config_validation(self):
        """Test configuration validation."""
        from memu.engram import EngramConfig, HashConfig
        
        # Invalid: vocab_sizes length mismatch
        with pytest.raises(ValueError, match="vocab_sizes"):
            EngramConfig(
                hash=HashConfig(
                    max_ngram_size=3,
                    vocab_sizes=[100000],  # Should be 2 elements
                ),
            )
    
    def test_preset_configs(self):
        """Test preset configuration functions."""
        from memu.engram import (
            get_lightweight_config,
            get_standard_config,
        )
        
        light = get_lightweight_config()
        assert light.hash.max_ngram_size == 2
        assert light.hash.num_heads == 4
        
        standard = get_standard_config()
        assert standard.hash.max_ngram_size == 3
        assert standard.hash.num_heads == 8
    
    def test_memory_estimation(self):
        """Test memory usage estimation."""
        from memu.engram import EngramConfig, HashConfig, EmbeddingConfig
        
        config = EngramConfig(
            hash=HashConfig(
                max_ngram_size=3,
                num_heads=8,
                vocab_sizes=[100000, 100000],
            ),
            embedding=EmbeddingConfig(
                embedding_dim=64,
            ),
        )
        
        # Should be able to estimate memory
        bytes_usage = config.estimate_memory_usage_bytes()
        assert bytes_usage > 0
        
        human = config.estimate_memory_usage_human()
        assert "MB" in human or "GB" in human
    
    def test_config_serialization(self):
        """Test configuration to/from dict."""
        from memu.engram import EngramConfig
        
        config = EngramConfig()
        data = config.to_dict()
        
        assert isinstance(data, dict)
        assert "hash" in data
        assert "embedding" in data
        
        # Reconstruct from dict
        config2 = EngramConfig.from_dict(data)
        assert config2.hash.max_ngram_size == config.hash.max_ngram_size


# ============================================================================
# Test Normalizer
# ============================================================================

class TestNormalizer:
    """Tests for text normalization."""
    
    def test_text_normalizer_basic(self):
        """Test basic text normalization."""
        from memu.engram import TextNormalizer, NormalizerConfig
        
        config = NormalizerConfig(
            lowercase=True,
            strip_accents=True,
            collapse_whitespace=True,
        )
        normalizer = TextNormalizer(config)
        
        # Test lowercase
        assert normalizer.normalize("HELLO") == "hello"
        
        # Test whitespace collapse
        assert normalizer.normalize("  hello   world  ") == "hello world"
        
        # Test accents
        assert normalizer.normalize("café") == "cafe"
    
    def test_text_normalizer_cache(self):
        """Test normalization caching."""
        from memu.engram import TextNormalizer
        
        normalizer = TextNormalizer()
        
        # First call
        result1 = normalizer.normalize_cached("test string")
        
        # Second call should hit cache
        result2 = normalizer.normalize_cached("test string")
        
        assert result1 == result2
        
        # Check cache stats
        stats = normalizer.get_cache_info()
        assert stats["hits"] >= 1


# ============================================================================
# Test Hash Mapping
# ============================================================================

class TestHashMapping:
    """Tests for N-gram hash mapping."""
    
    def test_hash_basic(self):
        """Test basic hash computation."""
        from memu.engram import NgramHashMapping, HashConfig
        
        config = HashConfig(
            max_ngram_size=3,
            num_heads=4,
            vocab_sizes=[10000, 10000],
        )
        hasher = NgramHashMapping(config)
        
        # Hash a sequence
        token_ids = np.array([[1, 2, 3, 4, 5]])
        result = hasher.hash(token_ids)
        
        # Check shape
        assert result.hash_ids.shape == (1, 5, 8)  # 2 ngram levels * 4 heads
        
        # Check values are within bounds
        assert np.all(result.hash_ids >= 0)
    
    def test_hash_deterministic(self):
        """Test hash is deterministic."""
        from memu.engram import NgramHashMapping, HashConfig
        
        config = HashConfig(seed=42)
        hasher = NgramHashMapping(config)
        
        token_ids = np.array([[1, 2, 3]])
        
        result1 = hasher.hash(token_ids)
        result2 = hasher.hash(token_ids)
        
        np.testing.assert_array_equal(result1.hash_ids, result2.hash_ids)
    
    def test_hash_layer_specific(self):
        """Test layer-specific hashing."""
        from memu.engram import NgramHashMapping, HashConfig
        
        config = HashConfig(seed=42)
        
        hasher0 = NgramHashMapping(config, layer_id=0)
        hasher1 = NgramHashMapping(config, layer_id=1)
        
        token_ids = np.array([[1, 2, 3]])
        
        result0 = hasher0.hash(token_ids)
        result1 = hasher1.hash(token_ids)
        
        # Different layers should produce different hashes
        assert not np.array_equal(result0.hash_ids, result1.hash_ids)
    
    def test_ngram_ranges(self):
        """Test N-gram range extraction."""
        from memu.engram import NgramHashMapping, HashConfig
        
        config = HashConfig(
            max_ngram_size=3,
            num_heads=4,
            vocab_sizes=[10000, 10000],
        )
        hasher = NgramHashMapping(config)
        
        token_ids = np.array([[1, 2, 3, 4, 5]])
        result = hasher.hash(token_ids)
        
        # Get 2-gram hashes
        bigram_hashes = result.get_ngram_hashes(2)
        assert bigram_hashes.shape == (1, 5, 4)
        
        # Get 3-gram hashes
        trigram_hashes = result.get_ngram_hashes(3)
        assert trigram_hashes.shape == (1, 5, 4)


# ============================================================================
# Test Embedding Storage
# ============================================================================

class TestEmbeddingStorage:
    """Tests for embedding storage backends."""
    
    def test_inmemory_storage(self):
        """Test in-memory storage."""
        from memu.engram.storage import InMemoryStorage
        
        storage = InMemoryStorage(
            num_embeddings=1000,
            embedding_dim=64,
        )
        
        assert storage.shape == (1000, 64)
        
        # Load some embeddings
        indices = np.array([0, 1, 2])
        embeddings = storage.load(indices)
        
        assert embeddings.shape == (3, 64)
        
        # Update embeddings
        new_values = np.random.randn(3, 64).astype(np.float32)
        storage.update(indices, new_values)
        
        loaded = storage.load(indices)
        np.testing.assert_array_almost_equal(loaded, new_values)
        
        storage.close()
    
    def test_mmap_storage(self):
        """Test memory-mapped storage."""
        from memu.engram.storage import MMapStorage
        
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_mmap.bin"
            
            # Create new storage
            storage = MMapStorage(
                path=path,
                num_embeddings=1000,
                embedding_dim=64,
                mode="w+",
            )
            
            assert storage.shape == (1000, 64)
            
            # Write some data
            indices = np.array([0, 1, 2])
            new_values = np.random.randn(3, 64).astype(np.float32)
            storage.update(indices, new_values)
            storage.close()
            
            # Reopen and verify
            storage2 = MMapStorage(path=path, mode="r+")
            loaded = storage2.load(indices)
            np.testing.assert_array_almost_equal(loaded, new_values)
            storage2.close()
    
    def test_hybrid_storage(self):
        """Test hybrid storage with caching."""
        from memu.engram.storage import HybridStorage
        
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_hybrid.bin"
            
            storage = HybridStorage(
                path=path,
                num_embeddings=1000,
                embedding_dim=64,
                hot_cache_size=100,
            )
            
            # Load same indices multiple times
            indices = np.array([0, 1, 2])
            
            _ = storage.load(indices)  # First load: miss
            _ = storage.load(indices)  # Second load: hit
            
            stats = storage.get_cache_stats()
            assert stats["hits"] > 0
            
            storage.close()


# ============================================================================
# Test Multi-Head Embedding Table
# ============================================================================

class TestMultiHeadEmbedding:
    """Tests for multi-head embedding table."""
    
    def test_basic_lookup(self):
        """Test basic embedding lookup."""
        from memu.engram import MultiHeadEmbeddingTable, EmbeddingConfig
        
        config = EmbeddingConfig(embedding_dim=32)
        
        table = MultiHeadEmbeddingTable(
            head_vocab_sizes=[1000, 1000, 1000, 1000],
            embedding_dim=32,
            config=config,
        )
        
        assert table.num_heads == 4
        assert table.total_vocab_size == 4000
        
        # Lookup
        hash_ids = np.array([[[0, 0, 0, 0], [1, 1, 1, 1]]])  # [1, 2, 4]
        result = table.lookup(hash_ids)
        
        assert result.embeddings.shape == (1, 2, 4, 32)
        assert result.flat_embeddings.shape == (1, 2, 128)
        
        table.close()
    
    def test_offset_computation(self):
        """Test embedding offset computation."""
        from memu.engram import MultiHeadEmbeddingTable, EmbeddingConfig
        
        config = EmbeddingConfig(embedding_dim=32)
        
        table = MultiHeadEmbeddingTable(
            head_vocab_sizes=[100, 200, 300],
            embedding_dim=32,
            config=config,
        )
        
        expected_offsets = np.array([0, 100, 300])
        np.testing.assert_array_equal(table.offsets, expected_offsets)
        
        table.close()


# ============================================================================
# Test Gating
# ============================================================================

class TestGating:
    """Tests for gating mechanisms."""
    
    def test_simple_gating(self):
        """Test simple gating."""
        from memu.engram import SimpleGating, GatingConfig
        
        config = GatingConfig(hidden_dim=64)
        gating = SimpleGating(
            memory_dim=128,
            output_dim=64,
            config=config,
        )
        
        memory = np.random.randn(2, 10, 128).astype(np.float32)
        result = gating(memory)
        
        assert result.gates.shape == (2, 10)
        assert result.gated_memory.shape == (2, 10, 64)
        assert result.raw_scores.shape == (2, 10)
    
    def test_engram_gating(self):
        """Test Engram-style gating with query."""
        from memu.engram import EngramGating, GatingConfig
        
        config = GatingConfig(hidden_dim=64)
        gating = EngramGating(
            input_dim=64,
            memory_dim=128,
            output_dim=64,
            num_channels=2,
            config=config,
        )
        
        query = np.random.randn(2, 10, 64).astype(np.float32)
        memory = np.random.randn(2, 10, 128).astype(np.float32)
        
        result = gating(query, memory)
        
        assert result.gates.shape == (2, 10, 2)
        assert result.gated_memory.shape == (2, 10, 2, 64)
    
    def test_short_conv(self):
        """Test short convolution."""
        from memu.engram import ShortConv1D
        
        conv = ShortConv1D(
            channels=64,
            kernel_size=4,
            dilation=1,
        )
        
        x = np.random.randn(2, 10, 64).astype(np.float32)
        y = conv(x)
        
        assert y.shape == x.shape


# ============================================================================
# Test Engram Service
# ============================================================================

class TestEngramService:
    """Tests for the main Engram service."""
    
    def test_basic_retrieval(self):
        """Test basic memory retrieval."""
        from memu.engram import EngramService, get_lightweight_config
        
        config = get_lightweight_config()
        service = EngramService(config)
        
        # Retrieve for token sequence
        token_ids = np.array([[1, 2, 3, 4, 5]])
        result = service.retrieve(token_ids)
        
        assert result.gate_values.shape[0] == 1
        assert result.gate_values.shape[1] == 5
        assert result.gated_output is not None
        
        service.close()
    
    def test_batch_retrieval(self):
        """Test batch retrieval."""
        from memu.engram import EngramService, get_lightweight_config
        
        config = get_lightweight_config()
        service = EngramService(config)
        
        # Multiple sequences
        token_ids = np.array([
            [1, 2, 3, 4, 5],
            [6, 7, 8, 9, 10],
            [11, 12, 13, 14, 15],
        ])
        result = service.retrieve(token_ids)
        
        assert result.gate_values.shape[0] == 3
        
        service.close()
    
    def test_context_manager(self):
        """Test context manager usage."""
        from memu.engram import EngramService, get_lightweight_config
        
        config = get_lightweight_config()
        
        with EngramService(config) as service:
            token_ids = [[1, 2, 3]]
            result = service.retrieve(token_ids)
            assert result is not None
    
    def test_save_load(self):
        """Test save and load functionality."""
        from memu.engram import EngramService, get_lightweight_config
        
        config = get_lightweight_config()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "engram_state"
            
            # Create and save
            with EngramService(config) as service:
                token_ids = [[1, 2, 3]]
                result1 = service.retrieve(token_ids)
                service.save(save_path)
            
            # Load and verify
            with EngramService(config) as service2:
                service2.load(save_path)
                result2 = service2.retrieve(token_ids)
                
                # Results should be similar
                np.testing.assert_array_almost_equal(
                    result1.gate_values,
                    result2.gate_values,
                    decimal=5,
                )
    
    def test_metrics_collection(self):
        """Test metrics collection."""
        from memu.engram import EngramService, get_lightweight_config
        
        config = get_lightweight_config()
        config.collect_metrics = True
        
        with EngramService(config) as service:
            for _ in range(5):
                service.retrieve([[1, 2, 3, 4, 5]])
            
            stats = service.get_stats()
            assert "metrics" in stats
            assert stats["metrics"]["num_calls"] == 5
    
    def test_get_stats(self):
        """Test statistics retrieval."""
        from memu.engram import EngramService, get_lightweight_config
        
        config = get_lightweight_config()
        
        with EngramService(config) as service:
            stats = service.get_stats()
            
            assert "config" in stats
            assert "memory" in stats
            assert "hash_mapping" in stats
            assert "embedding_table" in stats


# ============================================================================
# Test Text Engram Service
# ============================================================================

class TestTextEngramService:
    """Tests for text-based Engram service."""
    
    def test_add_and_query(self):
        """Test adding and querying memories."""
        from memu.engram import TextEngramService, get_lightweight_config
        
        config = get_lightweight_config()
        service = TextEngramService(config)
        
        # Add memories
        service.add_memory("The capital of France is Paris")
        service.add_memory("Python is a programming language")
        service.add_memory("Machine learning is a subset of AI")
        
        # Query
        result = service.query("What is the capital of France?", top_k=2)
        
        assert len(result.top_k_indices) == 2
        assert result.top_k_embeddings.shape[0] == 2
        
        service.close()
    
    def test_clear_memories(self):
        """Test clearing memories."""
        from memu.engram import TextEngramService, get_lightweight_config
        
        config = get_lightweight_config()
        service = TextEngramService(config)
        
        service.add_memory("Test memory")
        assert len(service._memories) == 1
        
        service.clear_memories()
        assert len(service._memories) == 0
        
        service.close()


# ============================================================================
# Test Factory Functions
# ============================================================================

class TestFactory:
    """Tests for factory functions."""
    
    def test_create_engram_service(self):
        """Test service creation via factory."""
        from memu.engram import create_engram_service
        
        service = create_engram_service(
            storage_backend="memory",
            max_ngram_size=2,
            num_heads=4,
            embedding_dim=32,
        )
        
        assert service.config.hash.max_ngram_size == 2
        assert service.config.hash.num_heads == 4
        assert service.config.embedding.embedding_dim == 32
        
        service.close()
    
    def test_create_with_mmap(self):
        """Test service creation with mmap storage."""
        from memu.engram import create_engram_service
        
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "engram.bin"
            
            service = create_engram_service(
                storage_path=path,
                storage_backend="mmap",
                max_ngram_size=2,
                num_heads=4,
            )
            
            result = service.retrieve([[1, 2, 3]])
            assert result is not None
            
            service.close()
            
            # File should exist
            assert path.exists()


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for complete workflows."""
    
    def test_end_to_end_workflow(self):
        """Test complete end-to-end workflow."""
        from memu.engram import (
            EngramService,
            EngramConfig,
            HashConfig,
            EmbeddingConfig,
            GatingConfig,
            StorageBackend,
        )
        
        # Configure
        config = EngramConfig(
            hash=HashConfig(
                max_ngram_size=2,
                num_heads=4,
                vocab_sizes=[10000],
            ),
            embedding=EmbeddingConfig(
                embedding_dim=32,
                storage_backend=StorageBackend.MEMORY,
            ),
            gating=GatingConfig(
                hidden_dim=64,
            ),
            collect_metrics=True,
        )
        
        # Create service
        with EngramService(config) as service:
            # Retrieve memories
            batch = np.array([
                [100, 200, 300, 400, 500],
                [600, 700, 800, 900, 1000],
            ])
            
            result = service.retrieve(batch)
            
            # Verify output shapes
            assert result.gate_values.shape == (2, 5)
            assert result.hash_result.hash_ids.shape == (2, 5, 4)
            
            # Check metrics
            stats = service.get_stats()
            assert stats["metrics"]["num_calls"] == 1
    
    def test_persistence_workflow(self):
        """Test persistence across service instances."""
        from memu.engram import EngramService, get_lightweight_config
        
        config = get_lightweight_config()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "state"
            
            token_ids = [[42, 43, 44, 45, 46]]
            
            # First session
            with EngramService(config) as service1:
                result1 = service1.retrieve(token_ids)
                service1.save(save_path)
            
            # Second session
            with EngramService(config) as service2:
                service2.load(save_path)
                result2 = service2.retrieve(token_ids)
            
            # Should get same results
            np.testing.assert_array_almost_equal(
                result1.gated_output,
                result2.gated_output,
                decimal=5,
            )


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
