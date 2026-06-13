import unittest

from memu.app.settings import LLMConfig
from memu.llm.backends.litellm import LiteLLMBackend


class TestLiteLLMProvider(unittest.IsolatedAsyncioTestCase):
    def test_settings_defaults(self):
        """Test that setting provider='litellm' sets the correct defaults."""
        config = LLMConfig(provider="litellm")
        self.assertEqual(config.base_url, "http://localhost:4000")
        self.assertEqual(config.api_key, "LITELLM_API_KEY")
        self.assertEqual(config.chat_model, "gpt-4o-mini")

    def test_settings_preserves_custom_values(self):
        """Test that custom values are not overridden by litellm defaults."""
        config = LLMConfig(
            provider="litellm",
            base_url="http://my-proxy:8000",
            api_key="sk-my-key",
            chat_model="anthropic/claude-sonnet-4-6",
        )
        self.assertEqual(config.base_url, "http://my-proxy:8000")
        self.assertEqual(config.api_key, "sk-my-key")
        self.assertEqual(config.chat_model, "anthropic/claude-sonnet-4-6")

    def test_backend_payload_parsing(self):
        """Test that LiteLLMBackend parses responses correctly (inherited from OpenAI)."""
        backend = LiteLLMBackend()

        dummy_response = {"choices": [{"message": {"content": "LiteLLM response content", "role": "assistant"}}]}

        result = backend.parse_summary_response(dummy_response)
        self.assertEqual(result, "LiteLLM response content")

    def test_backend_summary_payload(self):
        """Test that LiteLLMBackend builds correct summary payloads."""
        backend = LiteLLMBackend()

        payload = backend.build_summary_payload(
            text="Hello world",
            system_prompt="Summarize this.",
            chat_model="anthropic/claude-sonnet-4-6",
            max_tokens=100,
        )

        self.assertEqual(payload["model"], "anthropic/claude-sonnet-4-6")
        self.assertEqual(len(payload["messages"]), 2)
        self.assertEqual(payload["messages"][0]["role"], "system")
        self.assertEqual(payload["messages"][1]["role"], "user")
        self.assertEqual(payload["max_tokens"], 100)

    def test_backend_vision_payload(self):
        """Test that LiteLLMBackend builds correct vision payloads."""
        backend = LiteLLMBackend()

        payload = backend.build_vision_payload(
            prompt="Describe this image",
            base64_image="abc123",
            mime_type="image/png",
            system_prompt=None,
            chat_model="openai/gpt-4o",
            max_tokens=200,
        )

        self.assertEqual(payload["model"], "openai/gpt-4o")
        self.assertEqual(payload["messages"][0]["role"], "user")
        content = payload["messages"][0]["content"]
        self.assertEqual(content[0]["type"], "text")
        self.assertEqual(content[1]["type"], "image_url")

    def test_backend_name(self):
        """Test that the backend name is 'litellm'."""
        backend = LiteLLMBackend()
        self.assertEqual(backend.name, "litellm")

    def test_backend_endpoint(self):
        """Test that the backend uses OpenAI-compatible endpoint."""
        backend = LiteLLMBackend()
        self.assertEqual(backend.summary_endpoint, "/chat/completions")
