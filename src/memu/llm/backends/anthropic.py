"""Anthropic LLM Backend for memU.

Supports Claude models via Anthropic Messages API.
"""
from __future__ import annotations

from typing import Any, cast

from memu.llm.backends.base import LLMBackend


class AnthropicLLMBackend(LLMBackend):
    """Backend for Anthropic Claude API.
    
    Anthropic API differences from OpenAI:
    - Endpoint: /v1/messages
    - Auth: x-api-key header (not Bearer token)
    - System prompt is a separate field, not a message
    - Response format: content[0].text instead of choices[0].message.content
    """

    name = "anthropic"
    summary_endpoint = "/v1/messages"

    def build_summary_payload(
        self, *, text: str, system_prompt: str | None, chat_model: str, max_tokens: int | None
    ) -> dict[str, Any]:
        """Build Anthropic Messages API request payload."""
        payload: dict[str, Any] = {
            "model": chat_model,
            "messages": [
                {"role": "user", "content": text},
            ],
            "temperature": 0.2,
            "max_tokens": max_tokens or 1024,
        }
        
        # Anthropic uses separate system field
        if system_prompt:
            payload["system"] = system_prompt
        else:
            payload["system"] = "Summarize the text in one short paragraph."
        
        return payload

    def parse_summary_response(self, data: dict[str, Any]) -> str:
        """Parse Anthropic Messages API response.
        
        Response format:
        {
            "content": [
                {"type": "text", "text": "..."}
            ]
        }
        """
        content = data.get("content", [])
        if content and len(content) > 0:
            return cast(str, content[0].get("text", ""))
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
        """Build payload for Anthropic Vision API.
        
        Anthropic vision format uses source.type = "base64"
        """
        payload: dict[str, Any] = {
            "model": chat_model,
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
            "temperature": 0.2,
            "max_tokens": max_tokens or 1024,
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        return payload
