from __future__ import annotations

from typing import Any, cast

from memu.embedding.backends.base import EmbeddingBackend


class JinaEmbeddingBackend(EmbeddingBackend):
    """Backend for Jina AI embedding API."""

    name = "jina"
    embedding_endpoint = "/embeddings"  # base_url should include /v1

    def build_embedding_payload(self, *, inputs: list[str], embed_model: str) -> dict[str, Any]:
        """
        Build payload for Jina embedding API.

        Jina supports models like:
        - jina-embeddings-v3 (latest, multilingual)
        - jina-embeddings-v2-base-en (English)
        - jina-embeddings-v2-base-zh (Chinese)
        - jina-embeddings-v2-base-de (German)
        - jina-clip-v1 (multimodal text/image)
        - jina-colbert-v2 (late interaction)

        Note: Jina v3 models don't accept encoding_format parameter.
        """
        return {
            "model": embed_model,
            "input": inputs,
        }

    def parse_embedding_response(self, data: dict[str, Any]) -> list[list[float]]:
        """Parse Jina embedding response."""
        return [cast(list[float], d["embedding"]) for d in data["data"]]

    def build_embedding_payload_with_task(
        self, *, inputs: list[str], embed_model: str, task: str
    ) -> dict[str, Any]:
        """
        Build payload with task specification for jina-embeddings-v3.

        Args:
            inputs: Text inputs to embed
            embed_model: Model name
            task: One of 'retrieval.query', 'retrieval.passage', 'separation',
                  'classification', 'text-matching'
        """
        return {
            "model": embed_model,
            "input": inputs,
            "task": task,
        }

