from __future__ import annotations

import os
from collections.abc import Callable
from typing import cast

import httpx
import numpy as np

from memu.llm.backends.base import HTTPBackend
from memu.llm.backends.openai import OpenAIHTTPBackend

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
        self.fake = bool(os.getenv("MEMUFLOW_FAKE_OPENAI")) or not bool(self.api_key)
        self.timeout = timeout

    async def summarize(self, text: str, max_tokens: int = 160, system_prompt: str | None = None) -> str:
        if self.fake:
            s = " ".join(text.strip().split())
            return s[:200] + ("..." if len(s) > 200 else "")

        payload = self.backend.build_summary_payload(
            text=text, system_prompt=system_prompt, chat_model=self.chat_model, max_tokens=max_tokens
        )
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            resp = await client.post(self.summary_endpoint, json=payload, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
        return self.backend.parse_summary_response(data)

    async def embed(self, inputs: list[str]) -> list[list[float]]:
        if self.fake:
            return [self._fake_vec(x) for x in inputs]
        payload = self.backend.build_embedding_payload(inputs=inputs, embed_model=self.embed_model)
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            resp = await client.post(self.embedding_endpoint, json=payload, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
        return self.backend.parse_embedding_response(data)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    def _fake_vec(self, s: str, dim: int = 256) -> list[float]:
        import hashlib

        h = hashlib.sha256(s.encode("utf-8")).digest()
        b = (h * (dim // len(h) + 1))[:dim]
        arr = np.frombuffer(b, dtype=np.uint8).astype(np.float32)
        arr = (arr - arr.mean()) / (arr.std() + 1e-6)
        arr = arr / (np.linalg.norm(arr) + 1e-9)
        return cast(list[float], arr.tolist())

    def _load_backend(self, provider: str) -> HTTPBackend:
        factory = HTTP_BACKENDS.get(provider)
        if not factory:
            msg = f"Unsupported HTTP LLM provider '{provider}'. Available: {', '.join(HTTP_BACKENDS.keys())}"
            raise ValueError(msg)
        return factory()
