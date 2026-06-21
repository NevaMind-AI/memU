import unittest
from unittest.mock import patch

from memu.app.settings import LLMConfig
from memu.llm.backends.minimax import MiniMaxLLMBackend
from memu.llm.openai_sdk import OpenAISDKClient


class TestMiniMaxProvider(unittest.IsolatedAsyncioTestCase):
    def test_settings_defaults(self):
        """Test that setting provider='minimax' sets the correct defaults."""
        config = LLMConfig(provider="minimax")
        self.assertEqual(config.base_url, "https://api.minimax.io/v1")
        self.assertEqual(config.api_key, "MINIMAX_API_KEY")
        self.assertEqual(config.chat_model, "MiniMax-M2.5")

    def test_settings_custom_model(self):
        """Test that custom model can be set for MiniMax provider."""
        config = LLMConfig(provider="minimax", chat_model="MiniMax-M2.5-highspeed")
        self.assertEqual(config.base_url, "https://api.minimax.io/v1")
        self.assertEqual(config.chat_model, "MiniMax-M2.5-highspeed")

    def test_settings_custom_base_url(self):
        """Test that custom base_url is preserved for MiniMax provider."""
        config = LLMConfig(provider="minimax", base_url="https://api.minimaxi.com/v1")
        self.assertEqual(config.base_url, "https://api.minimaxi.com/v1")

    @patch("memu.llm.openai_sdk.AsyncOpenAI")
    async def test_client_initialization_with_minimax_config(self, mock_async_openai):
        """Test that OpenAISDKClient initializes with MiniMax base URL when configured."""
        config = LLMConfig(provider="minimax")

        client = OpenAISDKClient(
            base_url=config.base_url,
            api_key="fake-key",
            chat_model=config.chat_model,
            embed_model=config.embed_model,
        )

        mock_async_openai.assert_called_with(api_key="fake-key", base_url="https://api.minimax.io/v1")
        self.assertEqual(client.chat_model, "MiniMax-M2.5")

    def test_minimax_backend_payload_parsing(self):
        """Test that MiniMaxLLMBackend parses responses correctly (inherited from OpenAI)."""
        backend = MiniMaxLLMBackend()

        dummy_response = {"choices": [{"message": {"content": "MiniMax response content", "role": "assistant"}}]}

        result = backend.parse_summary_response(dummy_response)
        self.assertEqual(result, "MiniMax response content")

    def test_minimax_backend_name(self):
        """Test that MiniMaxLLMBackend has the correct name."""
        backend = MiniMaxLLMBackend()
        self.assertEqual(backend.name, "minimax")

    def test_minimax_backend_summary_payload(self):
        """Test that MiniMaxLLMBackend builds the correct summary payload."""
        backend = MiniMaxLLMBackend()
        payload = backend.build_summary_payload(
            text="Hello world",
            system_prompt="Summarize this.",
            chat_model="MiniMax-M2.5",
            max_tokens=100,
        )
        self.assertEqual(payload["model"], "MiniMax-M2.5")
        self.assertEqual(len(payload["messages"]), 2)
        self.assertEqual(payload["messages"][0]["role"], "system")
        self.assertEqual(payload["messages"][1]["role"], "user")
        self.assertEqual(payload["messages"][1]["content"], "Hello world")
        self.assertEqual(payload["max_tokens"], 100)

    def test_minimax_backend_vision_payload(self):
        """Test that MiniMaxLLMBackend builds the correct vision payload."""
        backend = MiniMaxLLMBackend()
        payload = backend.build_vision_payload(
            prompt="Describe this image",
            base64_image="base64data",
            mime_type="image/png",
            system_prompt=None,
            chat_model="MiniMax-M2.5",
            max_tokens=200,
        )
        self.assertEqual(payload["model"], "MiniMax-M2.5")
        self.assertIsInstance(payload["messages"], list)
        # Should have user message with text and image content
        user_msg = payload["messages"][0]
        self.assertEqual(user_msg["role"], "user")
        self.assertIsInstance(user_msg["content"], list)
        self.assertEqual(len(user_msg["content"]), 2)

    def test_minimax_http_backend_registration(self):
        """Test that MiniMax is registered in the HTTP LLM backends."""
        from memu.llm.http_client import LLM_BACKENDS

        self.assertIn("minimax", LLM_BACKENDS)
        backend = LLM_BACKENDS["minimax"]()
        self.assertEqual(backend.name, "minimax")

    def test_minimax_http_embedding_backend_registration(self):
        """Test that MiniMax is registered in the HTTP embedding backends."""
        from memu.llm.http_client import HTTPLLMClient

        client = HTTPLLMClient(
            base_url="https://api.minimax.io/v1",
            api_key="fake-key",
            chat_model="MiniMax-M2.5",
            provider="minimax",
        )
        self.assertEqual(client.provider, "minimax")
        self.assertEqual(client.backend.name, "minimax")
