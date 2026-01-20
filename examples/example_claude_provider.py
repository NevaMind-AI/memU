"""
Example: Claude Model Provider Integration

This example demonstrates how to use Anthropic's Claude as the LLM provider
for MemU's memory service, including chat completions and vision capabilities.

Usage:
    export ANTHROPIC_API_KEY=your_anthropic_api_key
    export OPENAI_API_KEY=your_openai_api_key  # For embeddings (Claude doesn't have native embeddings)
    python examples/example_claude_provider.py
"""

import asyncio
import os
import sys

from memu.app import MemoryService

# Add src to sys.path
src_path = os.path.abspath("src")
sys.path.insert(0, src_path)


async def test_claude_memorize():
    """Test Claude provider with conversation memorization."""
    print("\n" + "=" * 60)
    print("Testing Claude Provider - Conversation Memorization")
    print("=" * 60)

    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if not anthropic_key:
        print("ERROR: Please set ANTHROPIC_API_KEY environment variable")
        return False

    if not openai_key:
        print("WARNING: OPENAI_API_KEY not set. Embeddings will fail.")
        print("Claude doesn't have native embeddings, so OpenAI is used for embeddings.")

    # Initialize service with Claude as the LLM provider
    # Note: Claude doesn't have embeddings, so we use OpenAI for that
    service = MemoryService(
        llm_profiles={
            "default": {
                "provider": "claude",
                "base_url": "https://api.anthropic.com",
                "api_key": anthropic_key,
                "chat_model": "claude-sonnet-4-20250514",  # Using Sonnet for cost efficiency
            },
            "embedding": {
                "provider": "openai",
                "api_key": openai_key,
                "embed_model": "text-embedding-3-small",
            },
        },
        database_config={
            "metadata_store": {"provider": "inmemory"},
        },
    )

    # Test with a conversation file
    conv_file = "examples/resources/conversations/conv1.json"
    if not os.path.exists(conv_file):
        print(f"Conversation file not found: {conv_file}")
        print("Creating a sample conversation...")

        # Create sample conversation
        os.makedirs("examples/resources/conversations", exist_ok=True)
        sample_conv = [
            {"role": "user", "content": "Hi, I'm interested in learning Python programming."},
            {"role": "assistant", "content": "Great! Python is an excellent choice. What's your current experience level?"},
            {"role": "user", "content": "I'm a complete beginner. I work as a data analyst and want to automate my Excel tasks."},
            {"role": "assistant", "content": "Perfect! Python is ideal for data analysis and automation. We can start with pandas for data manipulation."},
            {"role": "user", "content": "That sounds good. I prefer learning through practical examples rather than theory."},
        ]
        import json
        with open(conv_file, "w") as f:
            json.dump(sample_conv, f, indent=2)

    print(f"\nProcessing conversation: {conv_file}")

    try:
        result = await service.memorize(
            resource_url=conv_file,
            modality="conversation",
            user={"user_id": "claude_test_user"},
        )

        print("\n✓ Memorization successful!")
        print(f"  Items extracted: {len(result.get('items', []))}")
        print(f"  Categories: {len(result.get('categories', []))}")

        for cat in result.get("categories", [])[:3]:
            print(f"    - {cat.get('name')}: {(cat.get('summary') or '')[:60]}...")

    except Exception as e:
        print(f"\n✗ Error during memorization: {e}")
        import traceback
        traceback.print_exc()
        return False
    else:
        return True


async def test_claude_retrieve():
    """Test Claude provider with memory retrieval."""
    print("\n" + "=" * 60)
    print("Testing Claude Provider - Memory Retrieval")
    print("=" * 60)

    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if not anthropic_key or not openai_key:
        print("Skipping retrieval test - API keys not set")
        return False

    service = MemoryService(
        llm_profiles={
            "default": {
                "provider": "claude",
                "base_url": "https://api.anthropic.com",
                "api_key": anthropic_key,
                "chat_model": "claude-sonnet-4-20250514",
            },
            "embedding": {
                "provider": "openai",
                "api_key": openai_key,
                "embed_model": "text-embedding-3-small",
            },
        },
        database_config={
            "metadata_store": {"provider": "inmemory"},
        },
        retrieve_config={"method": "rag"},
    )

    # First memorize something
    conv_file = "examples/resources/conversations/conv1.json"
    if os.path.exists(conv_file):
        await service.memorize(
            resource_url=conv_file,
            modality="conversation",
            user={"user_id": "claude_test_user"},
        )

    # Now retrieve
    queries = [
        {"role": "user", "content": {"text": "What programming language does the user want to learn?"}},
    ]

    try:
        result = await service.retrieve(
            queries=queries,
            where={"user_id": "claude_test_user"},
        )

        print("\n✓ Retrieval successful!")
        print(f"  Categories found: {len(result.get('categories', []))}")
        print(f"  Items found: {len(result.get('items', []))}")

        for item in result.get("items", [])[:3]:
            print(f"    - [{item.get('memory_type')}] {item.get('summary', '')[:80]}...")

    except Exception as e:
        print(f"\n✗ Error during retrieval: {e}")
        import traceback
        traceback.print_exc()
        return False
    else:
        return True


async def test_claude_sdk_direct():
    """Test Claude SDK client directly."""
    print("\n" + "=" * 60)
    print("Testing Claude SDK Client - Direct Usage")
    print("=" * 60)

    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_key:
        print("Skipping SDK test - ANTHROPIC_API_KEY not set")
        return False

    try:
        from memu.llm.claude_sdk import ClaudeSDKClient

        client = ClaudeSDKClient(
            api_key=anthropic_key,
            chat_model="claude-sonnet-4-20250514",
        )

        # Test summarization
        print("\nTesting summarization...")
        text = """
        Python is a high-level, general-purpose programming language. Its design philosophy
        emphasizes code readability with the use of significant indentation. Python is
        dynamically typed and garbage-collected. It supports multiple programming paradigms,
        including structured, object-oriented and functional programming.
        """

        summary, response = await client.summarize(
            text,
            system_prompt="Summarize in one sentence.",
            max_tokens=100,
        )

        print(f"✓ Summary: {summary[:100]}...")
        print(f"  Tokens used: {response.usage.total_tokens}")

    except ImportError:
        print("✗ anthropic package not installed. Run: pip install anthropic")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    else:
        return True
        return False


async def test_claude_http_client():
    """Test Claude via HTTP client."""
    print("\n" + "=" * 60)
    print("Testing Claude HTTP Client")
    print("=" * 60)

    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_key:
        print("Skipping HTTP client test - ANTHROPIC_API_KEY not set")
        return False

    try:
        from memu.llm.http_client import HTTPLLMClient

        client = HTTPLLMClient(
            base_url="https://api.anthropic.com",
            api_key=anthropic_key,
            chat_model="claude-sonnet-4-20250514",
            provider="claude",
        )

        # Test summarization
        print("\nTesting HTTP client summarization...")
        text = "The quick brown fox jumps over the lazy dog. This is a test sentence."

        summary, _raw_response = await client.summarize(
            text,
            system_prompt="Repeat the text exactly.",
            max_tokens=100,
        )

        print(f"✓ Response: {summary[:100]}...")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    else:
        return True


async def main():
    """Run all Claude provider tests."""
    print("\n" + "=" * 60)
    print("MemU Claude Provider Integration Tests")
    print("=" * 60)

    results = {
        "SDK Direct": await test_claude_sdk_direct(),
        "HTTP Client": await test_claude_http_client(),
        "Memorize": await test_claude_memorize(),
        "Retrieve": await test_claude_retrieve(),
    }

    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {test_name}: {status}")

    all_passed = all(results.values())
    print("\n" + ("All tests passed!" if all_passed else "Some tests failed."))

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
