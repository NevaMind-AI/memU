from __future__ import annotations

import logging
from collections.abc import Callable

import httpx

from memu.llm.backends.base import HTTPBackend
from memu.llm.backends.openai import OpenAIHTTPBackend

logger = logging.getLogger(__name__)

HTTP_BACKENDS: dict[str, Callable[[], HTTPBackend]] = {
    OpenAIHTTPBackend.name: OpenAIHTTPBackend,
}


class HTTPLLMClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        chat_model: str,
        embed_model: str,
        provider: str = "openai",
        endpoint_overrides: dict[str, str] | None = None,
        timeout: int = 60,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or ""
        self.chat_model = chat_model
        self.embed_model = embed_model
        self.provider = provider.lower()
        self.backend = self._load_backend(self.provider)
        overrides = endpoint_overrides or {}
        self.summary_endpoint = overrides.get("chat") or overrides.get("summary") or self.backend.summary_endpoint
        self.embedding_endpoint = (
            overrides.get("embeddings")
            or overrides.get("embedding")
            or overrides.get("embed")
            or self.backend.embedding_endpoint
        )
        self.timeout = timeout

    async def summarize(self, text: str, max_tokens: int | None = None, system_prompt: str | None = None) -> str:
        payload = self.backend.build_summary_payload(
            text=text, system_prompt=system_prompt, chat_model=self.chat_model, max_tokens=max_tokens
        )
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            resp = await client.post(self.summary_endpoint, json=payload, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
        logger.debug("HTTP LLM summarize response: %s", data)
        return self.backend.parse_summary_response(data)

    async def embed(self, inputs: list[str]) -> list[list[float]]:
        payload = self.backend.build_embedding_payload(inputs=inputs, embed_model=self.embed_model)
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            resp = await client.post(self.embedding_endpoint, json=payload, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
        logger.debug("HTTP LLM embedding response: %s", data)
        return self.backend.parse_embedding_response(data)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    def _load_backend(self, provider: str) -> HTTPBackend:
        factory = HTTP_BACKENDS.get(provider)
        if not factory:
            msg = f"Unsupported HTTP LLM provider '{provider}'. Available: {', '.join(HTTP_BACKENDS.keys())}"
            raise ValueError(msg)
        return factory()
