from __future__ import annotations

from typing import Any, cast

from memu.llm.backends.base import LLMBackend


class QwenLLMBackend(LLMBackend):
    """Backend for Alibaba Qwen/DashScope API."""

    name = "qwen"
    # DashScope compatible-mode endpoint (OpenAI-compatible)
    summary_endpoint = "/compatible-mode/v1/chat/completions"

    def build_summary_payload(
        self, *, text: str, system_prompt: str | None, chat_model: str, max_tokens: int | None
    ) -> dict[str, Any]:
        """Build payload for Qwen chat completions (OpenAI-compatible mode)."""
        prompt = system_prompt or "Summarize the text in one short paragraph."
        payload: dict[str, Any] = {
            "model": chat_model,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": text},
            ],
            "temperature": 0.2,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        return payload

    def parse_summary_response(self, data: dict[str, Any]) -> str:
        return cast(str, data["choices"][0]["message"]["content"])

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
        """Build payload for Qwen Vision API (OpenAI-compatible)."""
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

        payload: dict[str, Any] = {
            "model": chat_model,
            "messages": messages,
            "temperature": 0.2,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        return payload


class Qwen3LLMBackend(QwenLLMBackend):
    """Backend for Qwen3 models (alias with Qwen3-specific defaults)."""

    name = "qwen3"

    def build_summary_payload(
        self, *, text: str, system_prompt: str | None, chat_model: str, max_tokens: int | None
    ) -> dict[str, Any]:
        """Build payload for Qwen3 with enable_thinking support."""
        payload = super().build_summary_payload(
            text=text, system_prompt=system_prompt, chat_model=chat_model, max_tokens=max_tokens
        )
        # Qwen3/QwQ supports thinking mode, disable by default for summarization
        # Use DashScope's enable_search parameter format
        payload["enable_thinking"] = False
        return payload

