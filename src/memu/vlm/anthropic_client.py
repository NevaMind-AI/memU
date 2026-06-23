from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from memu.vlm.base import VLMClient, encode_image

if TYPE_CHECKING:
    from anthropic.types import Message

logger = logging.getLogger(__name__)

# Anthropic requires max_tokens on every request; fall back to this when omitted.
_DEFAULT_MAX_TOKENS = 1024


class AnthropicVLMClient(VLMClient):
    """Vision-language client backed by the official Anthropic Python SDK."""

    def __init__(
        self,
        *,
        base_url: str | None,
        api_key: str,
        vlm_model: str,
        max_tokens: int | None = None,
    ):
        from anthropic import AsyncAnthropic

        self.base_url = base_url.rstrip("/") if base_url else None
        self.api_key = api_key or ""
        self.vlm_model = vlm_model
        self.max_tokens = max_tokens or _DEFAULT_MAX_TOKENS
        self.client = AsyncAnthropic(api_key=self.api_key, base_url=self.base_url)

    async def vision(
        self,
        prompt: str,
        image_path: str,
        *,
        max_tokens: int | None = None,
        system_prompt: str | None = None,
    ) -> tuple[str, Message]:
        base64_image, mime_type = encode_image(image_path)

        kwargs: dict[str, Any] = {
            "model": self.vlm_model,
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
        logger.debug("Anthropic VLM vision response: %s", response)
        return _extract_text(response), response


def _extract_text(response: Message) -> str:
    """Concatenate text blocks from an Anthropic Messages response."""
    parts: list[str] = []
    for block in response.content:
        if getattr(block, "type", None) == "text":
            parts.append(getattr(block, "text", ""))
    return "".join(parts)
