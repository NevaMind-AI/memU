from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping
from threading import Lock
from typing import Any

from memu.database.vector_index.interfaces import VectorIndex

logger = logging.getLogger(__name__)

_ID_FIELD = "id"
_VECTOR_FIELD = "vector"
_DEFAULT_ID_MAX_LENGTH = 128


def _format_scalar(value: Any) -> str | None:
    """Render a Python value as a Milvus boolean-expression literal.

    Returns ``None`` when the value cannot be used in a scalar filter
    (e.g. nested dicts), in which case the calling search will fall back
    to unfiltered retrieval for that key.
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return None


def _build_filter_expr(where: Mapping[str, Any] | None) -> str:
    if not where:
        return ""
    parts: list[str] = []
    for key, value in where.items():
        literal = _format_scalar(value)
        if literal is None:
            logger.debug("Skipping unsupported filter key %s=%r for Milvus", key, value)
            continue
        parts.append(f"{key} == {literal}")
    return " and ".join(parts)


class MilvusVectorIndex(VectorIndex):
    """Milvus implementation of the VectorIndex protocol.

    Uses ``MilvusClient`` for all operations. The collection is created on
    first ``upsert`` once the embedding dimension is known (unless ``dim``
    is provided explicitly). Scope fields supplied via ``scope`` are stored
    as dynamic fields so they can be used as filter expressions at search
    time.

    The default ``uri="./milvus.db"`` runs Milvus Lite with zero external
    dependencies; point ``uri`` at a Milvus server or Zilliz Cloud endpoint
    for larger deployments.
    """

    def __init__(
        self,
        *,
        uri: str = "./milvus.db",
        token: str | None = None,
        collection_name: str = "memu_memory_items",
        dim: int | None = None,
    ) -> None:
        try:
            from pymilvus import MilvusClient
        except ImportError as e:
            msg = (
                "pymilvus is required for the Milvus vector index. "
                "Install it with: uv add pymilvus  (or: pip install pymilvus)"
            )
            raise ImportError(msg) from e

        self._uri = uri
        self._token = token
        self._collection_name = collection_name
        self._dim = dim
        self._client = MilvusClient(uri=uri, token=token) if token else MilvusClient(uri=uri)
        self._lock = Lock()
        self._ready = False

        if dim is not None:
            self._ensure_collection(dim)

    def _ensure_collection(self, dim: int) -> None:
        with self._lock:
            if self._ready:
                return
            if self._client.has_collection(collection_name=self._collection_name):
                self._ready = True
                self._dim = dim
                return

            from pymilvus import DataType

            schema = self._client.create_schema(
                auto_id=False,
                enable_dynamic_field=True,
            )
            schema.add_field(
                field_name=_ID_FIELD,
                datatype=DataType.VARCHAR,
                is_primary=True,
                max_length=_DEFAULT_ID_MAX_LENGTH,
            )
            schema.add_field(
                field_name=_VECTOR_FIELD,
                datatype=DataType.FLOAT_VECTOR,
                dim=dim,
            )

            index_params = self._client.prepare_index_params()
            index_params.add_index(
                field_name=_VECTOR_FIELD,
                index_type="AUTOINDEX",
                metric_type="COSINE",
            )

            self._client.create_collection(
                collection_name=self._collection_name,
                schema=schema,
                index_params=index_params,
            )
            self._dim = dim
            self._ready = True

    def upsert(
        self,
        item_id: str,
        vector: list[float],
        scope: Mapping[str, Any] | None = None,
    ) -> None:
        if not vector:
            logger.debug("Skipping Milvus upsert for %s: empty vector", item_id)
            return
        self._ensure_collection(len(vector))

        data: dict[str, Any] = {_ID_FIELD: item_id, _VECTOR_FIELD: list(vector)}
        if scope:
            for key, value in scope.items():
                if key in (_ID_FIELD, _VECTOR_FIELD):
                    continue
                # Only persist scalar scope values; complex types are ignored
                # since they cannot be used in Milvus filter expressions.
                if isinstance(value, (str, int, float, bool)) or value is None:
                    data[key] = value

        self._client.upsert(collection_name=self._collection_name, data=[data])

    def delete(self, item_id: str) -> None:
        if not self._ready:
            return
        self._client.delete(
            collection_name=self._collection_name,
            filter=f'{_ID_FIELD} == "{item_id}"',
        )

    def delete_many(self, item_ids: Iterable[str]) -> None:
        ids = list(item_ids)
        if not ids or not self._ready:
            return
        quoted = ", ".join(f'"{i}"' for i in ids)
        self._client.delete(
            collection_name=self._collection_name,
            filter=f"{_ID_FIELD} in [{quoted}]",
        )

    def search(
        self,
        query_vec: list[float],
        top_k: int,
        where: Mapping[str, Any] | None = None,
    ) -> list[tuple[str, float]]:
        if not self._ready or top_k <= 0 or not query_vec:
            return []

        expr = _build_filter_expr(where)
        results = self._client.search(
            collection_name=self._collection_name,
            data=[list(query_vec)],
            limit=top_k,
            filter=expr or None,
            output_fields=[_ID_FIELD],
            search_params={"metric_type": "COSINE"},
        )
        if not results:
            return []

        hits = results[0]
        scored: list[tuple[str, float]] = []
        for hit in hits:
            # MilvusClient returns hits as dicts with ``id`` and ``distance`` keys.
            # For COSINE, distance is cosine similarity (higher = better).
            hit_id = hit.get("id") if isinstance(hit, dict) else getattr(hit, "id", None)
            raw_score = hit.get("distance") if isinstance(hit, dict) else getattr(hit, "distance", 0.0)
            if hit_id is None:
                continue
            scored.append((str(hit_id), float(raw_score if raw_score is not None else 0.0)))
        return scored

    def close(self) -> None:
        with self._lock:
            close = getattr(self._client, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:
                    logger.debug("MilvusClient.close raised; ignoring", exc_info=True)
            self._ready = False


__all__ = ["MilvusVectorIndex"]
