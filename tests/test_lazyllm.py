#!/usr/bin/env python3
"""
Quick test script to verify LazyLLM backend configuration and basic functionality.

Usage:
    export LAZYLLM_API_KEY=your_api_key
    python examples/test_lazyllm.py
"""

import asyncio
import os
import sys
import lazyllm

# Add src to sys.path
src_path = os.path.abspath("src")
sys.path.insert(0, src_path)

from memu.llm.lazyllm_client import LazyLLMClient


async def test_lazyllm_client():
    """Test LazyLLMClient with basic operations."""
    
    print("LazyLLM Backend Test")
    print("=" * 60)
    
    # Get API key from environment
    lazyllm.config.add("qwen_api_key", str, env="QWEN_API_KEY", description="Qwen API Key")
    with lazyllm.config.namespace("MEMU"):
        api_key = lazyllm.config['qwen_api_key']
    if not api_key:
        msg = "Please set MEMU_QWEN_API_KEY environment variable"
        raise ValueError(msg)
    
    print(f"✓ API key found: {api_key[:20]}...")
    try:
        client = LazyLLMClient(
            source="qwen",
            chat_model="qwen3-max",
            vlm_model="qwen-vl-plus",
            embed_model="text-embedding-v3",
            stt_model="qwen-audio-turbo",
            base_url="",
            api_key=api_key
        )
        print("✓ LazyLLMClient initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize LazyLLMClient: {e}")
        return False
    
    # Test 1: Summarization
    print("\n[Test 1] Testing summarization...")
    try:
        test_text = "这是一段关于Python编程的文本。Python是一种高级编程语言，具有简单易学的语法。它被广泛用于数据分析、机器学习和Web开发。"
        result = await client.summarize(test_text)
        print(f"✓ Summarization successful")
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
        print(f"✓ Embedding successful")
        print(f"  Generated {len(embeddings)} embeddings")
        if embeddings and embeddings[0]:
            print(f"  Embedding dimension: {len(embeddings[0])}")
    except Exception as e:
        print(f"❌ Embedding failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Vision (requires image file)
    print("\n[Test 3] Testing vision...")
    test_image_path = "examples/resources/images/sample.jpg"
    if os.path.exists(test_image_path):
        try:
            result, response = await client.vision(
                prompt="描述这张图片的内容",
                image_path=test_image_path
            )
            print(f"✓ Vision successful")
            print(f"  Result: {result[:100]}...")
        except Exception as e:
            print(f"❌ Vision failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"⚠ Skipped: Test image not found at {test_image_path}")
    
    # Test 4: Transcription (requires audio file)
    print("\n[Test 4] Testing transcription...")
    test_audio_path = "examples/resources/audio/sample.wav"
    if os.path.exists(test_audio_path):
        try:
            result, response = await client.transcribe(
                audio_path=test_audio_path,
                language="zh"
            )
            print(f"✓ Transcription successful")
            print(f"  Result: {result[:100]}...")
        except Exception as e:
            print(f"❌ Transcription failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"⚠ Skipped: Test audio not found at {test_audio_path}")
    
    print("\n" + "=" * 60)
    print("✓ LazyLLM backend tests completed!")
    return True


if __name__ == "__main__":
    success = asyncio.run(test_lazyllm_client())
    sys.exit(0 if success else 1)
