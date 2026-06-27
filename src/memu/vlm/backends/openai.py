from __future__ import annotations

from typing import Any, cast

from memu.vlm.backends.base import VLMBackend


class OpenAIVLMBackend(VLMBackend):
    """Backend for OpenAI-compatible vision (chat completions with image parts)."""

    name = "openai"
    vision_endpoint = "/chat/completions"

    def build_vision_payload(
        self,
        *,
        prompt: str,
        base64_image: str,
        mime_type: str,
        system_prompt: str | None,
        vlm_model: str,
        max_tokens: int | None,
    ) -> dict[str, Any]:
        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{base64_image}"},
                },
            ],
        })

        payload: dict[str, Any] = {
            "model": vlm_model,
            "messages": messages,
            "temperature": 0.2,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        return payload

    def parse_vision_response(self, data: dict[str, Any]) -> str:
        return cast(str, data["choices"][0]["message"]["content"])

    def build_video_payload(
        self,
        *,
        prompt: str,
        video_data_uri: str,
        system_prompt: str | None,
        vlm_model: str,
        max_tokens: int | None,
    ) -> dict[str, Any]:
        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "video_url", "video_url": {"url": video_data_uri}},
            ],
        })

        payload: dict[str, Any] = {
            "model": vlm_model,
            "messages": messages,
            "temperature": 0.2,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        return payload
