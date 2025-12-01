from __future__ import annotations

from typing import Any


class EmbeddingBackend:
    """Defines how to talk to a specific embedding provider."""

    name: str = "base"
    embedding_endpoint: str = "/embeddings"

    def build_embedding_payload(self, *, inputs: list[str], embed_model: str) -> dict[str, Any]:
        raise NotImplementedError

    def parse_embedding_response(self, data: dict[str, Any]) -> list[list[float]]:
        raise NotImplementedError
