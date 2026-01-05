from __future__ import annotations

from typing import Any, cast

from memu.llm.backends.base import LLMBackend


class ClaudeLLMBackend(LLMBackend):
    """Backend for Anthropic Claude API."""

    name = "claude"
    summary_endpoint = "/v1/messages"

    def build_summary_payload(
        self, *, text: str, system_prompt: str | None, chat_model: str, max_tokens: int | None
    ) -> dict[str, Any]:
        """Build payload for Anthropic Claude messages API."""
        prompt = system_prompt or "Summarize the text in one short paragraph."
        payload: dict[str, Any] = {
            "model": chat_model,
            "system": prompt,
            "messages": [
                {"role": "user", "content": text},
            ],
            "max_tokens": max_tokens or 4096,
        }
        return payload

    def parse_summary_response(self, data: dict[str, Any]) -> str:
        # Claude API returns content as a list of content blocks
        content_blocks = data.get("content", [])
        if content_blocks:
            # Get text from the first text block
            for block in content_blocks:
                if block.get("type") == "text":
                    return cast(str, block.get("text", ""))
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
        """Build payload for Claude Vision API."""
        payload: dict[str, Any] = {
            "model": chat_model,
            "max_tokens": max_tokens or 4096,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mime_type,
                                "data": base64_image,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt,
                        },
                    ],
                }
            ],
        }
        if system_prompt:
            payload["system"] = system_prompt
        return payload

    def get_extra_headers(self) -> dict[str, str]:
        """Return extra headers required by Claude API."""
        return {
            "anthropic-version": "2023-06-01",
        }

