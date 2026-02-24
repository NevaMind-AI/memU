#!/usr/bin/env python3
"""
Quick test script to verify LazyLLM backend configuration and basic functionality.

Usage:
    export MEMU_QWEN_API_KEY=your_api_key
    python examples/test_lazyllm.py
"""

import asyncio
import os
import sys

# Add src to sys.path
src_path = os.path.abspath("src")
sys.path.insert(0, src_path)

from memu.llm.lazyllm_client import LazyLLMClient  # noqa: E402


async def test_lazyllm_client():
    """Test LazyLLMClient with basic operations."""

    print("LazyLLM Backend Test")
    print("=" * 60)

    # Get API key from environment
    try:
        client = LazyLLMClient(
            llm_source="qwen",
            vlm_source="qwen",
            embed_source="qwen",
            stt_source="qwen",
            chat_model="qwen-plus",
            vlm_model="qwen-vl-plus",
            embed_model="text-embedding-v3",
            stt_model="qwen-audio-turbo",
        )
        print("✓ LazyLLMClient initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize LazyLLMClient: {e}")
        return False

    # Test 1: Summarization
    print("\n[Test 1] Testing summarization...")
    try:
        test_text = "这是一段关于Python编程的文本。Python是一种高级编程语言，具有简单易学的语法。它被广泛用于数据分析、机器学习和Web开发。"  # noqa: RUF001
        result = await client.chat(test_text)
        print("✓ Summarization successful")
        print(f"  Result: {result[:100]}...")
    except Exception as e:
        print(f"❌ Summarization failed: {e}")
        import traceback

        traceback.print_exc()

    # Test 2: Embedding
    print("\n[Test 2] Testing embedding...")
    try:
        test_texts = ["Hello world", "How are you", "Nice to meet you"]
        embeddings = await client.embed(test_texts)
        print("✓ Embedding successful")
        print(f"  Generated {len(embeddings)} embeddings")
        if embeddings and embeddings[0]:
            print(f"  Embedding dimension: {len(embeddings[0])}")
    except Exception as e:
        print(f"❌ Embedding failed: {e}")
        import traceback

        traceback.print_exc()

    # Test 3: Vision (requires image file)
    print("\n[Test 3] Testing vision...")
    test_image_path = "examples/resources/images/image1.png"
    if os.path.exists(test_image_path):
        try:
            result, _ = await client.vision(prompt="描述这张图片的内容", image_path=test_image_path)
            print("✓ Vision successful")
            print(f"  Result: {result[:100]}...")
        except Exception as e:
            print(f"❌ Vision failed: {e}")
            import traceback

            traceback.print_exc()
    else:
        print(f"⚠ Skipped: Test image not found at {test_image_path}")


if __name__ == "__main__":
    success = asyncio.run(test_lazyllm_client())
    sys.exit(0 if success else 1)
