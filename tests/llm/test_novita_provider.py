import unittest
from unittest.mock import patch

from memu.app.settings import LLMConfig
from memu.llm.backends.novita import NovitaBackend
from memu.llm.openai_sdk import OpenAISDKClient


class TestNovitaProvider(unittest.IsolatedAsyncioTestCase):
    def test_settings_defaults(self):
        """Test that setting provider='novita' sets the correct defaults."""
        config = LLMConfig(provider="novita")
        self.assertEqual(config.base_url, "https://api.novita.ai/openai")
        self.assertEqual(config.api_key, "NOVITA_API_KEY")
        self.assertEqual(config.chat_model, "deepseek/deepseek-r1")

    def test_settings_do_not_override_non_openai_defaults(self):
        """Test that provider defaults only apply when values are OpenAI defaults."""
        config = LLMConfig(
            provider="novita",
            base_url="https://custom.novita.endpoint/v1",
            api_key="CUSTOM_NOVITA_KEY",
            chat_model="custom-model",
        )
        self.assertEqual(config.base_url, "https://custom.novita.endpoint/v1")
        self.assertEqual(config.api_key, "CUSTOM_NOVITA_KEY")
        self.assertEqual(config.chat_model, "custom-model")

    @patch.dict("os.environ", {"NOVITA_API_KEY": "env-key"}, clear=True)
    def test_openai_provider_not_auto_switched_by_env(self):
        """Test that NOVITA_API_KEY env var does not auto-switch provider defaults."""
        config = LLMConfig(provider="openai")
        self.assertEqual(config.base_url, "https://api.openai.com/v1")
        self.assertEqual(config.api_key, "OPENAI_API_KEY")

    @patch("memu.llm.openai_sdk.AsyncOpenAI")
    async def test_client_initialization_with_novita_config(self, mock_async_openai):
        """Test that OpenAISDKClient initializes with Novita base URL when configured."""
        config = LLMConfig(provider="novita")

        client = OpenAISDKClient(
            base_url=config.base_url,
            api_key="fake-key",
            chat_model=config.chat_model,
            embed_model=config.embed_model,
        )

        mock_async_openai.assert_called_with(api_key="fake-key", base_url="https://api.novita.ai/openai")
        self.assertEqual(client.chat_model, "deepseek/deepseek-r1")

    def test_novita_backend_payload_parsing(self):
        """Test that NovitaBackend parses responses correctly (inherited from OpenAI)."""
        backend = NovitaBackend()
        dummy_response = {"choices": [{"message": {"content": "Novita response content", "role": "assistant"}}]}
        result = backend.parse_summary_response(dummy_response)
        self.assertEqual(result, "Novita response content")
