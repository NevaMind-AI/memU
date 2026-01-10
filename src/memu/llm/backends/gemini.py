from __future__ import annotations

from typing import Any, cast

from memu.llm.backends.base import LLMBackend

_DEFAULT_SUMMARY_PROMPT = "Summarize the text in one short paragraph."


def _extract_text(data: dict[str, Any]) -> str:
    candidates = data.get("candidates")
    if isinstance(candidates, list):
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            content = candidate.get("content")
            if not isinstance(content, dict):
                continue
            parts = content.get("parts")
            if not isinstance(parts, list):
                continue
            texts: list[str] = []
            for part in parts:
                if isinstance(part, dict):
                    text = part.get("text")
                    if isinstance(text, str) and text:
                        texts.append(text)
            if texts:
                return "\n".join(texts)
    fallback = data.get("text")
    return cast(str, fallback) if isinstance(fallback, str) else ""


def _build_generation_config(*, temperature: float | None, max_tokens: int | None) -> dict[str, Any] | None:
    config: dict[str, Any] = {}
    if temperature is not None:
        config["temperature"] = temperature
    if max_tokens is not None:
        config["maxOutputTokens"] = max_tokens
    return config or None


class GeminiLLMBackend(LLMBackend):
    """Backend for Gemini API (Google AI Studio)."""

    name = "gemini"
    summary_endpoint = "/models/{model}:generateContent"

    def build_summary_payload(
        self, *, text: str, system_prompt: str | None, chat_model: str, max_tokens: int | None
    ) -> dict[str, Any]:
        prompt = system_prompt or _DEFAULT_SUMMARY_PROMPT
        combined = f"{prompt}\n\n{text}" if text else prompt
        payload: dict[str, Any] = {
            "contents": [{"parts": [{"text": combined}]}],
        }
        generation_config = _build_generation_config(temperature=0.2, max_tokens=max_tokens)
        if generation_config:
            payload["generationConfig"] = generation_config
        return payload

    def parse_summary_response(self, data: dict[str, Any]) -> str:
        return _extract_text(data)

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
        combined = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        payload: dict[str, Any] = {
            "contents": [
                {
                    "parts": [
                        {"text": combined},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": base64_image,
                            }
                        },
                    ]
                }
            ]
        }
        generation_config = _build_generation_config(temperature=0.2, max_tokens=max_tokens)
        if generation_config:
            payload["generationConfig"] = generation_config
        return payload

