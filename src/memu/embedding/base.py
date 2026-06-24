"""Shared types for embedding (vectorization) clients.

Embedding clients expose a single capability, :meth:`EmbeddingClient.embed`,
which turns a batch of texts into dense vectors. Each transport (official SDK,
raw HTTP, or framework backend) implements this surface so it can be
wrapped/swapped like the text :mod:`memu.llm` and vision :mod:`memu.vlm` clients.
"""

from __future__ import annotations

from typing import Any


class EmbeddingClient:
    """Base interface for embedding clients."""

    embed_model: str

    async def embed(self, inputs: list[str]) -> tuple[list[list[float]], Any]:
        """Embed ``inputs`` and return ``(vectors, raw_response)``.

        ``raw_response`` carries provider usage metadata (token counts) so the
        :class:`memu.llm.wrapper.LLMClientWrapper` can record consumption; it may
        be ``None`` for transports that do not expose usage.
        """
        raise NotImplementedError
