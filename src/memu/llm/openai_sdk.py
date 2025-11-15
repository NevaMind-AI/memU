import os
from typing import TYPE_CHECKING, cast

import numpy as np

if TYPE_CHECKING:
    from openai import AsyncOpenAI  # 只给类型检查用

try:
    import openai
except ImportError:
    openai = None  # 运行时用来判断有没有这个库


class OpenAISDKClient:
    """OpenAI client that relies on the official Python SDK."""

    def __init__(self, *, base_url: str, api_key: str, chat_model: str, embed_model: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or ""
        self.chat_model = chat_model
        self.embed_model = embed_model
        self.fake = bool(os.getenv("MEMUFLOW_FAKE_OPENAI")) or not bool(self.api_key)
        self.client: AsyncOpenAI | None = None
        if self.fake:
            self.client = None
        else:
            if openai is None:
                msg = "The 'openai' Python package is required for the SDK client. Install it via `pip install openai` or switch to the httpx backend."
                raise RuntimeError(msg)
            self.client = openai.AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

    async def summarize(
        self,
        text: str,
        *,
        max_tokens: int = 160,
        system_prompt: str | None = None,
    ) -> str:
        prompt = system_prompt or "Summarize the text in one short paragraph."
        if self.fake:
            s = " ".join(text.strip().split())
            return s[:200] + ("..." if len(s) > 200 else "")
        if self.client is None:
            msg = "The 'openai' Python package is required for the SDK client. Install it via `pip install openai` or switch to the httpx backend."
            raise RuntimeError(msg)
        response = await self.client.chat.completions.create(
            model=self.chat_model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text},
            ],
            temperature=0.2,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content
        return content or ""

    async def embed(self, inputs: list[str]) -> list[list[float]]:
        if self.fake:
            return [self._fake_vec(x) for x in inputs]
        if self.client is None:
            msg = "The 'openai' Python package is required for the SDK client. Install it via `pip install openai` or switch to the httpx backend."
            raise RuntimeError(msg)
        response = await self.client.embeddings.create(model=self.embed_model, input=inputs)
        return [cast(list[float], d.embedding) for d in response.data]

    def _fake_vec(self, s: str, dim: int = 256) -> list[float]:
        # deterministic pseudo-embedding for offline demo
        import hashlib

        h = hashlib.sha256(s.encode("utf-8")).digest()
        b = (h * (dim // len(h) + 1))[:dim]
        arr = np.frombuffer(b, dtype=np.uint8).astype(np.float32)
        arr = (arr - arr.mean()) / (arr.std() + 1e-6)
        arr = arr / (np.linalg.norm(arr) + 1e-9)
        return arr.tolist()
