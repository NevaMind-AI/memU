from __future__ import annotations

import logging
import math
import re
from collections.abc import Iterable, Mapping
from threading import Lock
from typing import Any

from memu.database.vector_index.interfaces import VectorIndex

logger = logging.getLogger(__name__)

_ID_FIELD = "id"
_VECTOR_FIELD = "vector"
_DEFAULT_ID_MAX_LENGTH = 128
_FIELD_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_AUTO_ID_ERROR = "primary keys must use auto_id=False"
_DYNAMIC_FIELD_ERROR = "dynamic fields must be enabled"
_MISSING_ID_ERROR = f"missing primary-key field {_ID_FIELD!r}"
_ID_SCHEMA_ERROR = f"field {_ID_FIELD!r} must be the VARCHAR primary key"
_MISSING_VECTOR_ERROR = f"missing vector field {_VECTOR_FIELD!r}"
_VECTOR_TYPE_ERROR = f"field {_VECTOR_FIELD!r} must be FLOAT_VECTOR"
_VECTOR_DIM_ERROR = f"field {_VECTOR_FIELD!r} has no valid dimension"
_MISSING_INDEX_ERROR = f"field {_VECTOR_FIELD!r} has no index"
_INDEX_METRIC_ERROR = f"field {_VECTOR_FIELD!r} must use a COSINE index"


class MilvusCollectionCompatibilityError(ValueError):
    def __init__(self, collection_name: str, reason: str) -> None:
        self.collection_name = collection_name
        self.reason = reason
        super().__init__(f"Milvus collection {collection_name!r} is incompatible: {reason}")


def _valid_field_name(field_name: str) -> bool:
    return bool(_FIELD_NAME_RE.fullmatch(field_name))


def _format_scalar(value: Any) -> str | None:
    """Render a Python value as a Milvus boolean-expression literal.

    Returns ``None`` when the value cannot be safely represented in a
    Milvus boolean expression.
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            return None
        return str(value)
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return None


def _format_in_filter(raw_key: str, value: Any) -> str | None:
    if isinstance(value, str):
        return _format_scalar(value)
    literals: list[str] = []
    try:
        for item in value:
            literal = _format_scalar(item)
            if literal is None:
                logger.warning("Rejecting unsupported Milvus filter value for %s=%r", raw_key, value)
                return None
            literals.append(literal)
    except TypeError:
        logger.warning("Rejecting unsupported Milvus filter value for %s=%r", raw_key, value)
        return None
    if not literals:
        logger.warning("Rejecting unsupported Milvus filter value for %s=%r", raw_key, value)
        return None
    return f"[{', '.join(literals)}]"


def _build_filter_expr(where: Mapping[str, Any] | None) -> str | None:
    if not where:
        return ""
    parts: list[str] = []
    for raw_key, value in where.items():
        if value is None:
            continue
        field_name, sep, parsed_op = raw_key.partition("__")
        op: str | None = parsed_op if sep else None
        if not _valid_field_name(field_name):
            logger.warning("Rejecting unsafe Milvus filter field %r", field_name)
            return None
        if op == "in":
            literal = _format_in_filter(raw_key, value)
            if literal is None:
                return None
            operator = "==" if isinstance(value, str) else "in"
            parts.append(f"{field_name} {operator} {literal}")
            continue
        literal = _format_scalar(value)
        if literal is None:
            logger.warning("Rejecting unsupported Milvus filter value for %s=%r", raw_key, value)
            return None
        parts.append(f"{field_name} == {literal}")
    return " and ".join(parts)


def _coerce_score(score: Any) -> float:
    if score is None:
        return 0.0
    try:
        value = float(score)
    except (TypeError, ValueError):
        return 0.0
    return value if math.isfinite(value) else 0.0


def _value(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(key, default)
    return getattr(obj, key, default)


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
        db_name: str | None = None,
        collection_name: str = "memu_memory_items",
        dim: int | None = None,
        consistency_level: str | None = None,
    ) -> None:
        try:
            from pymilvus import MilvusClient
        except ImportError as e:
            msg = "pymilvus is required for the Milvus vector index. Install it with: uv sync --extra milvus"
            raise ImportError(msg) from e

        self._uri = uri
        self._token = token
        self._db_name = db_name
        self._collection_name = collection_name
        self._dim = dim
        self._consistency_level = consistency_level
        client_kwargs: dict[str, Any] = {"uri": uri}
        if token:
            client_kwargs["token"] = token
        if db_name:
            client_kwargs["db_name"] = db_name
        self._client = MilvusClient(**client_kwargs)
        self._lock = Lock()
        self._ready = False

        if dim is not None:
            self._ensure_collection(dim)

    def _validate_dimension(self, dim: int) -> None:
        if dim <= 0:
            msg = f"Milvus vector dimension must be positive, got {dim}"
            raise ValueError(msg)
        if self._dim is not None and dim != self._dim:
            msg = f"Milvus vector dimension mismatch: expected {self._dim}, got {dim}"
            raise ValueError(msg)

    def _incompatible_collection(self, reason: str) -> MilvusCollectionCompatibilityError:
        return MilvusCollectionCompatibilityError(self._collection_name, reason)

    def _validate_existing_schema(self, description: Any, dim: int) -> None:
        from pymilvus import DataType

        if _value(description, "auto_id") is not False:
            raise self._incompatible_collection(_AUTO_ID_ERROR)
        if _value(description, "enable_dynamic_field") is not True:
            raise self._incompatible_collection(_DYNAMIC_FIELD_ERROR)

        fields = _value(description, "fields", [])
        by_name = {_value(field, "name"): field for field in fields}
        id_field = by_name.get(_ID_FIELD)
        if id_field is None:
            raise self._incompatible_collection(_MISSING_ID_ERROR)
        if _value(id_field, "type") != DataType.VARCHAR or _value(id_field, "is_primary") is not True:
            raise self._incompatible_collection(_ID_SCHEMA_ERROR)

        vector_field = by_name.get(_VECTOR_FIELD)
        if vector_field is None:
            raise self._incompatible_collection(_MISSING_VECTOR_ERROR)
        if _value(vector_field, "type") != DataType.FLOAT_VECTOR:
            raise self._incompatible_collection(_VECTOR_TYPE_ERROR)
        params = _value(vector_field, "params", {})
        raw_dim = _value(params, "dim", _value(vector_field, "dim"))
        try:
            existing_dim = int(raw_dim)
        except (TypeError, ValueError) as exc:
            raise self._incompatible_collection(_VECTOR_DIM_ERROR) from exc
        if existing_dim != dim:
            reason = f"field {_VECTOR_FIELD!r} has dimension {existing_dim}, expected {dim}"
            raise self._incompatible_collection(reason)

    def _validate_existing_indexes(self) -> None:
        try:
            index_names = self._client.list_indexes(collection_name=self._collection_name)
            indexes = [
                self._client.describe_index(collection_name=self._collection_name, index_name=index_name)
                for index_name in index_names
            ]
        except Exception as exc:
            msg = f"Could not inspect indexes for Milvus collection {self._collection_name!r}"
            raise RuntimeError(msg) from exc
        vector_indexes = [index for index in indexes if _value(index, "field_name") == _VECTOR_FIELD]
        if not vector_indexes:
            raise self._incompatible_collection(_MISSING_INDEX_ERROR)
        if not any(str(_value(index, "metric_type", "")).upper() == "COSINE" for index in vector_indexes):
            raise self._incompatible_collection(_INDEX_METRIC_ERROR)

    def _validate_existing_collection(self, dim: int) -> None:
        try:
            description = self._client.describe_collection(collection_name=self._collection_name)
        except Exception as exc:
            msg = f"Could not inspect Milvus collection {self._collection_name!r}"
            raise RuntimeError(msg) from exc
        self._validate_existing_schema(description, dim)
        self._validate_existing_indexes()

    def _ensure_collection(self, dim: int) -> None:
        self._validate_dimension(dim)
        with self._lock:
            self._validate_dimension(dim)
            if self._ready:
                return
            if self._client.has_collection(collection_name=self._collection_name):
                self._validate_existing_collection(dim)
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

            create_kwargs: dict[str, Any] = {
                "collection_name": self._collection_name,
                "schema": schema,
                "index_params": index_params,
            }
            if self._consistency_level:
                create_kwargs["consistency_level"] = self._consistency_level
            self._client.create_collection(**create_kwargs)
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
                if key in (_ID_FIELD, _VECTOR_FIELD) or not _valid_field_name(key):
                    continue
                # Only persist scalar scope values; complex types are ignored
                # since they cannot be used in Milvus filter expressions.
                if _format_scalar(value) is not None:
                    data[key] = value

        self._client.upsert(collection_name=self._collection_name, data=[data])

    def delete(self, item_id: str) -> None:
        if not self._ready:
            return
        item_literal = _format_scalar(item_id)
        if item_literal is None:
            return
        self._client.delete(
            collection_name=self._collection_name,
            filter=f"{_ID_FIELD} == {item_literal}",
        )

    def delete_many(self, item_ids: Iterable[str]) -> None:
        ids = list(item_ids)
        if not ids or not self._ready:
            return
        quoted = ", ".join(literal for item_id in ids if (literal := _format_scalar(item_id)) is not None)
        if not quoted:
            return
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
        self._validate_dimension(len(query_vec))

        expr = _build_filter_expr(where)
        if expr is None:
            return []
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
            if isinstance(hit, dict):
                entity = hit.get("entity") or {}
                hit_id = hit.get("id") or (entity.get(_ID_FIELD) if isinstance(entity, dict) else None)
            else:
                hit_id = getattr(hit, "id", None)
            raw_score = hit.get("distance") if isinstance(hit, dict) else getattr(hit, "distance", 0.0)
            if hit_id is None:
                continue
            scored.append((str(hit_id), _coerce_score(raw_score)))
        return scored

    def close(self) -> None:
        with self._lock:
            close = getattr(self._client, "close", None)
            if callable(close):
                close()
            self._ready = False


__all__ = ["MilvusVectorIndex"]
