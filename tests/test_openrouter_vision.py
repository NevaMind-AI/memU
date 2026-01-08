"""
Test OpenRouter vision functionality.

Tests:
1. Vision API payload building
2. Image description generation
3. Integration with MemU's multimodal workflow

Usage:
    export OPENROUTER_API_KEY=your_api_key
    python tests/test_openrouter_vision.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from memu.llm.http_client import HTTPLLMClient
from memu.llm.backends.openrouter import OpenRouterLLMBackend


def test_vision_payload_building():
    """Test that OpenRouter vision payload is built correctly."""
    print("\n[OPENROUTER VISION] Test 1: Vision payload building...")

    backend = OpenRouterLLMBackend()

    payload = backend.build_vision_payload(
        prompt="Describe this image",
        base64_image="SGVsbG8gV29ybGQ=",
        mime_type="image/png",
        system_prompt="You are a helpful assistant",
        chat_model="anthropic/claude-3.5-sonnet",
        max_tokens=500,
    )

    assert "model" in payload, "Missing 'model' in payload"
    assert payload["model"] == "anthropic/claude-3.5-sonnet", "Incorrect model"
    assert "messages" in payload, "Missing 'messages' in payload"
    assert len(payload["messages"]) == 2, "Expected 2 messages (system + user)"

    system_msg = payload["messages"][0]
    assert system_msg["role"] == "system", "First message should be system"
    assert system_msg["content"] == "You are a helpful assistant", "Incorrect system prompt"

    user_msg = payload["messages"][1]
    assert user_msg["role"] == "user", "Second message should be user"
    assert isinstance(user_msg["content"], list), "User content should be a list"
    assert len(user_msg["content"]) == 2, "User content should have text and image"

    text_part = user_msg["content"][0]
    assert text_part["type"] == "text", "First part should be text"
    assert text_part["text"] == "Describe this image", "Incorrect prompt text"

    image_part = user_msg["content"][1]
    assert image_part["type"] == "image_url", "Second part should be image_url"
    assert "image_url" in image_part, "Missing image_url object"
    assert image_part["image_url"]["url"].startswith("data:image/png;base64,"), "Incorrect data URL format"

    assert payload.get("max_tokens") == 500, "Incorrect max_tokens"

    print("  Payload structure is correct")
    print("  System message formatted correctly")
    print("  User message with image formatted correctly")
    print("  Data URL format is correct")


def test_vision_payload_without_system_prompt():
    """Test vision payload without system prompt."""
    print("\n[OPENROUTER VISION] Test 2: Vision payload without system prompt...")

    backend = OpenRouterLLMBackend()

    payload = backend.build_vision_payload(
        prompt="What's in this image?",
        base64_image="SGVsbG8gV29ybGQ=",
        mime_type="image/jpeg",
        system_prompt=None,
        chat_model="openai/gpt-4o",
        max_tokens=None,
    )

    assert len(payload["messages"]) == 1, "Expected 1 message when no system prompt"
    assert payload["messages"][0]["role"] == "user", "Should be user message"
    assert "max_tokens" not in payload or payload.get("max_tokens") is None, "max_tokens should not be set"

    print("  Payload without system prompt is correct")
    print("  Only user message present")


async def test_vision_api_call():
    """Test actual vision API call with OpenRouter."""
    print("\n[OPENROUTER VISION] Test 3: Vision API call (live test)...")

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("  Skipping live test: OPENROUTER_API_KEY not set")
        return

    image_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "examples", "resources", "images", "image1.png")
    )
    if not os.path.exists(image_path):
        print(f"  Skipping live test: Test image not found at {image_path}")
        return

    client = HTTPLLMClient(
        base_url="https://openrouter.ai",
        api_key=api_key,
        chat_model="openai/gpt-4o-mini",
        provider="openrouter",
    )

    result, raw_response = await client.vision(
        prompt="Describe what you see in this image in one sentence.",
        image_path=image_path,
        max_tokens=100,
    )

    assert result, "Vision API returned empty result"
    assert len(result) > 0, "Vision response is empty"
    print(f"  Vision API call successful")
    print(f"  Response: {result[:150]}...")


async def main():
    """Run all vision tests."""
    print("\n" + "=" * 60)
    print("[OPENROUTER VISION] Starting vision tests...")
    print("=" * 60)

    test_vision_payload_building()
    test_vision_payload_without_system_prompt()
    await test_vision_api_call()

    print("\n" + "=" * 60)
    print("[OPENROUTER VISION] All vision tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
