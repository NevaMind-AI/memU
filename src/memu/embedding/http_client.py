from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Literal

import httpx

from memu.embedding.backends.base import EmbeddingBackend
from memu.embedding.backends.doubao import DoubaoEmbeddingBackend, DoubaoMultimodalEmbeddingInput
from memu.embedding.backends.openai import OpenAIEmbeddingBackend

logger = logging.getLogger(__name__)

EMBEDDING_BACKENDS: dict[str, Callable[[], EmbeddingBackend]] = {
    OpenAIEmbeddingBackend.name: OpenAIEmbeddingBackend,
    DoubaoEmbeddingBackend.name: DoubaoEmbeddingBackend,
}


class HTTPEmbeddingClient:
    """HTTP client for embedding APIs."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        embed_model: str,
        provider: str = "openai",
        endpoint_overrides: dict[str, str] | None = None,
        timeout: int = 60,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or ""
        self.embed_model = embed_model
        self.provider = provider.lower()
        self.backend = self._load_backend(self.provider)
        overrides = endpoint_overrides or {}
        self.embedding_endpoint = (
            overrides.get("embeddings")
            or overrides.get("embedding")
            or overrides.get("embed")
            or self.backend.embedding_endpoint
        )
        self.timeout = timeout

    async def embed(self, inputs: list[str]) -> list[list[float]]:
        """
        Create text embeddings.

        Args:
            inputs: List of text strings to embed

        Returns:
            List of embedding vectors
        """
        payload = self.backend.build_embedding_payload(inputs=inputs, embed_model=self.embed_model)
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            resp = await client.post(self.embedding_endpoint, json=payload, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
        logger.debug("HTTP embedding response: %s", data)
        return self.backend.parse_embedding_response(data)

    async def embed_multimodal(
        self,
        inputs: list[tuple[Literal["text", "image_url", "video_url"], str]],
        *,
        encoding_format: str = "float",
    ) -> list[list[float]]:
        """
        Create multimodal embeddings using Doubao embedding vision API.

        This method supports embedding a mix of text, images, and videos in a single request.
        Only available when using the 'doubao' provider.

        Args:
            inputs: List of tuples where each tuple contains:
                - input_type: One of 'text', 'image_url', or 'video_url'
                - content: The text content or URL to the image/video
            encoding_format: Encoding format for the embeddings ('float' or 'base64')

        Returns:
            List of embedding vectors

        Example:
            >>> client = HTTPEmbeddingClient(
            ...     base_url="https://ark.cn-beijing.volces.com",
            ...     api_key="your-api-key",
            ...     embed_model="doubao-embedding-vision-250615",
            ...     provider="doubao",
            ... )
            >>> embeddings = await client.embed_multimodal([
            ...     ("text", "What is in the image and video?"),
            ...     ("image_url", "https://example.com/image.png"),
            ...     ("video_url", "https://example.com/video.mp4"),
            ... ])

        Raises:
            TypeError: If the backend does not support multimodal embeddings
        """
        if not isinstance(self.backend, DoubaoEmbeddingBackend):
            msg = (
                f"Multimodal embedding is only supported by 'doubao' provider, "
                f"but current provider is '{self.provider}'"
            )
            raise TypeError(msg)

        multimodal_inputs = [
            DoubaoMultimodalEmbeddingInput(input_type=input_type, content=content) for input_type, content in inputs
        ]

        payload = self.backend.build_multimodal_embedding_payload(
            inputs=multimodal_inputs,
            embed_model=self.embed_model,
            encoding_format=encoding_format,
        )

        endpoint = self.backend.multimodal_embedding_endpoint
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            resp = await client.post(endpoint, json=payload, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()

        logger.debug("HTTP multimodal embedding response: %s", data)
        return self.backend.parse_multimodal_embedding_response(data)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    def _load_backend(self, provider: str) -> EmbeddingBackend:
        factory = EMBEDDING_BACKENDS.get(provider)
        if not factory:
            msg = f"Unsupported embedding provider '{provider}'. Available: {', '.join(EMBEDDING_BACKENDS.keys())}"
            raise ValueError(msg)
        return factory()
