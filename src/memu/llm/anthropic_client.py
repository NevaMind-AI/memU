from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from anthropic.types import Message

logger = logging.getLogger(__name__)

# Anthropic requires max_tokens on every request; fall back to this when omitted.
_DEFAULT_MAX_TOKENS = 1024

_MIME_BY_SUFFIX = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


class AnthropicClient:
    """Claude LLM client that relies on the official Anthropic Python SDK.

    Mirrors the surface of :class:`memu.llm.openai_client.OpenAIClient` so it can
    be wrapped by :class:`memu.llm.wrapper.LLMClientWrapper`. Anthropic does not
    offer audio transcription, so that method raises. Embedding is handled by the
    dedicated :mod:`memu.embedding` clients.
    """

    def __init__(
        self,
        *,
        base_url: str | None,
        api_key: str,
        chat_model: str,
        max_tokens: int | None = None,
    ):
        # Imported lazily so the optional ``anthropic`` dependency is only
        # required when this client is actually used.
        from anthropic import AsyncAnthropic

        self.base_url = base_url.rstrip("/") if base_url else None
        self.api_key = api_key or ""
        self.chat_model = chat_model
        self.max_tokens = max_tokens or _DEFAULT_MAX_TOKENS
        self.client = AsyncAnthropic(api_key=self.api_key, base_url=self.base_url)

    async def chat(
        self,
        prompt: str,
        *,
        max_tokens: int | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.2,
    ) -> tuple[str, Message]:
        """Generic chat completion via the Messages API."""
        kwargs: dict[str, Any] = {
            "model": self.chat_model,
            "max_tokens": max_tokens or self.max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt is not None:
            kwargs["system"] = system_prompt

        response = await self.client.messages.create(**kwargs)
        logger.debug("Anthropic chat response: %s", response)
        return _extract_text(response), response

    async def summarize(
        self,
        text: str,
        *,
        max_tokens: int | None = None,
        system_prompt: str | None = None,
    ) -> tuple[str, Message]:
        system = system_prompt or "Summarize the text in one short paragraph."
        response = await self.client.messages.create(
            model=self.chat_model,
            max_tokens=max_tokens or self.max_tokens,
            system=system,
            messages=[{"role": "user", "content": text}],
        )
        logger.debug("Anthropic summarize response: %s", response)
        return _extract_text(response), response

    async def vision(
        self,
        prompt: str,
        image_path: str,
        *,
        max_tokens: int | None = None,
        system_prompt: str | None = None,
    ) -> tuple[str, Message]:
        """Analyze an image alongside a text prompt via the Messages API."""
        image_data = Path(image_path).read_bytes()
        base64_image = base64.b64encode(image_data).decode("utf-8")
        mime_type = _MIME_BY_SUFFIX.get(Path(image_path).suffix.lower(), "image/jpeg")

        kwargs: dict[str, Any] = {
            "model": self.chat_model,
            "max_tokens": max_tokens or self.max_tokens,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mime_type,
                                "data": base64_image,
                            },
                        },
                    ],
                }
            ],
        }
        if system_prompt is not None:
            kwargs["system"] = system_prompt

        response = await self.client.messages.create(**kwargs)
        logger.debug("Anthropic vision response: %s", response)
        return _extract_text(response), response

    async def transcribe(
        self,
        audio_path: str,
        *,
        prompt: str | None = None,
        language: str | None = None,
        response_format: str = "text",
    ) -> tuple[str, None]:
        msg = "Anthropic does not provide an audio transcription API."
        raise NotImplementedError(msg)


def _extract_text(response: Message) -> str:
    """Concatenate text blocks from an Anthropic Messages response."""
    parts: list[str] = []
    for block in response.content:
        if getattr(block, "type", None) == "text":
            parts.append(getattr(block, "text", ""))
    return "".join(parts)
