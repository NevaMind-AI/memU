"""Gemini Embedding Backend for memU.

Supports Google's Gemini embedding models via the Generative Language API.
Supports multimodal inputs (text, images, or text+image combinations).
"""
from __future__ import annotations

import base64
from typing import Any

from memu.embedding.backends.base import EmbeddingBackend


def _build_parts(input_item: str | dict) -> list[dict[str, Any]]:
    """Convert a single input item into Gemini content parts.

    Args:
        input_item: Either a plain string or a dict with optional keys:
            - "text": str
            - "image": bytes (raw) or str (already base64-encoded)
            - "mime_type": str (default "image/png")

    Returns:
        A list of part dicts suitable for Gemini's ``content.parts``.
    """
    if isinstance(input_item, str):
        return [{"text": input_item}]

    parts: list[dict[str, Any]] = []

    if "text" in input_item:
        parts.append({"text": input_item["text"]})

    if "image" in input_item:
        image = input_item["image"]
        mime_type = input_item.get("mime_type", "image/png")
        b64 = base64.b64encode(image).decode() if isinstance(image, bytes) else image
        parts.append({"inline_data": {"mime_type": mime_type, "data": b64}})

    return parts


class GeminiEmbeddingBackend(EmbeddingBackend):
    """Backend for Google Gemini embedding API.

    Gemini API uses a different endpoint structure:
    - Endpoint: /v1beta/models/{model}:batchEmbedContents
    - Auth: x-goog-api-key header or ?key= query param

    Note: The embedding_endpoint will be dynamically constructed
    with the model name in HTTPEmbeddingClient.
    """

    name = "gemini"
    # This will be formatted with model name later
    embedding_endpoint = "/v1beta/models/{model}:batchEmbedContents"

    def build_embedding_payload(self, *, inputs: list[str | dict], embed_model: str) -> dict[str, Any]:
        """Build Gemini batchEmbedContents request payload.

        Gemini batch format:
        {
            "requests": [
                {"model": "models/{model}", "content": {"parts": [...]}}
            ]
        }

        Each input can be a plain string or a dict with text/image fields.
        """
        requests = [
            {
                "model": f"models/{embed_model}",
                "content": {"parts": _build_parts(item)},
            }
            for item in inputs
        ]
        return {"requests": requests}

    def parse_embedding_response(self, data: dict[str, Any]) -> list[list[float]]:
        """Parse Gemini batchEmbedContents response.
        
        Response format:
        {
            "embeddings": [
                {"values": [0.1, 0.2, ...]}
            ]
        }
        """
        embeddings = data.get("embeddings", [])
        return [emb["values"] for emb in embeddings]
