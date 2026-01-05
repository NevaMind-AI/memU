from __future__ import annotations

from typing import Any, cast

from memu.llm.backends.base import LLMBackend


class GeminiLLMBackend(LLMBackend):
    """Backend for Google Gemini API."""

    name = "gemini"
    # Gemini uses model name in the endpoint, this is a placeholder
    summary_endpoint = "/v1beta/models/{model}:generateContent"

    def __init__(self) -> None:
        super().__init__()
        self._current_model: str = ""

    def get_endpoint(self, model: str) -> str:
        """Get the actual endpoint with model name substituted."""
        return f"/v1beta/models/{model}:generateContent"

    def build_summary_payload(
        self, *, text: str, system_prompt: str | None, chat_model: str, max_tokens: int | None
    ) -> dict[str, Any]:
        """Build payload for Gemini generateContent API."""
        self._current_model = chat_model
        prompt = system_prompt or "Summarize the text in one short paragraph."

        payload: dict[str, Any] = {
            "contents": [
                {
                    "parts": [
                        {"text": f"{prompt}\n\n{text}"},
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
            },
        }
        if max_tokens is not None:
            payload["generationConfig"]["maxOutputTokens"] = max_tokens
        return payload

    def parse_summary_response(self, data: dict[str, Any]) -> str:
        # Gemini returns candidates list with content parts
        candidates = data.get("candidates", [])
        if candidates:
            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            if parts:
                return cast(str, parts[0].get("text", ""))
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
        """Build payload for Gemini Vision API."""
        self._current_model = chat_model
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        payload: dict[str, Any] = {
            "contents": [
                {
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": base64_image,
                            }
                        },
                        {"text": full_prompt},
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
            },
        }
        if max_tokens is not None:
            payload["generationConfig"]["maxOutputTokens"] = max_tokens
        return payload

    def uses_query_param_auth(self) -> bool:
        """Gemini uses API key in query parameter instead of header."""
        return True

