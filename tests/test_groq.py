"""
Tests for Groq LLM provider integration.

Run tests:
    export GROQ_API_KEY=your_key
    export OPENAI_API_KEY=your_key_for_embeddings
    pytest tests/test_groq.py -v
"""

import os
import pytest

from memu.app import MemoryService
from memu.llm.backends.groq import GroqLLMBackend
from memu.llm.http_client import HTTPLLMClient


class TestGroqBackend:
    """Test Groq backend implementation."""

    def test_backend_initialization(self):
        """Test Groq backend can be instantiated."""
        backend = GroqLLMBackend()
        assert backend.name == "groq"
        assert backend.summary_endpoint == "/chat/completions"

    def test_build_summary_payload(self):
        """Test summary payload construction."""
        backend = GroqLLMBackend()
        payload = backend.build_summary_payload(
            text="Hello world",
            system_prompt="Be concise",
            chat_model="llama-3.3-70b-versatile",
            max_tokens=100
        )
        
        assert payload["model"] == "llama-3.3-70b-versatile"
        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][0]["content"] == "Be concise"
        assert payload["messages"][1]["role"] == "user"
        assert payload["messages"][1]["content"] == "Hello world"
        assert payload["temperature"] == 0.2
        assert payload["max_tokens"] == 100

    def test_build_vision_payload(self):
        """Test vision payload construction."""
        backend = GroqLLMBackend()
        payload = backend.build_vision_payload(
            prompt="Describe this image",
            base64_image="base64encodedimage",
            mime_type="image/jpeg",
            system_prompt="Be descriptive",
            chat_model="llama-3.2-90b-vision-preview",
            max_tokens=200
        )
        
        assert payload["model"] == "llama-3.2-90b-vision-preview"
        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][1]["role"] == "user"
        assert payload["messages"][1]["content"][0]["type"] == "text"
        assert payload["messages"][1]["content"][1]["type"] == "image_url"
        assert "base64encodedimage" in payload["messages"][1]["content"][1]["image_url"]["url"]


class TestGroqHTTPClient:
    """Test HTTP client with Groq backend."""

    @pytest.mark.skipif(not os.getenv("GROQ_API_KEY"), reason="GROQ_API_KEY not set")
    async def test_http_client_initialization(self):
        """Test HTTP client can be initialized with Groq."""
        client = HTTPLLMClient(
            base_url="https://api.groq.com/openai/v1",
            api_key=os.getenv("GROQ_API_KEY"),
            chat_model="llama-3.3-70b-versatile",
            provider="groq"
        )
        assert client.provider == "groq"
        assert client.backend.name == "groq"

    @pytest.mark.skipif(not os.getenv("GROQ_API_KEY"), reason="GROQ_API_KEY not set")
    async def test_groq_summarize(self):
        """Test actual summarization with Groq API."""
        client = HTTPLLMClient(
            base_url="https://api.groq.com/openai/v1",
            api_key=os.getenv("GROQ_API_KEY"),
            chat_model="llama-3.3-70b-versatile",
            provider="groq"
        )
        
        result, raw = await client.summarize(
            text="Artificial intelligence is transforming the world. "
                 "Machine learning enables computers to learn from data.",
            max_tokens=50
        )
        
        assert isinstance(result, str)
        assert len(result) > 0
        assert "choices" in raw


class TestGroqMemoryService:
    """Test MemoryService with Groq integration."""

    @pytest.mark.skipif(
        not (os.getenv("GROQ_API_KEY") and os.getenv("OPENAI_API_KEY")),
        reason="GROQ_API_KEY and OPENAI_API_KEY required"
    )
    async def test_memory_service_with_groq(self):
        """Test MemoryService can be initialized with Groq."""
        service = MemoryService(
            llm_profiles={
                "default": {
                    "provider": "groq",
                    "base_url": "https://api.groq.com/openai/v1",
                    "api_key": os.getenv("GROQ_API_KEY"),
                    "chat_model": "llama-3.3-70b-versatile",
                    "client_backend": "http"
                },
                "embedding": {
                    "provider": "openai",
                    "api_key": os.getenv("OPENAI_API_KEY"),
                    "embed_model": "text-embedding-3-small"
                }
            }
        )
        
        # Service should be properly initialized
        assert service is not None

    @pytest.mark.skipif(
        not (os.getenv("GROQ_API_KEY") and os.getenv("OPENAI_API_KEY")),
        reason="API keys required"
    )
    async def test_groq_model_variants(self):
        """Test different Groq models can be used."""
        models = [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768"
        ]
        
        for model in models:
            service = MemoryService(
                llm_profiles={
                    "default": {
                        "provider": "groq",
                        "base_url": "https://api.groq.com/openai/v1",
                        "api_key": os.getenv("GROQ_API_KEY"),
                        "chat_model": model,
                        "client_backend": "http"
                    },
                    "embedding": {
                        "provider": "openai",
                        "api_key": os.getenv("OPENAI_API_KEY"),
                        "embed_model": "text-embedding-3-small"
                    }
                }
            )
            assert service is not None
