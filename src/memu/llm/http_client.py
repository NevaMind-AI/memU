from __future__ import annotations

import base64
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import httpx

from memu.llm.backends.base import LLMBackend
from memu.llm.backends.claude import ClaudeLLMBackend
from memu.llm.backends.deepseek import DeepSeekLLMBackend
from memu.llm.backends.doubao import DoubaoLLMBackend
from memu.llm.backends.gemini import GeminiLLMBackend
from memu.llm.backends.openai import OpenAILLMBackend
from memu.llm.backends.openrouter import OpenRouterLLMBackend
from memu.llm.backends.qwen import Qwen3LLMBackend, QwenLLMBackend


# Minimal embedding backend support (moved from embedding module)
class _EmbeddingBackend:
    name: str
    embedding_endpoint: str

    def build_embedding_payload(self, *, inputs: list[str], embed_model: str) -> dict[str, Any]:
        raise NotImplementedError

    def parse_embedding_response(self, data: dict[str, Any]) -> list[list[float]]:
        raise NotImplementedError


class _OpenAIEmbeddingBackend(_EmbeddingBackend):
    name = "openai"
    embedding_endpoint = "/embeddings"

    def build_embedding_payload(self, *, inputs: list[str], embed_model: str) -> dict[str, Any]:
        return {"model": embed_model, "input": inputs}

    def parse_embedding_response(self, data: dict[str, Any]) -> list[list[float]]:
        return [cast(list[float], d["embedding"]) for d in data["data"]]


class _DoubaoEmbeddingBackend(_EmbeddingBackend):
    name = "doubao"
    embedding_endpoint = "/api/v3/embeddings"

    def build_embedding_payload(self, *, inputs: list[str], embed_model: str) -> dict[str, Any]:
        return {"model": embed_model, "input": inputs, "encoding_format": "float"}

    def parse_embedding_response(self, data: dict[str, Any]) -> list[list[float]]:
        return [cast(list[float], d["embedding"]) for d in data["data"]]


class _VoyageEmbeddingBackend(_EmbeddingBackend):
    name = "voyage"
    embedding_endpoint = "/embeddings"  # base_url should include /v1

    def build_embedding_payload(self, *, inputs: list[str], embed_model: str) -> dict[str, Any]:
        return {"model": embed_model, "input": inputs, "input_type": "document"}

    def parse_embedding_response(self, data: dict[str, Any]) -> list[list[float]]:
        return [cast(list[float], d["embedding"]) for d in data["data"]]


class _JinaEmbeddingBackend(_EmbeddingBackend):
    name = "jina"
    embedding_endpoint = "/embeddings"  # base_url should include /v1

    def build_embedding_payload(self, *, inputs: list[str], embed_model: str) -> dict[str, Any]:
        # Jina v3 models don't accept encoding_format parameter
        return {"model": embed_model, "input": inputs}

    def parse_embedding_response(self, data: dict[str, Any]) -> list[list[float]]:
        return [cast(list[float], d["embedding"]) for d in data["data"]]


class _QwenEmbeddingBackend(_EmbeddingBackend):
    name = "qwen"
    embedding_endpoint = "/compatible-mode/v1/embeddings"

    def build_embedding_payload(self, *, inputs: list[str], embed_model: str) -> dict[str, Any]:
        return {"model": embed_model, "input": inputs, "encoding_format": "float"}

    def parse_embedding_response(self, data: dict[str, Any]) -> list[list[float]]:
        return [cast(list[float], d["embedding"]) for d in data["data"]]


logger = logging.getLogger(__name__)

LLM_BACKENDS: dict[str, Callable[[], LLMBackend]] = {
    OpenAILLMBackend.name: OpenAILLMBackend,
    DoubaoLLMBackend.name: DoubaoLLMBackend,
    OpenRouterLLMBackend.name: OpenRouterLLMBackend,
    ClaudeLLMBackend.name: ClaudeLLMBackend,
    GeminiLLMBackend.name: GeminiLLMBackend,
    DeepSeekLLMBackend.name: DeepSeekLLMBackend,
    QwenLLMBackend.name: QwenLLMBackend,
    Qwen3LLMBackend.name: Qwen3LLMBackend,
}


class HTTPLLMClient:
    """HTTP client for LLM APIs (chat, vision, transcription) and embeddings."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        chat_model: str,
        provider: str = "openai",
        endpoint_overrides: dict[str, str] | None = None,
        timeout: int = 60,
        embed_model: str | None = None,
        # Separate embedding configuration (if different from LLM provider)
        embed_provider: str | None = None,
        embed_base_url: str | None = None,
        embed_api_key: str | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or ""
        self.chat_model = chat_model
        self.provider = provider.lower()
        self.backend = self._load_backend(self.provider)
        self.timeout = timeout
        self.embed_model = embed_model or chat_model

        # Setup embedding: use separate provider if configured, otherwise use main provider
        self._embed_provider = (embed_provider or provider).lower()
        self._embed_base_url = (embed_base_url or base_url).rstrip("/")
        self._embed_api_key = embed_api_key or api_key or ""
        self._has_separate_embed = embed_provider is not None or embed_base_url is not None

        self.embedding_backend = self._load_embedding_backend(self._embed_provider)
        overrides = endpoint_overrides or {}
        self.summary_endpoint = overrides.get("chat") or overrides.get("summary") or self.backend.summary_endpoint
        self.embedding_endpoint = (
            overrides.get("embeddings")
            or overrides.get("embedding")
            or overrides.get("embed")
            or self.embedding_backend.embedding_endpoint
        )

    async def summarize(self, text: str, max_tokens: int | None = None, system_prompt: str | None = None) -> str:
        payload = self.backend.build_summary_payload(
            text=text, system_prompt=system_prompt, chat_model=self.chat_model, max_tokens=max_tokens
        )
        # Get endpoint (may be model-specific for Gemini)
        endpoint = self.backend.get_endpoint(self.chat_model)
        endpoint = self._get_url_with_auth(endpoint)

        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            resp = await client.post(endpoint, json=payload, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
        logger.debug("HTTP LLM summarize response: %s", data)
        return self.backend.parse_summary_response(data)

    async def vision(
        self,
        prompt: str,
        image_path: str,
        *,
        max_tokens: int | None = None,
        system_prompt: str | None = None,
    ) -> str:
        """
        Call Vision API with an image.

        Args:
            prompt: Text prompt to send with the image
            image_path: Path to the image file
            max_tokens: Maximum tokens in response
            system_prompt: Optional system prompt

        Returns:
            LLM response text
        """
        # Read and encode image as base64
        image_data = Path(image_path).read_bytes()
        base64_image = base64.b64encode(image_data).decode("utf-8")

        # Detect image format
        suffix = Path(image_path).suffix.lower()
        mime_type = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }.get(suffix, "image/jpeg")

        payload = self.backend.build_vision_payload(
            prompt=prompt,
            base64_image=base64_image,
            mime_type=mime_type,
            system_prompt=system_prompt,
            chat_model=self.chat_model,
            max_tokens=max_tokens,
        )

        # Get endpoint (may be model-specific for Gemini)
        endpoint = self.backend.get_endpoint(self.chat_model)
        endpoint = self._get_url_with_auth(endpoint)

        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            resp = await client.post(endpoint, json=payload, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
        logger.debug("HTTP LLM vision response: %s", data)
        return self.backend.parse_summary_response(data)

    async def embed(self, inputs: list[str]) -> list[list[float]]:
        """Create text embeddings using the provider-specific embedding API."""
        payload = self.embedding_backend.build_embedding_payload(inputs=inputs, embed_model=self.embed_model)
        # Use separate embedding base_url and api_key if configured
        embed_headers = {"Authorization": f"Bearer {self._embed_api_key}"}
        async with httpx.AsyncClient(base_url=self._embed_base_url, timeout=self.timeout) as client:
            resp = await client.post(self.embedding_endpoint, json=payload, headers=embed_headers)
            resp.raise_for_status()
            data = resp.json()
        logger.debug("HTTP embedding response: %s", data)
        return self.embedding_backend.parse_embedding_response(data)

    async def transcribe(
        self,
        audio_path: str,
        *,
        prompt: str | None = None,
        language: str | None = None,
        response_format: str = "text",
    ) -> str:
        """
        Transcribe audio file using OpenAI Audio API.

        Args:
            audio_path: Path to the audio file
            prompt: Optional prompt to guide the transcription
            language: Optional language code (e.g., 'en', 'zh')
            response_format: Response format ('text', 'json', 'verbose_json')

        Returns:
            Transcribed text
        """
        try:
            # Prepare multipart form data
            with open(audio_path, "rb") as audio_file:
                files = {"file": (Path(audio_path).name, audio_file, "application/octet-stream")}
                data = {
                    "model": "gpt-4o-mini-transcribe",
                    "response_format": response_format,
                }
                if prompt:
                    data["prompt"] = prompt
                if language:
                    data["language"] = language

                async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout * 3) as client:
                    resp = await client.post(
                        "/v1/audio/transcriptions",
                        files=files,
                        data=data,
                        headers=self._headers(),
                    )
                    resp.raise_for_status()

                    if response_format == "text":
                        result = resp.text
                    else:
                        result_data = resp.json()
                        result = result_data.get("text", "")

            logger.debug("HTTP audio transcribe response for %s: %s chars", audio_path, len(result))
        except Exception:
            logger.exception("Audio transcription failed for %s", audio_path)
            raise
        else:
            return result or ""

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        # Handle different authentication methods
        if self.backend.uses_query_param_auth():
            # Gemini uses API key in query parameter, no auth header needed
            pass
        elif self.provider == "claude":
            # Claude uses x-api-key header instead of Authorization
            headers["x-api-key"] = self.api_key
        else:
            # Default: Bearer token authentication
            headers["Authorization"] = f"Bearer {self.api_key}"
        # Add any extra headers required by the backend
        headers.update(self.backend.get_extra_headers())
        return headers

    def _get_url_with_auth(self, endpoint: str) -> str:
        """Get URL with query parameter auth if needed (for Gemini)."""
        if self.backend.uses_query_param_auth():
            separator = "&" if "?" in endpoint else "?"
            return f"{endpoint}{separator}key={self.api_key}"
        return endpoint

    def _load_backend(self, provider: str) -> LLMBackend:
        factory = LLM_BACKENDS.get(provider)
        if not factory:
            msg = f"Unsupported LLM provider '{provider}'. Available: {', '.join(LLM_BACKENDS.keys())}"
            raise ValueError(msg)
        return factory()

    def _load_embedding_backend(self, provider: str) -> _EmbeddingBackend:
        backends: dict[str, type[_EmbeddingBackend]] = {
            _OpenAIEmbeddingBackend.name: _OpenAIEmbeddingBackend,
            _DoubaoEmbeddingBackend.name: _DoubaoEmbeddingBackend,
            _VoyageEmbeddingBackend.name: _VoyageEmbeddingBackend,
            _JinaEmbeddingBackend.name: _JinaEmbeddingBackend,
            _QwenEmbeddingBackend.name: _QwenEmbeddingBackend,
            # Aliases for convenience
            "openrouter": _OpenAIEmbeddingBackend,  # OpenRouter uses OpenAI-compatible format
            "claude": _OpenAIEmbeddingBackend,  # Claude doesn't have embeddings, fallback
            "gemini": _OpenAIEmbeddingBackend,  # Gemini embeddings use different API
            "deepseek": _OpenAIEmbeddingBackend,  # DeepSeek uses OpenAI-compatible format
        }
        factory = backends.get(provider)
        if not factory:
            msg = f"Unsupported embedding provider '{provider}'. Available: {', '.join(backends.keys())}"
            raise ValueError(msg)
        return factory()
