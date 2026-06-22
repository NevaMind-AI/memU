from __future__ import annotations

from typing import Any


def _extract_content_from_dict(data: dict[str, Any]) -> str:
    """Extract text content from a raw API response dict.

    Falls back to ``reasoning_content`` for reasoning models (e.g. MiniMax-M2.7,
    DeepSeek-R1) that put their output there instead of ``content``.
    """
    msg = data["choices"][0]["message"]
    content = msg.get("content")
    if not content:
        content = msg.get("reasoning_content")
    return content or ""


class LLMBackend:
    """Defines how to talk to a specific HTTP LLM provider."""

    name: str = "base"
    summary_endpoint: str = "/chat/completions"

    def build_summary_payload(
        self, *, text: str, system_prompt: str | None, chat_model: str, max_tokens: int | None
    ) -> dict[str, Any]:
        raise NotImplementedError

    def parse_summary_response(self, data: dict[str, Any]) -> str:
        raise NotImplementedError

    def build_vision_payload(
        self,
        *,
        prompt: str,
        base64_image: str,
        mime_type: str,
        system_prompt: str | None,
        chat_model: str,
        max_tokens: int | None,
    ) -> dict[str, Any]:
        raise NotImplementedError
