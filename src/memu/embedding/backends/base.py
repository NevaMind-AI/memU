from __future__ import annotations

from typing import Any


class EmbeddingBackend:
    """Defines how to talk to a specific embedding provider.

    Each provider lives in its own module under :mod:`memu.embedding.backends`
    and customizes the request endpoint, payload shape, response parsing and
    (when needed) the auth headers. Mirrors :class:`memu.llm.backends.base.LLMBackend`.
    """

    name: str = "base"
    embedding_endpoint: str = "/embeddings"

    def default_headers(self, api_key: str) -> dict[str, str]:
        """Auth/request headers for this provider.

        Defaults to OpenAI-style bearer auth; providers with a different scheme
        override this.
        """
        return {"Authorization": f"Bearer {api_key}"}

    def build_embedding_payload(self, *, inputs: list[str], embed_model: str) -> dict[str, Any]:
        raise NotImplementedError

    def parse_embedding_response(self, data: dict[str, Any]) -> list[list[float]]:
        raise NotImplementedError
