import sys
import types
import unittest
from unittest import mock

from memu.app.settings import LLMConfig
from memu.llm.backends.litellm import LiteLLMBackend


def _install_litellm_stub():
    """Install a fake litellm module so tests run without the real package."""
    fake = types.ModuleType("litellm")
    fake.acompletion = mock.AsyncMock(name="litellm.acompletion")
    fake.aembedding = mock.AsyncMock(name="litellm.aembedding")
    sys.modules["litellm"] = fake
    return fake


class TestLiteLLMBackend(unittest.TestCase):
    def test_backend_name(self):
        backend = LiteLLMBackend()
        self.assertEqual(backend.name, "litellm")

    def test_backend_endpoint(self):
        backend = LiteLLMBackend()
        self.assertEqual(backend.summary_endpoint, "/chat/completions")

    def test_backend_payload_parsing(self):
        backend = LiteLLMBackend()
        dummy_response = {"choices": [{"message": {"content": "LiteLLM response", "role": "assistant"}}]}
        result = backend.parse_summary_response(dummy_response)
        self.assertEqual(result, "LiteLLM response")

    def test_backend_summary_payload(self):
        backend = LiteLLMBackend()
        payload = backend.build_summary_payload(
            text="Hello world",
            system_prompt="Summarize this.",
            chat_model="anthropic/claude-sonnet-4-6",
            max_tokens=100,
        )
        self.assertEqual(payload["model"], "anthropic/claude-sonnet-4-6")
        self.assertEqual(len(payload["messages"]), 2)
        self.assertEqual(payload["max_tokens"], 100)

    def test_backend_vision_payload(self):
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
        content = payload["messages"][0]["content"]
        self.assertEqual(content[0]["type"], "text")
        self.assertEqual(content[1]["type"], "image_url")


class TestLiteLLMSettings(unittest.TestCase):
    def test_defaults(self):
        config = LLMConfig(provider="litellm")
        self.assertEqual(config.base_url, "http://localhost:4000")
        self.assertEqual(config.api_key, "LITELLM_API_KEY")
        self.assertEqual(config.client_backend, "litellm")

    def test_preserves_custom_values(self):
        config = LLMConfig(
            provider="litellm",
            base_url="http://my-proxy:8000",
            api_key="sk-my-key",
            chat_model="anthropic/claude-sonnet-4-6",
        )
        self.assertEqual(config.base_url, "http://my-proxy:8000")
        self.assertEqual(config.api_key, "sk-my-key")
        self.assertEqual(config.chat_model, "anthropic/claude-sonnet-4-6")

    def test_httpx_backend_preserved(self):
        config = LLMConfig(provider="litellm", client_backend="httpx")
        self.assertEqual(config.client_backend, "httpx")


class TestLiteLLMSDKClient(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.fake_litellm = _install_litellm_stub()

    def tearDown(self):
        sys.modules.pop("litellm", None)

    async def test_chat_calls_acompletion(self):
        from types import SimpleNamespace

        mock_response = SimpleNamespace(
            model_dump=lambda: {
                "choices": [{"message": {"content": "4", "role": "assistant"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 1, "total_tokens": 11},
            }
        )
        self.fake_litellm.acompletion.return_value = mock_response

        from memu.llm.litellm_sdk import LiteLLMSDKClient

        client = LiteLLMSDKClient(
            chat_model="anthropic/claude-sonnet-4-6",
            embed_model="text-embedding-3-small",
            api_key="sk-test",
        )

        text, _data = await client.chat("What is 2+2?", max_tokens=10)

        self.assertEqual(text, "4")
        self.fake_litellm.acompletion.assert_called_once()
        call_kwargs = self.fake_litellm.acompletion.call_args[1]
        self.assertEqual(call_kwargs["model"], "anthropic/claude-sonnet-4-6")
        self.assertTrue(call_kwargs["drop_params"])
        self.assertEqual(call_kwargs["api_key"], "sk-test")
        self.assertEqual(call_kwargs["max_tokens"], 10)

    async def test_chat_omits_api_key_when_none(self):
        from types import SimpleNamespace

        mock_response = SimpleNamespace(
            model_dump=lambda: {
                "choices": [{"message": {"content": "ok", "role": "assistant"}}],
            }
        )
        self.fake_litellm.acompletion.return_value = mock_response

        from memu.llm.litellm_sdk import LiteLLMSDKClient

        client = LiteLLMSDKClient(
            chat_model="openai/gpt-4o-mini",
            embed_model="text-embedding-3-small",
        )

        await client.chat("test")

        call_kwargs = self.fake_litellm.acompletion.call_args[1]
        self.assertNotIn("api_key", call_kwargs)
        self.assertNotIn("api_base", call_kwargs)

    async def test_embed_calls_aembedding(self):
        from types import SimpleNamespace

        mock_response = SimpleNamespace(
            model_dump=lambda: {
                "data": [{"embedding": [0.1, 0.2, 0.3]}],
                "usage": {"total_tokens": 5},
            }
        )
        self.fake_litellm.aembedding.return_value = mock_response

        from memu.llm.litellm_sdk import LiteLLMSDKClient

        client = LiteLLMSDKClient(
            chat_model="openai/gpt-4o-mini",
            embed_model="text-embedding-3-small",
        )

        embeddings, _data = await client.embed(["hello"])

        self.assertEqual(len(embeddings), 1)
        self.assertEqual(embeddings[0], [0.1, 0.2, 0.3])
        self.fake_litellm.aembedding.assert_called_once()
        call_kwargs = self.fake_litellm.aembedding.call_args[1]
        self.assertEqual(call_kwargs["model"], "text-embedding-3-small")
        self.assertTrue(call_kwargs["drop_params"])
