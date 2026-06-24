"""Embedding (vectorization) clients.

Sibling package to :mod:`memu.llm` and :mod:`memu.vlm`, scoped to the embedding
capability used by vector search. It mirrors their package layout:

- ``backends/``: per-provider embedding request/response shapes (HTTP transport).
- ``http_client``/``openai_sdk``: transport clients.
- ``gateway``: build a client from a :class:`memu.app.settings.EmbeddingConfig`.
- ``defaults``: per-provider default embedding models / endpoints.
"""

from __future__ import annotations

from memu.embedding.base import EmbeddingClient
from memu.embedding.defaults import (
    EMBEDDING_PROVIDER_DEFAULTS,
    EMBEDDING_PROVIDER_ENDPOINTS,
    default_embedding_model,
)
from memu.embedding.gateway import build_embedding_client
from memu.embedding.http_client import HTTPEmbeddingClient
from memu.embedding.openai_sdk import OpenAIEmbeddingSDKClient

__all__ = [
    "EMBEDDING_PROVIDER_DEFAULTS",
    "EMBEDDING_PROVIDER_ENDPOINTS",
    "EmbeddingClient",
    "HTTPEmbeddingClient",
    "OpenAIEmbeddingSDKClient",
    "build_embedding_client",
    "default_embedding_model",
]
