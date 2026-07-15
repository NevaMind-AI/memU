"""Per-provider default embedding models and endpoints.

The single source of provider knowledge for the embedding capability: every
provider listed here has a real backend under :mod:`memu.embedding.backends`.
:class:`memu.app.settings.EmbeddingConfig` consults these tables to fill in
sensible defaults. Verified via provider docs, June 2026.
"""

from __future__ import annotations

EMBEDDING_PROVIDER_DEFAULTS: dict[str, str] = {
    "openai": "text-embedding-3-small",
    "jina": "jina-embeddings-v3",
    "voyage": "voyage-3.5",
    "doubao": "doubao-embedding-large-text-250515",
    "openrouter": "openai/text-embedding-3-small",
}

# base_url + API key env per provider. OpenAI is absent because its endpoint is
# the field default on ``EmbeddingConfig`` itself.
EMBEDDING_PROVIDER_ENDPOINTS: dict[str, tuple[str, str]] = {
    "jina": ("https://api.jina.ai/v1", "JINA_API_KEY"),
    "voyage": ("https://api.voyageai.com/v1", "VOYAGE_API_KEY"),
    "doubao": ("https://ark.cn-beijing.volces.com", "ARK_API_KEY"),
    "openrouter": ("https://openrouter.ai", "OPENROUTER_API_KEY"),
}


def default_embedding_model(provider: str) -> str | None:
    """Return the default embedding model for ``provider`` (``None`` if unknown)."""
    return EMBEDDING_PROVIDER_DEFAULTS.get(provider.lower())
