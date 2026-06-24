from __future__ import annotations

from typing import Any, cast

from memu.embedding.backends.base import EmbeddingBackend


class JinaEmbeddingBackend(EmbeddingBackend):
    """Backend for Jina AI embedding API.

    Jina exposes an OpenAI-compatible ``/embeddings`` surface (bearer auth,
    ``{"model", "input"}`` payload, ``data[].embedding`` response) at
    ``https://api.jina.ai/v1``. See https://jina.ai/embeddings/.
    """

    name = "jina"
    embedding_endpoint = "/embeddings"

    def build_embedding_payload(self, *, inputs: list[str], embed_model: str) -> dict[str, Any]:
        return {"model": embed_model, "input": inputs}

    def parse_embedding_response(self, data: dict[str, Any]) -> list[list[float]]:
        return [cast(list[float], d["embedding"]) for d in data["data"]]
