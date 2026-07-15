"""Shared types for embedding (vectorization) clients.

Embedding clients expose a single capability, :meth:`EmbeddingClient.embed`,
which turns a batch of texts into dense vectors. Each transport (official SDK
or raw HTTP) implements this surface so it can be wrapped or swapped freely.
"""

from __future__ import annotations

from typing import Any


class EmbeddingClient:
    """Base interface for embedding clients."""

    embed_model: str

    async def embed(self, inputs: list[str]) -> tuple[list[list[float]], Any]:
        """Embed ``inputs`` and return ``(vectors, raw_response)``.

        ``raw_response`` carries provider usage metadata (token counts); it may
        be ``None`` for transports that do not expose usage.
        """
        raise NotImplementedError
