from __future__ import annotations

from typing import Any

from memu.embedding.backends.base import EmbeddingBackend


def _normalize_model_name(model: str) -> str:
    normalized = model.strip()
    if normalized.startswith("models/"):
        return normalized
    return f"models/{normalized}"


class GeminiEmbeddingBackend(EmbeddingBackend):
    """Backend for Gemini embedding API (Google AI Studio)."""

    name = "gemini"
    embedding_endpoint = "/models/{model}:batchEmbedContents"

    def build_embedding_payload(self, *, inputs: list[str], embed_model: str) -> dict[str, Any]:
        model_name = _normalize_model_name(embed_model)
        requests: list[dict[str, Any]] = []
        for text in inputs:
            requests.append({"model": model_name, "content": {"parts": [{"text": text}]}})
        return {"requests": requests}

    def parse_embedding_response(self, data: dict[str, Any]) -> list[list[float]]:
        embeddings: list[list[float]] = []
        items = data.get("embeddings")
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                values = item.get("values")
                if isinstance(values, list):
                    embeddings.append([float(v) for v in values])
        if embeddings:
            return embeddings
        single = data.get("embedding")
        if isinstance(single, dict):
            values = single.get("values")
            if isinstance(values, list):
                return [[float(v) for v in values]]
        return []
