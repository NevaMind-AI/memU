from __future__ import annotations

from memu.app.settings import VectorIndexConfig
from memu.database.vector_index.interfaces import VectorIndex


def build_vector_index(config: VectorIndexConfig | None) -> VectorIndex | None:
    """Construct an external VectorIndex instance if configured.

    Returns None for providers that do not require a separate index
    (``bruteforce``, ``pgvector``, ``none``) because those are handled
    inside the metadata backend itself.
    """
    if config is None:
        return None
    provider = config.provider
    if provider == "milvus":
        from memu.database.vector_index.milvus import MilvusVectorIndex

        return MilvusVectorIndex(
            uri=config.uri or "./milvus.db",
            token=config.token,
            collection_name=config.collection_name,
            dim=config.dim,
        )
    return None


__all__ = ["VectorIndex", "build_vector_index"]
