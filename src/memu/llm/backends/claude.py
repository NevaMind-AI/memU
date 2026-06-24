from __future__ import annotations

from typing import Any, cast

from memu.llm.backends.base import LLMBackend

# Anthropic requires max_tokens; fall back to this when the caller omits it.
_DEFAULT_MAX_TOKENS = 1024
_ANTHROPIC_VERSION = "2023-06-01"


class ClaudeLLMBackend(LLMBackend):
    """Backend for Anthropic Claude (native Messages API).

    Unlike the OpenAI-compatible providers, Claude uses ``x-api-key`` auth, a
    top-level ``system`` field, a required ``max_tokens``, and a different
    response/vision shape.

    Default base_url: ``https://api.anthropic.com`` with model
    ``claude-haiku-4-5``.
    """

    name = "claude"
    summary_endpoint = "/v1/messages"

    def default_headers(self, api_key: str) -> dict[str, str]:
        return {
            "x-api-key": api_key,
            "anthropic-version": _ANTHROPIC_VERSION,
            "content-type": "application/json",
        }

    def build_summary_payload(
        self, *, text: str, system_prompt: str | None, chat_model: str, max_tokens: int | None
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": chat_model,
            "max_tokens": max_tokens or _DEFAULT_MAX_TOKENS,
            "messages": [{"role": "user", "content": text}],
        }
        if system_prompt:
            payload["system"] = system_prompt
        return payload

    def parse_summary_response(self, data: dict[str, Any]) -> str:
        blocks = data.get("content") or []
        for block in blocks:
            if isinstance(block, dict) and block.get("type") == "text":
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
        payload: dict[str, Any] = {
            "model": chat_model,
            "max_tokens": max_tokens or _DEFAULT_MAX_TOKENS,
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
        if system_prompt:
            payload["system"] = system_prompt
        return payload
