from __future__ import annotations

from memu.embedding.backends.openai import OpenAIEmbeddingBackend


class OpenRouterEmbeddingBackend(OpenAIEmbeddingBackend):
    """OpenRouter uses an OpenAI-compatible embedding API."""

    name = "openrouter"
    embedding_endpoint = "/api/v1/embeddings"
