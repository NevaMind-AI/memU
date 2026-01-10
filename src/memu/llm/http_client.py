from __future__ import annotations

import base64
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import httpx

from memu.llm.backends.base import LLMBackend
from memu.llm.backends.doubao import DoubaoLLMBackend
from memu.llm.backends.gemini import GeminiLLMBackend
from memu.llm.backends.openai import OpenAILLMBackend


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


class _GeminiEmbeddingBackend(_EmbeddingBackend):
    name = "gemini"
    embedding_endpoint = "/models/{model}:batchEmbedContents"

    @staticmethod
    def _normalize_model_name(model: str) -> str:
        normalized = model.strip()
        if normalized.startswith("models/"):
            return normalized
        return f"models/{normalized}"

    def build_embedding_payload(self, *, inputs: list[str], embed_model: str) -> dict[str, Any]:
        model_name = self._normalize_model_name(embed_model)
        requests: list[dict[str, Any]] = []
        for text in inputs:
            requests.append({"model": model_name, "content": {"parts": [{"text": text}]}})
        return {"requests": requests}

    def parse_embedding_response(self, data: dict[str, Any]) -> list[list[float]]:
        embeddings: list[list[float]] = []
        items = data.get("embeddings")
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                values = item.get("values")
                if isinstance(values, list):
                    embeddings.append([float(v) for v in values])
        if embeddings:
            return embeddings
        single = data.get("embedding")
        if isinstance(single, dict):
            values = single.get("values")
            if isinstance(values, list):
                return [[float(v) for v in values]]
        return []


logger = logging.getLogger(__name__)

LLM_BACKENDS: dict[str, Callable[[], LLMBackend]] = {
    OpenAILLMBackend.name: OpenAILLMBackend,
    DoubaoLLMBackend.name: DoubaoLLMBackend,
    GeminiLLMBackend.name: GeminiLLMBackend,
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
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or ""
        self.chat_model = chat_model
        self.provider = provider.lower()
        self.backend = self._load_backend(self.provider)
        self.embedding_backend = self._load_embedding_backend(self.provider)
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
    async def summarize(
        self, text: str, max_tokens: int | None = None, system_prompt: str | None = None
    ) -> tuple[str, dict[str, Any]]:
        payload = self.backend.build_summary_payload(
            text=text, system_prompt=system_prompt, chat_model=self.chat_model, max_tokens=max_tokens
        )
        endpoint = self._format_endpoint(self.summary_endpoint, self.chat_model)
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            resp = await client.post(endpoint, json=payload, headers=self._headers())
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

        endpoint = self._format_endpoint(self.summary_endpoint, self.chat_model)
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            resp = await client.post(endpoint, json=payload, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
        logger.debug("HTTP LLM vision response: %s", data)
        return self.backend.parse_summary_response(data), data

    async def embed(self, inputs: list[str]) -> tuple[list[list[float]], dict[str, Any]]:
        """Create text embeddings using the provider-specific embedding API."""
        payload = self.embedding_backend.build_embedding_payload(inputs=inputs, embed_model=self.embed_model)
        endpoint = self._format_endpoint(self.embedding_endpoint, self.embed_model)
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            resp = await client.post(endpoint, json=payload, headers=self._headers())
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
            return {"x-goog-api-key": self.api_key}
        return {"Authorization": f"Bearer {self.api_key}"}

    @staticmethod
    def _format_endpoint(endpoint: str, model: str) -> str:
        if "{model}" not in endpoint:
            return endpoint
        normalized = model
        if "models/{model}" in endpoint and normalized.startswith("models/"):
            normalized = normalized[len("models/") :]
        return endpoint.replace("{model}", normalized)

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
            _GeminiEmbeddingBackend.name: _GeminiEmbeddingBackend,
        }
        factory = backends.get(provider)
        if not factory:
            msg = f"Unsupported embedding provider '{provider}'. Available: {', '.join(backends.keys())}"
            raise ValueError(msg)
        return factory()
