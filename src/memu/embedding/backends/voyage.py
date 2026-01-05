from __future__ import annotations

from typing import Any, cast

from memu.embedding.backends.base import EmbeddingBackend


class VoyageEmbeddingBackend(EmbeddingBackend):
    """Backend for Voyage AI embedding API."""

    name = "voyage"
    embedding_endpoint = "/embeddings"  # base_url should include /v1

    def build_embedding_payload(self, *, inputs: list[str], embed_model: str) -> dict[str, Any]:
        """
        Build payload for Voyage embedding API.

        Voyage supports models like:
        - voyage-3 (best quality)
        - voyage-3-lite (faster)
        - voyage-code-3 (code-optimized)
        - voyage-finance-2 (finance domain)
        - voyage-law-2 (legal domain)
        - voyage-multilingual-2 (multilingual)
        """
        return {
            "model": embed_model,
            "input": inputs,
            "input_type": "document",  # or "query" for search queries
        }

    def parse_embedding_response(self, data: dict[str, Any]) -> list[list[float]]:
        """Parse Voyage embedding response."""
        return [cast(list[float], d["embedding"]) for d in data["data"]]

    def build_query_embedding_payload(self, *, inputs: list[str], embed_model: str) -> dict[str, Any]:
        """Build payload optimized for query embeddings."""
        return {
            "model": embed_model,
            "input": inputs,
            "input_type": "query",
        }

