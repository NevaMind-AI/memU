from __future__ import annotations

from typing import Any, cast

from memu.llm.backends.base import LLMBackend


class GeminiLLMBackend(LLMBackend):
    """Backend for Google Gemini LLM API.

    Gemini uses a different API format than OpenAI-compatible APIs:
    - Endpoint: /models/{model}:generateContent
    - Auth: x-goog-api-key header
    - Content format: contents[].parts[].text
    """

    name = "gemini"
    summary_endpoint = "/models/{model}:generateContent"

    def build_summary_payload(
        self, *, text: str, system_prompt: str | None, chat_model: str, max_tokens: int | None
    ) -> dict[str, Any]:
        """Build payload for Gemini generateContent API."""
        contents: list[dict[str, Any]] = []

        # Add user message
        contents.append({"role": "user", "parts": [{"text": text}]})

        payload: dict[str, Any] = {
            "contents": contents,
        }

        # Add system instruction if provided
        # Note: When system_prompt is None, we don't set a default to allow the user prompt
        # to fully control the output format (e.g., for JSON responses)
        if system_prompt:
            payload["system_instruction"] = {"parts": [{"text": system_prompt}]}

        # Add generation config
        generation_config: dict[str, Any] = {
            "temperature": 1.0,  # Gemini recommends keeping at 1.0
        }
        if max_tokens is not None:
            generation_config["maxOutputTokens"] = max_tokens
        payload["generationConfig"] = generation_config

        return payload

    def parse_summary_response(self, data: dict[str, Any]) -> str:
        """Parse Gemini generateContent response."""
        try:
            return cast(str, data["candidates"][0]["content"]["parts"][0]["text"])
        except (KeyError, IndexError) as e:
            msg = f"Failed to parse Gemini response: {e}"
            raise ValueError(msg) from e

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
        """Build payload for Gemini Vision API with inline image data."""
        # Build user content with text and image parts
        user_parts: list[dict[str, Any]] = [
            {"text": prompt},
            {
                "inline_data": {
                    "mime_type": mime_type,
                    "data": base64_image,
                }
            },
        ]

        contents: list[dict[str, Any]] = [
            {
                "role": "user",
                "parts": user_parts,
            }
        ]

        payload: dict[str, Any] = {
            "contents": contents,
        }

        # Add system instruction if provided
        if system_prompt:
            payload["system_instruction"] = {"parts": [{"text": system_prompt}]}

        # Add generation config
        generation_config: dict[str, Any] = {
            "temperature": 1.0,
        }
        if max_tokens is not None:
            generation_config["maxOutputTokens"] = max_tokens
        payload["generationConfig"] = generation_config

        return payload
