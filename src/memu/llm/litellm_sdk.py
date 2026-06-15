from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Any, cast

logger = logging.getLogger(__name__)


class LiteLLMSDKClient:
    """LLM client using the LiteLLM Python SDK for 100+ provider support."""

    def __init__(
        self,
        *,
        chat_model: str,
        embed_model: str,
        api_key: str | None = None,
        api_base: str | None = None,
        embed_batch_size: int = 1,
    ):
        self.chat_model = chat_model
        self.embed_model = embed_model
        self.api_key = api_key or None
        self.api_base = api_base or None
        self.embed_batch_size = embed_batch_size

    async def chat(
        self,
        prompt: str,
        *,
        max_tokens: int | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.2,
    ) -> tuple[str, dict[str, Any]]:
        import litellm

        messages: list[dict[str, str]] = []
        if system_prompt is not None:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        kwargs: dict[str, Any] = {
            "model": self.chat_model,
            "messages": messages,
            "temperature": temperature,
            "drop_params": True,
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.api_base:
            kwargs["api_base"] = self.api_base

        response = await litellm.acompletion(**kwargs)
        data = response.model_dump()
        content = data["choices"][0]["message"]["content"] or ""
        logger.debug("LiteLLM chat response: %s", data)
        return content, data

    async def summarize(
        self,
        text: str,
        *,
        max_tokens: int | None = None,
        system_prompt: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        prompt = system_prompt or "Summarize the text in one short paragraph."
        return await self.chat(
            text,
            max_tokens=max_tokens,
            system_prompt=prompt,
            temperature=0.2,
        )

    async def vision(
        self,
        prompt: str,
        image_path: str,
        *,
        max_tokens: int | None = None,
        system_prompt: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        import litellm

        image_data = Path(image_path).read_bytes()
        base64_image = base64.b64encode(image_data).decode("utf-8")

        suffix = Path(image_path).suffix.lower()
        mime_type = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }.get(suffix, "image/jpeg")

        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}},
            ],
        })

        kwargs: dict[str, Any] = {
            "model": self.chat_model,
            "messages": messages,
            "temperature": 0.2,
            "drop_params": True,
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.api_base:
            kwargs["api_base"] = self.api_base

        response = await litellm.acompletion(**kwargs)
        data = response.model_dump()
        content = data["choices"][0]["message"]["content"] or ""
        logger.debug("LiteLLM vision response: %s", data)
        return content, data

    async def embed(self, inputs: list[str]) -> tuple[list[list[float]], dict[str, Any] | None]:
        import litellm

        kwargs: dict[str, Any] = {"model": self.embed_model, "drop_params": True}
        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.api_base:
            kwargs["api_base"] = self.api_base

        if len(inputs) <= self.embed_batch_size:
            response = await litellm.aembedding(input=inputs, **kwargs)
            data = response.model_dump()
            return [cast(list[float], d["embedding"]) for d in data["data"]], data

        all_embeddings: list[list[float]] = []
        last_data: dict[str, Any] | None = None
        for idx in range(0, len(inputs), self.embed_batch_size):
            batch = inputs[idx : idx + self.embed_batch_size]
            response = await litellm.aembedding(input=batch, **kwargs)
            data = response.model_dump()
            all_embeddings.extend([cast(list[float], d["embedding"]) for d in data["data"]])
            last_data = data

        return all_embeddings, last_data
