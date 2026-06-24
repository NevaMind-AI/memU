from __future__ import annotations

from typing import Any


class LLMBackend:
    """Defines how to talk to a specific HTTP LLM provider.

    Each provider lives in its own module under :mod:`memu.llm.backends` and
    customizes the request endpoint, payload shape, response parsing and (when
    needed) the auth headers.
    """

    name: str = "base"
    summary_endpoint: str = "/chat/completions"

    def default_headers(self, api_key: str) -> dict[str, str]:
        """Auth/request headers for this provider.

        Defaults to OpenAI-style bearer auth; providers with a different scheme
        (e.g. Anthropic's ``x-api-key``) override this.
        """
        return {"Authorization": f"Bearer {api_key}"}

    def build_summary_payload(
        self, *, text: str, system_prompt: str | None, chat_model: str, max_tokens: int | None
    ) -> dict[str, Any]:
        raise NotImplementedError

    def parse_summary_response(self, data: dict[str, Any]) -> str:
        raise NotImplementedError

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
        raise NotImplementedError
