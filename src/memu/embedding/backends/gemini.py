"""Gemini Embedding Backend for memU.

Supports Google's Gemini embedding models via the Generative Language API.
"""
from __future__ import annotations

from typing import Any

from memu.embedding.backends.base import EmbeddingBackend


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

    def build_embedding_payload(self, *, inputs: list[str], embed_model: str) -> dict[str, Any]:
        """Build Gemini batchEmbedContents request payload.
        
        Gemini batch format:
        {
            "requests": [
                {"model": "models/{model}", "content": {"parts": [{"text": "..."}]}}
            ]
        }
        """
        requests = [
            {
                "model": f"models/{embed_model}",
                "content": {"parts": [{"text": text}]}
            }
            for text in inputs
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
