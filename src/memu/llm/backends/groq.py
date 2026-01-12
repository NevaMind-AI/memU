from __future__ import annotations

from typing import Any, cast

from memu.llm.backends.base import LLMBackend


class GroqLLMBackend(LLMBackend):
    """
    Backend for Groq LLM API (OpenAI-compatible).
    
    Groq provides ultra-fast LLM inference using their LPU architecture.
    Supports all Groq models including:
    - Llama 3.3 70B (versatile, speculative decoding)
    - Llama 3.2 90B Vision
    - Mixtral 8x7B
    - Gemma 2 9B
    - And many more...
    
    Note: Groq uses OpenAI-compatible API format.
    API Endpoint: https://api.groq.com/openai/v1
    """

    name = "groq"
    summary_endpoint = "/chat/completions"

    def build_summary_payload(
        self, *, text: str, system_prompt: str | None, chat_model: str, max_tokens: int | None
    ) -> dict[str, Any]:
        """Build payload for Groq chat completions (OpenAI-compatible format)."""
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
        """Parse Groq API response (OpenAI-compatible format)."""
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
        """
        Build payload for Groq Vision API (OpenAI-compatible format).
        
        Supports vision models like:
        - llama-3.2-90b-vision-preview
        - llama-3.2-11b-vision-preview
        """
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
