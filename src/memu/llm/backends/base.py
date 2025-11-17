from __future__ import annotations

from typing import Any


class HTTPBackend:
    """Defines how to talk to a specific HTTP LLM provider."""

    name: str = "base"
    summary_endpoint: str = "/chat/completions"
    embedding_endpoint: str = "/embeddings"

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

    def build_embedding_payload(self, *, inputs: list[str], embed_model: str) -> dict[str, Any]:
        raise NotImplementedError

    def parse_embedding_response(self, data: dict[str, Any]) -> list[list[float]]:
        raise NotImplementedError
