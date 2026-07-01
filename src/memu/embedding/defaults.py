"""Per-provider default embedding models and endpoints.

Maps a provider identifier to its latest general-purpose text embedding model,
used by :class:`memu.app.settings.EmbeddingConfig` to pick a sensible default.
Embedding-only providers (Jina, Voyage) also need their own base URL / API key
env, since they are absent from the shared chat ``_PROVIDER_DEFAULTS`` table.
Verified via provider docs, June 2026.
"""

from __future__ import annotations

EMBEDDING_PROVIDER_DEFAULTS: dict[str, str] = {
    "openai": "text-embedding-3-small",
    "jina": "jina-embeddings-v3",
    "voyage": "voyage-3.5",
    "doubao": "doubao-embedding-large-text-250515",
    "openrouter": "openai/text-embedding-3-small",
}

# base_url + API key env for embedding-only providers (not chat providers, so
# they are not in ``memu.app.settings._PROVIDER_DEFAULTS``).
EMBEDDING_PROVIDER_ENDPOINTS: dict[str, tuple[str, str]] = {
    "jina": ("https://api.jina.ai/v1", "JINA_API_KEY"),
    "voyage": ("https://api.voyageai.com/v1", "VOYAGE_API_KEY"),
}


def default_embedding_model(provider: str) -> str | None:
    """Return the default embedding model for ``provider`` (``None`` if unknown)."""
    return EMBEDDING_PROVIDER_DEFAULTS.get(provider.lower())
