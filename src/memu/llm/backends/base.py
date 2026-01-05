from __future__ import annotations

from typing import Any


class LLMBackend:
    """Defines how to talk to a specific HTTP LLM provider."""

    name: str = "base"
    summary_endpoint: str = "/chat/completions"

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

    def get_extra_headers(self) -> dict[str, str]:
        """Return extra headers required by this backend. Override in subclass if needed."""
        return {}

    def uses_query_param_auth(self) -> bool:
        """Return True if this backend uses API key in query parameter instead of header."""
        return False

    def get_endpoint(self, model: str) -> str:
        """Get the actual endpoint, optionally with model name substituted."""
        return self.summary_endpoint
