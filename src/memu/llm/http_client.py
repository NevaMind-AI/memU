from __future__ import annotations

import base64
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import httpx

from memu.llm.backends.anthropic import AnthropicLLMBackend
from memu.llm.backends.base import LLMBackend
from memu.llm.backends.doubao import DoubaoLLMBackend
from memu.llm.backends.grok import GrokBackend
from memu.llm.backends.openai import OpenAILLMBackend
from memu.llm.backends.openrouter import OpenRouterLLMBackend


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


class _OpenRouterEmbeddingBackend(_EmbeddingBackend):
    """OpenRouter uses OpenAI-compatible embedding API."""

    name = "openrouter"
    embedding_endpoint = "/api/v1/embeddings"

    def build_embedding_payload(self, *, inputs: list[str], embed_model: str) -> dict[str, Any]:
        return {"model": embed_model, "input": inputs}

    def parse_embedding_response(self, data: dict[str, Any]) -> list[list[float]]:
        return [cast(list[float], d["embedding"]) for d in data["data"]]


class _GeminiEmbeddingBackend(_EmbeddingBackend):
    """Gemini embedding API backend."""

    name = "gemini"
    embedding_endpoint = "/v1beta/models/{model}:batchEmbedContents"

    def build_embedding_payload(self, *, inputs: list[str], embed_model: str) -> dict[str, Any]:
        requests = [
            {"model": f"models/{embed_model}", "content": {"parts": [{"text": text}]}}
            for text in inputs
        ]
        return {"requests": requests}

    def parse_embedding_response(self, data: dict[str, Any]) -> list[list[float]]:
        embeddings = data.get("embeddings", [])
        return [emb["values"] for emb in embeddings]


logger = logging.getLogger(__name__)

LLM_BACKENDS: dict[str, Callable[[], LLMBackend]] = {
    OpenAILLMBackend.name: OpenAILLMBackend,
    DoubaoLLMBackend.name: DoubaoLLMBackend,
    GrokBackend.name: GrokBackend,
    OpenRouterLLMBackend.name: OpenRouterLLMBackend,
    AnthropicLLMBackend.name: AnthropicLLMBackend,
    "gemini": OpenAILLMBackend,  # Gemini uses embedding only; chat falls back to OpenAI format
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
        # Separate embedding provider settings
        embed_provider: str | None = None,
        embed_base_url: str | None = None,
        embed_api_key: str | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or ""
        self.chat_model = chat_model
        self.provider = provider.lower()
        self.backend = self._load_backend(self.provider)
        
        # Use separate embedding provider if specified
        self._embed_provider = (embed_provider or provider).lower()
        self._embed_base_url = (embed_base_url or base_url).rstrip("/")
        self._embed_api_key = embed_api_key or api_key or ""
        self.embedding_backend = self._load_embedding_backend(self._embed_provider)
        
        overrides = endpoint_overrides or {}
        self.summary_endpoint = overrides.get("chat") or overrides.get("summary") or self.backend.summary_endpoint
        self.embedding_endpoint = (
            overrides.get("embeddings")
            or overrides.get("embedding")
            or overrides.get("embed")
            or self.embedding_backend.embedding_endpoint
        )
        self.timeout = timeout
        self.embed_model = embed_model or chat_model

    async def chat(
        self,
        prompt: str,
        *,
        max_tokens: int | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.2,
    ) -> tuple[str, dict[str, Any]]:
        """Generic chat completion."""
        # Anthropic uses different payload format
        if self.provider == "anthropic":
            payload: dict[str, Any] = {
                "model": self.chat_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens or 1024,
            }
            if system_prompt is not None:
                payload["system"] = system_prompt
        else:
            messages: list[dict[str, Any]] = []
            if system_prompt is not None:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            payload = {
                "model": self.chat_model,
                "messages": messages,
                "temperature": temperature,
            }
            if max_tokens is not None:
                payload["max_tokens"] = max_tokens

        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            resp = await client.post(self.summary_endpoint, json=payload, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
        logger.debug("HTTP LLM chat response: %s", data)
        return self.backend.parse_summary_response(data), data

    async def summarize(
        self, text: str, max_tokens: int | None = None, system_prompt: str | None = None
    ) -> tuple[str, dict[str, Any]]:
        payload = self.backend.build_summary_payload(
            text=text, system_prompt=system_prompt, chat_model=self.chat_model, max_tokens=max_tokens
        )
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            resp = await client.post(self.summary_endpoint, json=payload, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
        logger.debug("HTTP LLM summarize response: %s", data)
        return self.backend.parse_summary_response(data), data

    async def vision(
        self,
        prompt: str,
        image_path: str,
        *,
        max_tokens: int | None = None,
        system_prompt: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """
        Call Vision API with an image.

        Args:
            prompt: Text prompt to send with the image
            image_path: Path to the image file
            max_tokens: Maximum tokens in response
            system_prompt: Optional system prompt

        Returns:
            Tuple of (LLM response text, raw response dict)
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

        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            resp = await client.post(self.summary_endpoint, json=payload, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
        logger.debug("HTTP LLM vision response: %s", data)
        return self.backend.parse_summary_response(data), data

    async def embed(self, inputs: list[str]) -> tuple[list[list[float]], dict[str, Any]]:
        """Create text embeddings using the provider-specific embedding API."""
        payload = self.embedding_backend.build_embedding_payload(inputs=inputs, embed_model=self.embed_model)
        
        # Gemini uses model name in endpoint path
        endpoint = self.embedding_endpoint
        if self._embed_provider == "gemini" and "{model}" in endpoint:
            endpoint = endpoint.format(model=self.embed_model)
        
        # Use separate embedding provider settings
        async with httpx.AsyncClient(base_url=self._embed_base_url, timeout=self.timeout) as client:
            resp = await client.post(endpoint, json=payload, headers=self._embed_headers())
            resp.raise_for_status()
            data = resp.json()
        logger.debug("HTTP embedding response: %s", data)
        return self.embedding_backend.parse_embedding_response(data), data

    async def transcribe(
        self,
        audio_path: str,
        *,
        prompt: str | None = None,
        language: str | None = None,
        response_format: str = "text",
    ) -> tuple[str, dict[str, Any] | None]:
        """
        Transcribe audio file using OpenAI Audio API.

        Args:
            audio_path: Path to the audio file
            prompt: Optional prompt to guide the transcription
            language: Optional language code (e.g., 'en', 'zh')
            response_format: Response format ('text', 'json', 'verbose_json')

        Returns:
            Tuple of (transcribed text, raw response dict or None for text format)
        """
        try:
            raw_response: dict[str, Any] | None = None
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
                        raw_response = resp.json()
                        result = raw_response.get("text", "")

            logger.debug("HTTP audio transcribe response for %s: %s chars", audio_path, len(result))
        except Exception:
            logger.exception("Audio transcription failed for %s", audio_path)
            raise
        else:
            return result or "", raw_response

    def _headers(self) -> dict[str, str]:
        if self.provider == "gemini":
            return {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}
        if self.provider == "anthropic":
            # Support both API key (x-api-key) and OAuth token (Bearer)
            # OAuth tokens start with "sk-ant-oat" 
            if self.api_key.startswith("sk-ant-oat"):
                return {
                    "Authorization": f"Bearer {self.api_key}",
                    "anthropic-version": "2023-06-01",
                    "anthropic-beta": "oauth-2025-04-20",
                    "Content-Type": "application/json",
                }
            else:
                return {
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                }
        return {"Authorization": f"Bearer {self.api_key}"}

    def _embed_headers(self) -> dict[str, str]:
        """Headers for embedding API (may use different provider)."""
        if self._embed_provider == "gemini":
            return {"x-goog-api-key": self._embed_api_key, "Content-Type": "application/json"}
        if self._embed_provider == "anthropic":
            if self._embed_api_key.startswith("sk-ant-oat"):
                return {
                    "Authorization": f"Bearer {self._embed_api_key}",
                    "anthropic-version": "2023-06-01",
                    "anthropic-beta": "oauth-2025-04-20",
                    "Content-Type": "application/json",
                }
            else:
                return {
                    "x-api-key": self._embed_api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                }
        return {"Authorization": f"Bearer {self._embed_api_key}"}

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
            "grok": _OpenAIEmbeddingBackend,
            _OpenRouterEmbeddingBackend.name: _OpenRouterEmbeddingBackend,
            _GeminiEmbeddingBackend.name: _GeminiEmbeddingBackend,
            # Anthropic doesn't have embedding API, use OpenAI-compatible as fallback
            "anthropic": _OpenAIEmbeddingBackend,
        }
        factory = backends.get(provider)
        if not factory:
            msg = f"Unsupported embedding provider '{provider}'. Available: {', '.join(backends.keys())}"
            raise ValueError(msg)
        return factory()
