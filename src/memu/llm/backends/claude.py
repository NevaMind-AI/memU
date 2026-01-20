from __future__ import annotations

from typing import Any

from memu.llm.backends.base import LLMBackend


class ClaudeLLMBackend(LLMBackend):
    """Backend for Anthropic Claude LLM API.

    Claude uses a different message format than OpenAI:
    - System prompt is a top-level parameter, not a message
    - Messages use 'content' as a list of content blocks
    - Response format differs from OpenAI
    """

    name = "claude"
    summary_endpoint = "/v1/messages"

    def build_summary_payload(
        self, *, text: str, system_prompt: str | None, chat_model: str, max_tokens: int | None
    ) -> dict[str, Any]:
        """Build payload for Claude messages API."""
        prompt = system_prompt or "Summarize the text in one short paragraph."

        payload: dict[str, Any] = {
            "model": chat_model,
            "messages": [
                {"role": "user", "content": text},
            ],
            "system": prompt,
            "max_tokens": max_tokens or 4096,
        }
        return payload

    def parse_summary_response(self, data: dict[str, Any]) -> str:
        """Parse Claude response format.

        Claude returns:
        {
            "content": [{"type": "text", "text": "..."}],
            "stop_reason": "end_turn",
            ...
        }
        """
        content = data.get("content", [])
        if content and isinstance(content, list):
            # Extract text from content blocks
            text_parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
            return "".join(text_parts)
        return ""

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
        """Build payload for Claude Vision API.

        Claude uses a different image format:
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": "<base64>"
            }
        }
        """
        content: list[dict[str, Any]] = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": mime_type,
                    "data": base64_image,
                },
            },
            {"type": "text", "text": prompt},
        ]

        payload: dict[str, Any] = {
            "model": chat_model,
            "messages": [
                {"role": "user", "content": content},
            ],
            "max_tokens": max_tokens or 4096,
        }

        if system_prompt:
            payload["system"] = system_prompt

        return payload


__all__ = ["ClaudeLLMBackend"]
