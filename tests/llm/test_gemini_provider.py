import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from memu.app.settings import LLMConfig
from memu.llm.backends.gemini import GeminiLLMBackend
from memu.llm.http_client import HTTPLLMClient, LLM_BACKENDS, _OpenAIEmbeddingBackend


class TestGeminiSettings(unittest.TestCase):
    def test_settings_defaults(self):
        """provider='gemini' should set Gemini-specific defaults."""
        config = LLMConfig(provider="gemini")
        self.assertEqual(config.base_url, "https://generativelanguage.googleapis.com/v1beta/openai")
        self.assertEqual(config.api_key, "GEMINI_API_KEY")
        self.assertEqual(config.chat_model, "gemini-2.0-flash")
        self.assertEqual(config.embed_model, "gemini-embedding-001")

    def test_explicit_values_not_overridden(self):
        """Explicit values should not be replaced by defaults."""
        config = LLMConfig(
            provider="gemini",
            chat_model="gemini-2.5-flash",
            embed_model="gemini-embedding-001",
            api_key="my-real-key",
        )
        self.assertEqual(config.chat_model, "gemini-2.5-flash")
        self.assertEqual(config.embed_model, "gemini-embedding-001")
        self.assertEqual(config.api_key, "my-real-key")


class TestGeminiBackend(unittest.TestCase):
    def setUp(self):
        self.backend = GeminiLLMBackend()

    def test_backend_registered(self):
        """GeminiLLMBackend must be in the LLM_BACKENDS registry."""
        self.assertIn("gemini", LLM_BACKENDS)
        self.assertIsInstance(LLM_BACKENDS["gemini"](), GeminiLLMBackend)

    def test_summary_endpoint(self):
        self.assertEqual(self.backend.summary_endpoint, "/chat/completions")

    def test_build_summary_payload(self):
        payload = self.backend.build_summary_payload(
            text="Hello world",
            system_prompt="Be concise.",
            chat_model="gemini-2.0-flash",
            max_tokens=100,
        )
        self.assertEqual(payload["model"], "gemini-2.0-flash")
        self.assertEqual(payload["messages"][0]["role"], "system")
        self.assertEqual(payload["messages"][1]["content"], "Hello world")
        self.assertEqual(payload["max_tokens"], 100)

    def test_parse_summary_response(self):
        dummy = {"choices": [{"message": {"content": "Gemini reply", "role": "assistant"}}]}
        result = self.backend.parse_summary_response(dummy)
        self.assertEqual(result, "Gemini reply")

    def test_build_vision_payload(self):
        payload = self.backend.build_vision_payload(
            prompt="Describe this image",
            base64_image="abc123",
            mime_type="image/png",
            system_prompt=None,
            chat_model="gemini-2.0-flash",
            max_tokens=None,
        )
        self.assertEqual(payload["model"], "gemini-2.0-flash")
        content = payload["messages"][0]["content"]
        image_part = next(p for p in content if p["type"] == "image_url")
        self.assertIn("data:image/png;base64,abc123", image_part["image_url"]["url"])


class TestGeminiHTTPClient(unittest.TestCase):
    def test_client_loads_gemini_backend(self):
        """HTTPLLMClient with provider='gemini' should load GeminiLLMBackend."""
        client = HTTPLLMClient(
            base_url="https://generativelanguage.googleapis.com/v1beta/openai",
            api_key="fake-key",
            chat_model="gemini-2.0-flash",
            provider="gemini",
            embed_model="gemini-embedding-001",
        )
        self.assertIsInstance(client.backend, GeminiLLMBackend)
        self.assertIsInstance(client.embedding_backend, _OpenAIEmbeddingBackend)
        self.assertEqual(client.embed_model, "gemini-embedding-001")

    def test_embedding_endpoint(self):
        client = HTTPLLMClient(
            base_url="https://generativelanguage.googleapis.com/v1beta/openai",
            api_key="fake-key",
            chat_model="gemini-2.0-flash",
            provider="gemini",
            embed_model="gemini-embedding-001",
        )
        self.assertEqual(client.embedding_endpoint, "embeddings")


class TestGeminiLiveAPI(unittest.IsolatedAsyncioTestCase):
    """Live tests — skipped if GEMINI_API_KEY is not set."""

    def setUp(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            self.skipTest("GEMINI_API_KEY not set")
        self.client = HTTPLLMClient(
            base_url="https://generativelanguage.googleapis.com/v1beta/openai",
            api_key=self.api_key,
            chat_model="gemini-2.5-flash",
            provider="gemini",
            embed_model="gemini-embedding-001",
        )

    async def test_chat(self):
        response, _ = await self.client.chat("Say hello in one word.")
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)

    async def test_summarize(self):
        response, _ = await self.client.summarize("The sky is blue and the grass is green.")
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)

    async def test_embed(self):
        vectors, _ = await self.client.embed(["Hello world", "Gemini embeddings"])
        self.assertEqual(len(vectors), 2)
        self.assertEqual(len(vectors[0]), 3072)  # gemini-embedding-001 dimension


if __name__ == "__main__":
    unittest.main()
