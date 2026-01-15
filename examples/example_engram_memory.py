"""
Engram Usage Example

This example demonstrates how to use the Engram module for
storage-compute separated memory retrieval in the memU framework.

Features demonstrated:
    1. Basic configuration and service creation
    2. Memory retrieval with token sequences
    3. Different storage backends
    4. Text-based memory operations
    5. Metrics collection and analysis

Run with:
    cd memU
    python examples/example_engram_memory.py
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import numpy as np


def example_basic_usage():
    """Example 1: Basic Engram usage with default configuration."""
    print("\n" + "=" * 60)
    print("Example 1: Basic Engram Usage")
    print("=" * 60)
    
    from memu.engram import EngramService, get_lightweight_config
    
    # Use lightweight config for quick demo
    config = get_lightweight_config()
    print(f"Memory usage estimate: {config.estimate_memory_usage_human()}")
    
    # Create service
    with EngramService(config) as service:
        # Simulate token IDs (in production, use a tokenizer)
        token_ids = np.array([
            [100, 200, 300, 400, 500],
            [600, 700, 800, 900, 1000],
        ])
        
        # Retrieve memories
        result = service.retrieve(token_ids)
        
        print(f"Input shape: {token_ids.shape}")
        print(f"Gate values shape: {result.gate_values.shape}")
        print(f"Gated output shape: {result.gated_output.shape}")
        print(f"Hash IDs shape: {result.hash_result.hash_ids.shape}")
        
        # Show gate statistics
        print(f"\nGate statistics:")
        print(f"  Mean: {result.gate_values.mean():.4f}")
        print(f"  Std:  {result.gate_values.std():.4f}")
        print(f"  Min:  {result.gate_values.min():.4f}")
        print(f"  Max:  {result.gate_values.max():.4f}")


def example_custom_configuration():
    """Example 2: Custom Engram configuration."""
    print("\n" + "=" * 60)
    print("Example 2: Custom Configuration")
    print("=" * 60)
    
    from memu.engram import (
        EngramService,
        EngramConfig,
        HashConfig,
        EmbeddingConfig,
        GatingConfig,
        StorageBackend,
        QuantizationType,
    )
    
    # Create custom configuration
    config = EngramConfig(
        hash=HashConfig(
            max_ngram_size=3,     # Use 2-gram and 3-gram
            num_heads=8,          # 8 hash heads per N-gram level
            vocab_sizes=[320000, 320000],
            seed=42,
        ),
        embedding=EmbeddingConfig(
            embedding_dim=64,
            storage_backend=StorageBackend.MEMORY,
            quantization=QuantizationType.FP16,  # Use FP16 for memory efficiency
            init_method="normal",
            init_scale=0.02,
        ),
        gating=GatingConfig(
            hidden_dim=256,
            use_layer_norm=True,
            activation="sigmoid",
            sqrt_scaling=True,  # Use Engram-style sqrt scaling
        ),
        collect_metrics=True,
    )
    
    print(f"Configuration:")
    print(f"  Max N-gram size: {config.hash.max_ngram_size}")
    print(f"  Num heads: {config.hash.num_heads}")
    print(f"  Embedding dim: {config.embedding.embedding_dim}")
    print(f"  Total embeddings: {config.get_total_embedding_entries():,}")
    print(f"  Memory usage: {config.estimate_memory_usage_human()}")
    
    with EngramService(config) as service:
        # Multiple retrieval calls
        for i in range(5):
            token_ids = np.random.randint(0, 10000, (4, 20))
            _ = service.retrieve(token_ids)
        
        # Get statistics
        stats = service.get_stats()
        print(f"\nService statistics:")
        print(f"  Storage backend: {stats['config']['storage_backend']}")
        print(f"  Total entries: {stats['memory']['total_entries']:,}")
        print(f"  Metrics: {stats.get('metrics', {})}")


def example_persistent_storage():
    """Example 3: Persistent storage with memory-mapped files."""
    print("\n" + "=" * 60)
    print("Example 3: Persistent Storage (Memory-Mapped)")
    print("=" * 60)
    
    from memu.engram import (
        EngramService,
        EngramConfig,
        HashConfig,
        EmbeddingConfig,
        StorageBackend,
    )
    
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "engram_embeddings.bin"
        
        # Configuration with mmap storage
        config = EngramConfig(
            hash=HashConfig(
                max_ngram_size=2,
                num_heads=4,
                vocab_sizes=[50_000],
            ),
            embedding=EmbeddingConfig(
                embedding_dim=32,
                storage_backend=StorageBackend.MMAP,
                storage_path=storage_path,
            ),
        )
        
        # First session: create and save
        print("Session 1: Create and save")
        with EngramService(config) as service:
            token_ids = np.array([[1, 2, 3, 4, 5]])
            result1 = service.retrieve(token_ids)
            print(f"  Output sum: {result1.gated_output.sum():.4f}")
            
            # Save state
            state_path = Path(tmpdir) / "state"
            service.save(state_path)
            print(f"  Saved to: {state_path}")
        
        # Second session: load and verify
        print("\nSession 2: Load and verify")
        with EngramService(config) as service:
            service.load(state_path)
            result2 = service.retrieve(token_ids)
            print(f"  Output sum: {result2.gated_output.sum():.4f}")
            
            # Verify consistency
            diff = np.abs(result1.gated_output - result2.gated_output).max()
            print(f"  Max difference: {diff:.6f}")
        
        print(f"\nStorage file size: {storage_path.stat().st_size / 1024:.1f} KB")


def example_hybrid_storage():
    """Example 4: Hybrid storage with hot cache."""
    print("\n" + "=" * 60)
    print("Example 4: Hybrid Storage (Hot Cache + Cold Disk)")
    print("=" * 60)
    
    from memu.engram import (
        EngramService,
        EngramConfig,
        HashConfig,
        EmbeddingConfig,
        StorageBackend,
    )
    
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "engram_hybrid.bin"
        
        # Configuration with hybrid storage
        config = EngramConfig(
            hash=HashConfig(
                max_ngram_size=2,
                num_heads=4,
                vocab_sizes=[100_000],
            ),
            embedding=EmbeddingConfig(
                embedding_dim=32,
                storage_backend=StorageBackend.HYBRID,
                storage_path=storage_path,
                hot_cache_size=10000,  # Keep 10K embeddings in memory
            ),
        )
        
        print(f"Configuration:")
        print(f"  Hot cache size: {config.embedding.hot_cache_size}")
        print(f"  Total embeddings: {config.get_total_embedding_entries():,}")
        
        with EngramService(config) as service:
            # Simulate repeated access patterns (cache should help)
            print("\nAccess pattern simulation:")
            
            # Frequently accessed sequence
            hot_tokens = np.array([[1, 2, 3, 4, 5]])
            
            # Cold sequences (random)
            for i in range(10):
                # Access hot tokens (should hit cache)
                _ = service.retrieve(hot_tokens)
                
                # Access cold tokens
                cold_tokens = np.random.randint(0, 10000, (1, 5))
                _ = service.retrieve(cold_tokens)
            
            # Get cache statistics
            stats = service.get_stats()
            if "cache" in stats.get("embedding_table", {}):
                cache_stats = stats["embedding_table"]["cache"]
                print(f"\nCache statistics:")
                print(f"  Hits: {cache_stats['hits']}")
                print(f"  Misses: {cache_stats['misses']}")
                print(f"  Hit rate: {cache_stats['hit_rate']:.2%}")


def example_text_based_memory():
    """Example 5: Text-based memory operations."""
    print("\n" + "=" * 60)
    print("Example 5: Text-Based Memory Operations")
    print("=" * 60)
    
    from memu.engram import TextEngramService, get_lightweight_config
    
    config = get_lightweight_config()
    service = TextEngramService(config)
    
    # Add memories
    memories = [
        "The capital of France is Paris.",
        "Python is a popular programming language.",
        "Machine learning is a subset of artificial intelligence.",
        "The Eiffel Tower is located in Paris.",
        "JavaScript is used for web development.",
        "Deep learning uses neural networks.",
    ]
    
    print("Adding memories:")
    for i, memory in enumerate(memories):
        idx = service.add_memory(memory)
        print(f"  [{idx}] {memory[:50]}...")
    
    # Query
    queries = [
        "What is the capital city of France?",
        "Tell me about programming languages",
        "What is AI?",
    ]
    
    print("\nQuerying memories:")
    for query in queries:
        result = service.query(query, top_k=2)
        print(f"\n  Query: {query}")
        print(f"  Top matches:")
        for i, idx in enumerate(result.top_k_indices):
            score = result.memory_scores[idx]
            memory = service.get_memory(idx)
            print(f"    [{i+1}] Score: {score:.4f} - {memory.text[:40]}...")
    
    service.close()


def example_query_based_gating():
    """Example 6: Query-based gating for conditional retrieval."""
    print("\n" + "=" * 60)
    print("Example 6: Query-Based Gating")
    print("=" * 60)
    
    from memu.engram import EngramService, get_lightweight_config
    
    config = get_lightweight_config()
    config.gating.hidden_dim = 128
    
    with EngramService(config) as service:
        # Token sequence
        token_ids = np.array([[100, 200, 300, 400, 500]])
        
        # Different query contexts
        query_dim = 128
        
        # Query 1: Random context
        query1 = np.random.randn(1, 5, query_dim).astype(np.float32)
        result1 = service.retrieve_with_query(token_ids, query1, num_channels=2)
        
        # Query 2: Different context
        query2 = np.random.randn(1, 5, query_dim).astype(np.float32) * 2
        result2 = service.retrieve_with_query(token_ids, query2, num_channels=2)
        
        print("Query-based gating results:")
        print(f"  Query 1 - Gate mean: {result1.gate_values.mean():.4f}")
        print(f"  Query 2 - Gate mean: {result2.gate_values.mean():.4f}")
        print(f"  Output shape: {result1.gated_output.shape}")
        print(f"  Num channels: {result1.metadata['num_channels']}")


def example_performance_analysis():
    """Example 7: Performance analysis and benchmarking."""
    print("\n" + "=" * 60)
    print("Example 7: Performance Analysis")
    print("=" * 60)
    
    import time
    from memu.engram import EngramService, get_lightweight_config, get_standard_config
    
    configs = {
        "Lightweight": get_lightweight_config(),
        "Standard": get_standard_config(),
    }
    
    # Enable metrics
    for name, config in configs.items():
        config.collect_metrics = True
    
    print("Benchmarking different configurations:")
    print("-" * 50)
    
    for name, config in configs.items():
        print(f"\n{name} Config:")
        print(f"  Memory: {config.estimate_memory_usage_human()}")
        
        with EngramService(config) as service:
            # Warmup
            for _ in range(3):
                _ = service.retrieve(np.random.randint(0, 10000, (1, 10)))
            
            # Benchmark
            batch_sizes = [1, 4, 16]
            seq_lens = [32, 128]
            
            for batch_size in batch_sizes:
                for seq_len in seq_lens:
                    token_ids = np.random.randint(0, 10000, (batch_size, seq_len))
                    
                    # Time multiple runs
                    times = []
                    for _ in range(10):
                        start = time.time()
                        _ = service.retrieve(token_ids)
                        times.append((time.time() - start) * 1000)
                    
                    avg_time = np.mean(times)
                    print(f"  Batch={batch_size:2d}, Seq={seq_len:3d}: {avg_time:.2f} ms")


def example_integration_with_memu():
    """Example 8: Integration with MemU memory system."""
    print("\n" + "=" * 60)
    print("Example 8: Integration with MemU (Conceptual)")
    print("=" * 60)
    
    from memu.engram import EngramService, get_lightweight_config
    
    # This example shows how Engram can be used alongside MemU's
    # existing RAG-based retrieval for enhanced memory capabilities.
    
    print("""
    Integration Concept:
    
    1. MemU RAG Retrieval:
       - Semantic search using embeddings
       - Good for: open-ended queries, fuzzy matching
       - Cost: O(n) or O(log n) with indexing
    
    2. Engram Retrieval:
       - Hash-based direct lookup
       - Good for: fixed patterns, known phrases
       - Cost: O(1) constant time
    
    Hybrid Approach:
    ┌─────────────────────────────────────────────┐
    │                User Query                    │
    │                    │                         │
    │         ┌──────────┴──────────┐             │
    │         ▼                     ▼             │
    │    ┌─────────┐          ┌─────────┐        │
    │    │ Engram  │          │   RAG   │        │
    │    │ O(1)    │          │ O(log n)│        │
    │    └────┬────┘          └────┬────┘        │
    │         │                    │              │
    │         └──────────┬─────────┘              │
    │                    ▼                        │
    │              ┌──────────┐                   │
    │              │  Fusion  │                   │
    │              │  Layer   │                   │
    │              └────┬─────┘                   │
    │                   ▼                         │
    │              Final Result                   │
    └─────────────────────────────────────────────┘
    """)
    
    # Demonstrate the concept
    config = get_lightweight_config()
    
    with EngramService(config) as engram:
        # Simulate integration
        token_ids = np.array([[42, 43, 44, 45, 46]])
        
        # Engram retrieval (O(1))
        engram_result = engram.retrieve(token_ids)
        
        # In production, you would also:
        # 1. Perform RAG retrieval via MemU
        # 2. Fuse results using learned weights
        # 3. Return combined memories
        
        print("Engram retrieval completed:")
        print(f"  Gate values: {engram_result.gate_values.shape}")
        print(f"  Output: {engram_result.gated_output.shape}")
        print("\nIn production, this would be fused with RAG results.")


def main():
    """Run all examples."""
    print("=" * 60)
    print("         ENGRAM MODULE USAGE EXAMPLES")
    print("=" * 60)
    
    examples = [
        ("Basic Usage", example_basic_usage),
        ("Custom Configuration", example_custom_configuration),
        ("Persistent Storage", example_persistent_storage),
        ("Hybrid Storage", example_hybrid_storage),
        ("Text-Based Memory", example_text_based_memory),
        ("Query-Based Gating", example_query_based_gating),
        ("Performance Analysis", example_performance_analysis),
        ("MemU Integration", example_integration_with_memu),
    ]
    
    for name, func in examples:
        try:
            func()
        except Exception as e:
            print(f"\nError in {name}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("         ALL EXAMPLES COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    main()
