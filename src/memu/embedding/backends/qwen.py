from __future__ import annotations

from typing import Any, cast

from memu.embedding.backends.base import EmbeddingBackend


class QwenEmbeddingBackend(EmbeddingBackend):
    """Backend for Alibaba Qwen/DashScope embedding API."""

    name = "qwen"
    # DashScope compatible-mode endpoint (OpenAI-compatible)
    embedding_endpoint = "/compatible-mode/v1/embeddings"

    def build_embedding_payload(self, *, inputs: list[str], embed_model: str) -> dict[str, Any]:
        """
        Build payload for Qwen embedding API (OpenAI-compatible mode).

        Qwen supports models like:
        - text-embedding-v3 (1024/2048 dims)
        - text-embedding-v2 (1536 dims)
        - text-embedding-v1 (1536 dims)
        """
        return {
            "model": embed_model,
            "input": inputs,
            "encoding_format": "float",
        }

    def parse_embedding_response(self, data: dict[str, Any]) -> list[list[float]]:
        """Parse Qwen embedding response."""
        return [cast(list[float], d["embedding"]) for d in data["data"]]



