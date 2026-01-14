import unittest
from unittest.mock import patch

from memu.app.settings import LLMConfig
from memu.llm.backends.grok import GrokBackend
from memu.llm.openai_sdk import OpenAISDKClient


class TestGrokProvider(unittest.IsolatedAsyncioTestCase):
    def test_settings_defaults(self):
        """Test that setting provider='grok' sets the correct defaults."""
        config = LLMConfig(provider="grok")
        self.assertEqual(config.base_url, "https://api.x.ai/v1")
        self.assertEqual(config.api_key, "XAI_API_KEY")
        self.assertEqual(config.chat_model, "grok-2-latest")

    @patch("memu.llm.openai_sdk.AsyncOpenAI")
    async def test_client_initialization_with_grok_config(self, mock_async_openai):
        """Test that OpenAISDKClient initializes with Grok base URL when configured."""
        # Setup config
        config = LLMConfig(provider="grok")

        # Instantiate client with Grok config
        # We simulate what the application factory would do: pass the config values
        client = OpenAISDKClient(
            base_url=config.base_url,
            api_key="fake-key",  # In real app, this would be os.getenv(config.api_key)
            chat_model=config.chat_model,
            embed_model=config.embed_model,
        )

        # Assert AsyncOpenAI was called with the correct base_url
        mock_async_openai.assert_called_with(api_key="fake-key", base_url="https://api.x.ai/v1")

        # Verify client attributes
        self.assertEqual(client.chat_model, "grok-2-latest")

    def test_grok_backend_payload_parsing(self):
        """Test that GrokBackend parses responses correctly (inherited from OpenAI)."""
        backend = GrokBackend()

        # Simulate a typical OpenAI-compatible response
        dummy_response = {"choices": [{"message": {"content": "Grok response content", "role": "assistant"}}]}

        result = backend.parse_summary_response(dummy_response)
        self.assertEqual(result, "Grok response content")
