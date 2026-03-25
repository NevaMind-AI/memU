from __future__ import annotations

from typing import Any

from memu.llm.backends.base import LLMBackend, _extract_content_from_dict


class OpenAILLMBackend(LLMBackend):
    """Backend for OpenAI-compatible LLM API."""

    name = "openai"
    summary_endpoint = "/chat/completions"

    def build_summary_payload(
        self, *, text: str, system_prompt: str | None, chat_model: str, max_tokens: int | None
    ) -> dict[str, Any]:
        prompt = system_prompt or "Summarize the text in one short paragraph."
        return {
            "model": chat_model,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": text},
            ],
            "temperature": 0.2,
            "max_tokens": max_tokens,
        }

    def parse_summary_response(self, data: dict[str, Any]) -> str:
        return _extract_content_from_dict(data)

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
        """Build payload for OpenAI Vision API."""
        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime_type};base64,{base64_image}",
                    },
                },
            ],
        })

        return {
            "model": chat_model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": max_tokens,
        }
