"""Tests for Claude model provider integration."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ============================================================================
# Claude Backend Tests
# ============================================================================


class TestClaudeLLMBackend:
    """Test Claude LLM backend."""

    def test_backend_name(self):
        """Test backend has correct name."""
        from memu.llm.backends.claude import ClaudeLLMBackend

        backend = ClaudeLLMBackend()
        assert backend.name == "claude"

    def test_summary_endpoint(self):
        """Test backend has correct endpoint."""
        from memu.llm.backends.claude import ClaudeLLMBackend

        backend = ClaudeLLMBackend()
        assert backend.summary_endpoint == "/v1/messages"

    def test_build_summary_payload(self):
        """Test building summary payload for Claude."""
        from memu.llm.backends.claude import ClaudeLLMBackend

        backend = ClaudeLLMBackend()
        payload = backend.build_summary_payload(
            text="Hello world",
            system_prompt="Be concise",
            chat_model="claude-opus-4-5-20251124",
            max_tokens=100,
        )

        assert payload["model"] == "claude-opus-4-5-20251124"
        assert payload["system"] == "Be concise"
        assert payload["max_tokens"] == 100
        assert len(payload["messages"]) == 1
        assert payload["messages"][0]["role"] == "user"
        assert payload["messages"][0]["content"] == "Hello world"

    def test_build_summary_payload_default_prompt(self):
        """Test building summary payload with default system prompt."""
        from memu.llm.backends.claude import ClaudeLLMBackend

        backend = ClaudeLLMBackend()
        payload = backend.build_summary_payload(
            text="Hello world",
            system_prompt=None,
            chat_model="claude-opus-4-5-20251124",
            max_tokens=None,
        )

        assert "Summarize" in payload["system"]
        assert payload["max_tokens"] == 4096  # Default

    def test_parse_summary_response(self):
        """Test parsing Claude response format."""
        from memu.llm.backends.claude import ClaudeLLMBackend

        backend = ClaudeLLMBackend()

        response = {
            "content": [
                {"type": "text", "text": "This is "},
                {"type": "text", "text": "the summary."},
            ],
            "stop_reason": "end_turn",
        }

        result = backend.parse_summary_response(response)
        assert result == "This is the summary."

    def test_parse_summary_response_empty(self):
        """Test parsing empty Claude response."""
        from memu.llm.backends.claude import ClaudeLLMBackend

        backend = ClaudeLLMBackend()

        response = {"content": []}
        result = backend.parse_summary_response(response)
        assert result == ""

    def test_build_vision_payload(self):
        """Test building vision payload for Claude."""
        from memu.llm.backends.claude import ClaudeLLMBackend

        backend = ClaudeLLMBackend()
        payload = backend.build_vision_payload(
            prompt="Describe this image",
            base64_image="abc123",
            mime_type="image/jpeg",
            system_prompt="Be detailed",
            chat_model="claude-opus-4-5-20251124",
            max_tokens=500,
        )

        assert payload["model"] == "claude-opus-4-5-20251124"
        assert payload["system"] == "Be detailed"
        assert payload["max_tokens"] == 500

        # Check message structure
        assert len(payload["messages"]) == 1
        content = payload["messages"][0]["content"]
        assert len(content) == 2

        # Image block
        assert content[0]["type"] == "image"
        assert content[0]["source"]["type"] == "base64"
        assert content[0]["source"]["media_type"] == "image/jpeg"
        assert content[0]["source"]["data"] == "abc123"

        # Text block
        assert content[1]["type"] == "text"
        assert content[1]["text"] == "Describe this image"


# ============================================================================
# Claude SDK Client Tests
# ============================================================================


class TestClaudeSDKClient:
    """Test Claude SDK client."""

    def test_client_init_requires_anthropic(self):
        """Test that client requires anthropic package."""
        # This test verifies the import check works
        from memu.llm.claude_sdk import ClaudeSDKClient

        # If anthropic is installed, this should work
        # If not, it should raise ImportError
        try:
            client = ClaudeSDKClient(api_key="test-key")
            assert client.chat_model == "claude-opus-4-5-20251124"
        except ImportError as e:
            assert "anthropic" in str(e)

    def test_embed_not_supported(self):
        """Test that embed raises NotImplementedError."""
        from memu.llm.claude_sdk import ClaudeSDKClient

        try:
            client = ClaudeSDKClient(api_key="test-key")
        except ImportError:
            pytest.skip("anthropic package not installed")

        # embed should raise NotImplementedError
        import asyncio
        with pytest.raises(NotImplementedError, match="embedding"):
            asyncio.run(client.embed(["test"]))

    def test_transcribe_not_supported(self):
        """Test that transcribe raises NotImplementedError."""
        from memu.llm.claude_sdk import ClaudeSDKClient

        try:
            client = ClaudeSDKClient(api_key="test-key")
        except ImportError:
            pytest.skip("anthropic package not installed")

        # transcribe should raise NotImplementedError
        import asyncio
        with pytest.raises(NotImplementedError, match="transcription"):
            asyncio.run(client.transcribe("test.mp3"))


# ============================================================================
# Claude Usage Dataclass Tests
# ============================================================================


class TestClaudeUsage:
    """Test Claude usage dataclass."""

    def test_total_tokens(self):
        """Test total_tokens property."""
        from memu.llm.claude_sdk import ClaudeUsage

        usage = ClaudeUsage(input_tokens=100, output_tokens=50)
        assert usage.total_tokens == 150


# ============================================================================
# HTTP Client Integration Tests
# ============================================================================


class TestHTTPClientClaudeIntegration:
    """Test HTTP client with Claude backend."""

    def test_claude_backend_registered(self):
        """Test that Claude backend is registered."""
        from memu.llm.http_client import LLM_BACKENDS

        assert "claude" in LLM_BACKENDS

    def test_http_client_loads_claude_backend(self):
        """Test HTTP client can load Claude backend."""
        from memu.llm.http_client import HTTPLLMClient

        client = HTTPLLMClient(
            base_url="https://api.anthropic.com",
            api_key="test-key",
            chat_model="claude-opus-4-5-20251124",
            provider="claude",
        )

        assert client.provider == "claude"
        assert client.backend.name == "claude"

    def test_claude_headers(self):
        """Test Claude uses correct headers."""
        from memu.llm.http_client import HTTPLLMClient

        client = HTTPLLMClient(
            base_url="https://api.anthropic.com",
            api_key="test-key",
            chat_model="claude-opus-4-5-20251124",
            provider="claude",
        )

        headers = client._headers()
        assert headers["x-api-key"] == "test-key"
        assert "anthropic-version" in headers
        assert "Authorization" not in headers

    def test_openai_headers(self):
        """Test OpenAI still uses Bearer token."""
        from memu.llm.http_client import HTTPLLMClient

        client = HTTPLLMClient(
            base_url="https://api.openai.com/v1",
            api_key="test-key",
            chat_model="gpt-4",
            provider="openai",
        )

        headers = client._headers()
        assert headers["Authorization"] == "Bearer test-key"
        assert "x-api-key" not in headers


# ============================================================================
# Backend Registration Tests
# ============================================================================


class TestBackendRegistration:
    """Test backend registration."""

    def test_claude_in_backends_init(self):
        """Test Claude is exported from backends module."""
        from memu.llm.backends import ClaudeLLMBackend

        assert ClaudeLLMBackend is not None
        assert ClaudeLLMBackend.name == "claude"

    def test_all_backends_available(self):
        """Test all expected backends are available."""
        from memu.llm.backends import (
            ClaudeLLMBackend,
            DoubaoLLMBackend,
            OpenAILLMBackend,
        )

        assert OpenAILLMBackend.name == "openai"
        assert DoubaoLLMBackend.name == "doubao"
        assert ClaudeLLMBackend.name == "claude"


# ============================================================================
# Claude Message Dataclass Tests
# ============================================================================


class TestClaudeMessage:
    """Test Claude message dataclass."""

    def test_text_property(self):
        """Test text property extracts content."""
        from memu.llm.claude_sdk import ClaudeMessage, ClaudeUsage

        message = ClaudeMessage(
            id="msg_123",
            type="message",
            role="assistant",
            content=[
                {"type": "text", "text": "Hello "},
                {"type": "text", "text": "world!"},
            ],
            model="claude-opus-4-5-20251124",
            stop_reason="end_turn",
            stop_sequence=None,
            usage=ClaudeUsage(input_tokens=10, output_tokens=5),
        )

        assert message.text == "Hello world!"

    def test_text_property_empty(self):
        """Test text property with empty content."""
        from memu.llm.claude_sdk import ClaudeMessage, ClaudeUsage

        message = ClaudeMessage(
            id="msg_123",
            type="message",
            role="assistant",
            content=[],
            model="claude-opus-4-5-20251124",
            stop_reason="end_turn",
            stop_sequence=None,
            usage=ClaudeUsage(input_tokens=10, output_tokens=0),
        )

        assert message.text == ""
