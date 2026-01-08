"""
Test OpenRouter embedding functionality.

Tests:
1. Direct embedding generation via OpenRouter API
2. Embedding-based similarity search
3. Batch embedding processing

Usage:
    export OPENROUTER_API_KEY=your_api_key
    python tests/test_openrouter_embedding.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from memu.llm.http_client import HTTPLLMClient


async def test_openrouter_embeddings():
    """Test OpenRouter embedding functionality."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY environment variable not set")
        print("Please set it with: export OPENROUTER_API_KEY=your_api_key")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("[OPENROUTER EMBEDDING] Starting embedding tests...")
    print("=" * 60)

    client = HTTPLLMClient(
        base_url="https://openrouter.ai",
        api_key=api_key,
        chat_model="anthropic/claude-3.5-sonnet",
        provider="openrouter",
        embed_model="openai/text-embedding-3-small",
    )

    # Test 1: Single text embedding
    print("\n[OPENROUTER EMBEDDING] Test 1: Single text embedding...")
    texts = ["I love coffee in the morning"]
    embeddings, raw_response = await client.embed(texts)
    assert len(embeddings) == 1, f"Expected 1 embedding, got {len(embeddings)}"
    assert len(embeddings[0]) > 0, "Embedding vector is empty"
    print(f"  Generated embedding with {len(embeddings[0])} dimensions")

    # Test 2: Batch embedding
    print("\n[OPENROUTER EMBEDDING] Test 2: Batch embedding...")
    batch_texts = [
        "I enjoy reading books",
        "Programming is fun",
        "The weather is nice today",
        "I like to exercise in the morning",
        "Coffee helps me stay focused",
    ]
    batch_embeddings, _ = await client.embed(batch_texts)
    assert len(batch_embeddings) == len(batch_texts), (
        f"Expected {len(batch_texts)} embeddings, got {len(batch_embeddings)}"
    )
    print(f"  Generated {len(batch_embeddings)} embeddings successfully")
    print(f"  Each embedding has {len(batch_embeddings[0])} dimensions")

    # Test 3: Embedding similarity
    print("\n[OPENROUTER EMBEDDING] Test 3: Embedding similarity check...")
    similar_texts = [
        "I love drinking coffee",
        "Coffee is my favorite drink",
    ]
    different_text = ["The stock market crashed yesterday"]

    similar_embeddings, _ = await client.embed(similar_texts)
    different_embedding, _ = await client.embed(different_text)

    def cosine_similarity(a, b):
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x**2 for x in a) ** 0.5
        norm_b = sum(x**2 for x in b) ** 0.5
        return dot_product / (norm_a * norm_b)

    sim_similar = cosine_similarity(similar_embeddings[0], similar_embeddings[1])
    sim_different = cosine_similarity(similar_embeddings[0], different_embedding[0])

    print(f"  Similarity between similar texts: {sim_similar:.4f}")
    print(f"  Similarity between different texts: {sim_different:.4f}")

    assert sim_similar > sim_different, (
        f"Expected similar texts to have higher similarity, "
        f"got {sim_similar:.4f} vs {sim_different:.4f}"
    )
    print("  Similarity check passed (similar texts have higher similarity)")

    print("\n" + "=" * 60)
    print("[OPENROUTER EMBEDDING] All embedding tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_openrouter_embeddings())
