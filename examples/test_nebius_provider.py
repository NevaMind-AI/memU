"""
Test script to verify Nebius AI works with MemU.

Before running:
1. Get your Nebius API key from https://tokenfactory.nebius.com
2. Set environment variable: NEBIUS_API_KEY=your_key_here

Usage:
    cd memU
    set NEBIUS_API_KEY=your_key_here
    python examples/test_nebius_provider.py

Nebius provides:
- Chat models: Qwen, DeepSeek, Llama, etc.
- Embedding models: BGE, E5, Qwen3-Embedding
- All via OpenAI-compatible API
"""

import asyncio
import os
import sys

# Add src to path for local development
src_path = os.path.abspath("src")
sys.path.insert(0, src_path)

# Nebius configuration
NEBIUS_BASE_URL = "https://api.tokenfactory.nebius.com/v1/"
# Available chat models (pick one):
# - "Qwen/Qwen3-30B-A3B-Instruct-2507" (fast, cheap)
# - "Qwen/Qwen3-32B" (good balance)
# - "deepseek-ai/DeepSeek-V3-0324" (powerful)
# - "meta-llama/Llama-3.3-70B-Instruct" (reliable)
NEBIUS_CHAT_MODEL = "Qwen/Qwen3-30B-A3B-Instruct-2507"
# Available embedding models:
# - "BAAI/bge-multilingual-gemma2" (3584 dims, multilingual)
# - "BAAI/BGE-ICL" (4096 dims)
# - "intfloat/e5-mistral-7b-instruct" (4096 dims)
# - "Qwen/Qwen3-Embedding-8B" (4096 dims)
NEBIUS_EMBED_MODEL = "BAAI/bge-multilingual-gemma2"


async def test_nebius_chat():
    """Test Nebius chat completion."""
    from openai import AsyncOpenAI

    api_key = os.environ.get("NEBIUS_API_KEY")
    if not api_key:
        print("ERROR: Set NEBIUS_API_KEY environment variable")
        return False

    client = AsyncOpenAI(
        base_url=NEBIUS_BASE_URL,
        api_key=api_key,
    )

    print(f"Testing Nebius Chat API ({NEBIUS_CHAT_MODEL})...")
    try:
        response = await client.chat.completions.create(
            model=NEBIUS_CHAT_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say hello in one sentence."},
            ],
            max_tokens=50,
        )
        content = response.choices[0].message.content
        # Truncate long responses for display
        display = content[:100] + "..." if len(content) > 100 else content
        print(f"  Response: {display}")
        print("  ✓ Chat API works!")
        return True
    except Exception as e:
        print(f"  ✗ Chat API failed: {e}")
        return False


async def test_nebius_embeddings():
    """Test Nebius embeddings API."""
    from openai import AsyncOpenAI

    api_key = os.environ.get("NEBIUS_API_KEY")
    if not api_key:
        print("ERROR: Set NEBIUS_API_KEY environment variable")
        return False

    client = AsyncOpenAI(
        base_url=NEBIUS_BASE_URL,
        api_key=api_key,
    )

    print(f"\nTesting Nebius Embeddings API ({NEBIUS_EMBED_MODEL})...")
    try:
        response = await client.embeddings.create(
            model=NEBIUS_EMBED_MODEL,
            input=["Hello world", "This is a test"],
        )
        print(f"  Embedding dimensions: {len(response.data[0].embedding)}")
        print(f"  Number of embeddings: {len(response.data)}")
        print("  ✓ Embeddings API works!")
        return True
    except Exception as e:
        print(f"  ✗ Embeddings API failed: {e}")
        return False


async def test_memu_with_nebius():
    """Test MemU with Nebius as the LLM provider."""
    from memu.app import MemoryService

    api_key = os.environ.get("NEBIUS_API_KEY")
    if not api_key:
        print("ERROR: Set NEBIUS_API_KEY environment variable")
        return False

    print("\nTesting MemU with Nebius provider...")

    # Configure MemU to use Nebius (using dict config like example_1)
    llm_profiles = {
        "default": {
            "provider": "openai",
            "base_url": NEBIUS_BASE_URL,
            "api_key": api_key,
            "chat_model": NEBIUS_CHAT_MODEL,
            "client_backend": "sdk",
        },
        "embedding": {
            "provider": "openai",
            "base_url": NEBIUS_BASE_URL,
            "api_key": api_key,
            "embed_model": NEBIUS_EMBED_MODEL,
            "client_backend": "sdk",
        },
    }

    try:
        # Create MemU service with Nebius
        service = MemoryService(llm_profiles=llm_profiles)
        print("  ✓ MemoryService initialized with Nebius!")

        # Test memorize with a file (create temp file)
        print("\n  Testing memorize...")
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("User likes Python programming and AI development. They prefer dark mode in their IDE.")
            temp_file = f.name

        try:
            result = await service.memorize(
                resource_url=temp_file,
                modality="text",
            )
            items_count = len(result.get("items", []))
            categories_count = len(result.get("categories", []))
            print(f"  ✓ Memorized! Items: {items_count}, Categories: {categories_count}")

            # Show what was extracted
            for item in result.get("items", [])[:3]:
                summary = item.get("summary", "")[:80]
                print(f"    - {summary}...")
        finally:
            os.unlink(temp_file)

        # Test retrieve
        print("\n  Testing retrieve...")
        retrieve_result = await service.retrieve(
            queries=[{"role": "user", "content": "What programming language does the user like?"}]
        )
        print(f"  ✓ Retrieved! Needs retrieval: {retrieve_result.get('needs_retrieval')}")

        items = retrieve_result.get("items", [])
        if items:
            print(f"  Found {len(items)} relevant items:")
            for item in items[:3]:
                if isinstance(item, dict):
                    summary = item.get("summary", str(item))[:60]
                else:
                    summary = str(item)[:60]
                print(f"    - {summary}...")

        print("\n" + "=" * 60)
        print("✓ SUCCESS: MemU works with Nebius!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"  ✗ MemU with Nebius failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    print("=" * 60)
    print("Nebius AI + MemU Integration Test")
    print("=" * 60)
    print(f"Base URL: {NEBIUS_BASE_URL}")
    print(f"Chat Model: {NEBIUS_CHAT_MODEL}")
    print(f"Embed Model: {NEBIUS_EMBED_MODEL}")
    print("=" * 60 + "\n")

    # Check for API key first
    if not os.environ.get("NEBIUS_API_KEY"):
        print("ERROR: NEBIUS_API_KEY environment variable not set!")
        print("\nTo get your API key:")
        print("1. Go to https://tokenfactory.nebius.com")
        print("2. Create an account / Log in")
        print("3. Get your API key")
        print("4. Run: set NEBIUS_API_KEY=your_key_here")
        return

    # Test individual APIs first
    chat_ok = await test_nebius_chat()
    embed_ok = await test_nebius_embeddings()

    if chat_ok and embed_ok:
        # Test full MemU integration
        await test_memu_with_nebius()
    else:
        print("\n" + "=" * 60)
        print("✗ FAILED: Basic API tests failed, skipping MemU test")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
