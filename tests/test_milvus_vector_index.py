from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

from memu.app import MemoryService
from memu.app.settings import DatabaseConfig
from memu.database.factory import build_database
from memu.database.inmemory.repo import InMemoryStore
from memu.database.vector_index.milvus import (
    MilvusVectorIndex,
    _build_filter_expr,
    _format_scalar,
)


class _UserScope(BaseModel):
    user_id: str = ""
    agent_id: str = ""


class _EmbeddingUnavailable(RuntimeError):
    def __init__(self) -> None:
        super().__init__("embedding unavailable")


class _VectorOperationFailed(RuntimeError):
    def __init__(self, operation: str) -> None:
        super().__init__(f"{operation} failed")


class _FakeEmbeddingClient:
    embed_model = "fake"

    async def embed(self, inputs: list[str]) -> tuple[list[list[float]], dict[str, Any]]:
        vectors: list[list[float]] = []
        for text in inputs:
            lowered = text.lower()
            vectors.append([
                1.0 if "alpha" in lowered or "coffee" in lowered else 0.0,
                1.0 if "beta" in lowered or "deploy" in lowered else 0.0,
                1.0 if "gamma" in lowered else 0.0,
            ])
        return vectors, {}


class _FailingEmbeddingClient:
    embed_model = "failing"

    async def embed(self, inputs: list[str]) -> tuple[list[list[float]], dict[str, Any]]:
        raise _EmbeddingUnavailable


class _RecordingVectorIndex:
    def __init__(self) -> None:
        self.rows: dict[str, tuple[list[float], dict[str, Any]]] = {}
        self.fail_on: str | None = None
        self.search_where: list[dict[str, Any]] = []
        self.closed = False

    def _raise_if_requested(self, operation: str) -> None:
        if self.fail_on == operation:
            raise _VectorOperationFailed(operation)

    def upsert(
        self,
        item_id: str,
        vector: list[float],
        scope: Mapping[str, Any] | None = None,
    ) -> None:
        self._raise_if_requested("upsert")
        self.rows[item_id] = (list(vector), dict(scope or {}))

    def delete(self, item_id: str) -> None:
        self._raise_if_requested("delete")
        self.rows.pop(item_id, None)

    def delete_many(self, item_ids: Iterable[str]) -> None:
        self._raise_if_requested("delete_many")
        for item_id in item_ids:
            self.rows.pop(item_id, None)

    def search(
        self,
        query_vec: list[float],
        top_k: int,
        where: Mapping[str, Any] | None = None,
    ) -> list[tuple[str, float]]:
        self.search_where.append(dict(where or {}))
        return [(item_id, 1.0) for item_id in list(self.rows)[:top_k]]

    def close(self) -> None:
        self._raise_if_requested("close")
        self.closed = True


def _unit_vec(values: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in values)) or 1.0
    return [v / norm for v in values]


def _make_index(tmp_path: Path, name: str = "memu_test") -> MilvusVectorIndex:
    pytest.importorskip("pymilvus")
    return MilvusVectorIndex(
        uri=str(tmp_path / "milvus.db"),
        collection_name=name,
    )


def test_milvus_filter_expression_escapes_scalars() -> None:
    assert _format_scalar('user "quoted"') == '"user \\"quoted\\""'
    assert _build_filter_expr({"user_id": 'u"1', "agent_id": "a1"}) == 'user_id == "u\\"1" and agent_id == "a1"'
    assert _build_filter_expr({"user_id__in": ["u1", 'u"2']}) == 'user_id in ["u1", "u\\"2"]'
    assert _build_filter_expr({"user_id": None}) == ""


def test_milvus_filter_expression_rejects_unsafe_inputs() -> None:
    assert _build_filter_expr({"user id": "u1"}) is None
    assert _build_filter_expr({"user_id) or id != (": "u1"}) is None
    assert _build_filter_expr({"user_id": {"nested": "u1"}}) is None


@pytest.mark.parametrize(
    ("provider", "dsn"),
    [("sqlite", "sqlite:///memu.db"), ("postgres", "postgresql://unused")],
)
def test_milvus_requires_inmemory_metadata_store(provider: str, dsn: str) -> None:
    config = DatabaseConfig.model_validate({
        "metadata_store": {"provider": provider, "dsn": dsn},
        "vector_index": {"provider": "milvus"},
    })
    with pytest.raises(ValueError, match="inmemory"):
        build_database(config=config, user_model=_UserScope)


def _new_fake_store(index: _RecordingVectorIndex) -> InMemoryStore:
    return InMemoryStore(scope_model=_UserScope, vector_index=index)


def _create_fake_segment(store: InMemoryStore, text: str = "alpha") -> Any:
    return store.recall_file_segment_repo.create_segment(
        recall_file_id="file-1",
        text=text,
        embedding=_unit_vec([1.0, 0.0, 0.0]),
        user_data={"user_id": "u1", "agent_id": "a1"},
    )


def test_external_upsert_failure_does_not_create_metadata() -> None:
    index = _RecordingVectorIndex()
    store = _new_fake_store(index)
    index.fail_on = "upsert"

    with pytest.raises(RuntimeError, match="upsert failed"):
        _create_fake_segment(store)

    assert store.segments == []
    assert index.rows == {}


def test_external_delete_failure_keeps_metadata_retryable() -> None:
    index = _RecordingVectorIndex()
    store = _new_fake_store(index)
    segment = _create_fake_segment(store)
    index.fail_on = "delete"

    with pytest.raises(RuntimeError, match="delete failed"):
        store.recall_file_segment_repo.delete_segment(segment.id)

    assert [item.id for item in store.segments] == [segment.id]
    assert segment.id in index.rows

    index.fail_on = None
    store.recall_file_segment_repo.delete_segment(segment.id)
    assert store.segments == []
    assert index.rows == {}


def test_external_delete_many_failure_keeps_file_segments_retryable() -> None:
    index = _RecordingVectorIndex()
    store = _new_fake_store(index)
    segments = [_create_fake_segment(store, text) for text in ("alpha", "beta")]
    index.fail_on = "delete_many"

    with pytest.raises(RuntimeError, match="delete_many failed"):
        store.recall_file_segment_repo.delete_segments_for_file("file-1")

    assert {item.id for item in store.segments} == {item.id for item in segments}
    assert set(index.rows) == {item.id for item in segments}


def test_external_clear_failure_keeps_scoped_segments_retryable() -> None:
    index = _RecordingVectorIndex()
    store = _new_fake_store(index)
    segments = [_create_fake_segment(store, text) for text in ("alpha", "beta")]
    index.fail_on = "delete_many"

    with pytest.raises(RuntimeError, match="delete_many failed"):
        store.recall_file_segment_repo.clear_segments(where={"user_id": "u1"})

    assert {item.id for item in store.segments} == {item.id for item in segments}
    assert set(index.rows) == {item.id for item in segments}


def test_inmemory_search_uses_an_internal_store_scope() -> None:
    index = _RecordingVectorIndex()
    store = _new_fake_store(index)
    segment = _create_fake_segment(store)

    hits = store.recall_file_segment_repo.vector_search_segments(_unit_vec([1.0, 0.0, 0.0]), 5, where={"user_id": "u1"})

    assert [item.id for item, _ in hits] == [segment.id]
    stored_scope = index.rows[segment.id][1]
    internal_fields = [key for key in stored_scope if key.startswith("_memu_")]
    assert len(internal_fields) == 1
    assert index.search_where[-1][internal_fields[0]] == stored_scope[internal_fields[0]]
    assert not any(key.startswith("id") for key in index.search_where[-1])


def test_inmemory_close_cleanup_failure_is_retryable() -> None:
    index = _RecordingVectorIndex()
    store = _new_fake_store(index)
    segment = _create_fake_segment(store)
    index.fail_on = "delete_many"

    with pytest.raises(RuntimeError, match="delete_many failed"):
        store.close()

    assert segment.id in index.rows
    assert not index.closed

    index.fail_on = None
    store.close()
    assert index.rows == {}
    assert index.closed


def test_milvus_vector_index_upsert_and_search(tmp_path: Path) -> None:
    index = _make_index(tmp_path)
    try:
        index.upsert("a", _unit_vec([1.0, 0.0, 0.0]), scope={"user_id": "u1"})
        index.upsert("b", _unit_vec([0.0, 1.0, 0.0]), scope={"user_id": "u1"})
        index.upsert("c", _unit_vec([0.0, 0.0, 1.0]), scope={"user_id": "u2"})

        hits = index.search(_unit_vec([1.0, 0.0, 0.0]), top_k=2)
        top_id, top_score = hits[0]
        assert top_id == "a"
        assert top_score > 0.99
        assert len(hits) == 2
        assert hits[1][1] == pytest.approx(0.0, abs=1e-6)
    finally:
        index.close()


def test_milvus_vector_index_accepts_optional_connection_settings(tmp_path: Path) -> None:
    pytest.importorskip("pymilvus")
    index = MilvusVectorIndex(
        uri=str(tmp_path / "milvus.db"),
        db_name="default",
        collection_name="memu_connection_settings",
        consistency_level="Strong",
    )
    try:
        index.upsert("a", _unit_vec([1.0, 0.0, 0.0]), scope={"user_id": "u1"})
        hits = index.search(_unit_vec([1.0, 0.0, 0.0]), top_k=1, where={"user_id": "u1"})
        assert hits and hits[0][0] == "a"
    finally:
        index.close()


def test_milvus_vector_index_scope_filter(tmp_path: Path) -> None:
    index = _make_index(tmp_path, name="memu_scope")
    try:
        index.upsert("a", _unit_vec([1.0, 0.0, 0.0]), scope={"user_id": "u1"})
        index.upsert("b", _unit_vec([1.0, 0.1, 0.0]), scope={"user_id": "u2"})

        hits = index.search(_unit_vec([1.0, 0.0, 0.0]), top_k=5, where={"user_id": "u2"})
        assert [hid for hid, _ in hits] == ["b"]
    finally:
        index.close()


def test_milvus_vector_index_delete_and_delete_many(tmp_path: Path) -> None:
    index = _make_index(tmp_path, name="memu_delete")
    try:
        index.upsert("a", _unit_vec([1.0, 0.0, 0.0]))
        index.upsert("b", _unit_vec([0.0, 1.0, 0.0]))
        index.upsert("c", _unit_vec([0.0, 0.0, 1.0]))

        index.delete("a")
        hits = index.search(_unit_vec([1.0, 0.0, 0.0]), top_k=5)
        assert "a" not in {hid for hid, _ in hits}

        index.delete_many(["b", "c"])
        hits = index.search(_unit_vec([1.0, 0.0, 0.0]), top_k=5)
        assert hits == []
    finally:
        index.close()


def test_milvus_vector_index_handles_quoted_ids(tmp_path: Path) -> None:
    index = _make_index(tmp_path, name="memu_quoted_ids")
    try:
        quoted_id = 'item "quoted"'
        index.upsert(quoted_id, _unit_vec([1.0, 0.0, 0.0]))

        index.delete(quoted_id)
        hits = index.search(_unit_vec([1.0, 0.0, 0.0]), top_k=5)
        assert quoted_id not in {hid for hid, _ in hits}
    finally:
        index.close()


def test_milvus_vector_index_rejects_dimension_mismatch(tmp_path: Path) -> None:
    index = _make_index(tmp_path, name="memu_dim")
    try:
        index.upsert("a", _unit_vec([1.0, 0.0, 0.0]))
        with pytest.raises(ValueError, match="dimension mismatch"):
            index.upsert("b", _unit_vec([1.0, 0.0]))
        with pytest.raises(ValueError, match="dimension mismatch"):
            index.search(_unit_vec([1.0, 0.0]), top_k=5)
    finally:
        index.close()


def _create_incompatible_collection(
    tmp_path: Path,
    name: str,
    *,
    dynamic: bool = True,
    primary_field: str = "id",
    vector_field: str = "vector",
    dim: int = 3,
    metric: str = "COSINE",
) -> None:
    from pymilvus import DataType, MilvusClient

    client = MilvusClient(uri=str(tmp_path / "milvus.db"))
    schema = client.create_schema(auto_id=False, enable_dynamic_field=dynamic)
    if primary_field == "id":
        schema.add_field(field_name="id", datatype=DataType.VARCHAR, is_primary=True, max_length=128)
    else:
        schema.add_field(field_name=primary_field, datatype=DataType.INT64, is_primary=True)
        schema.add_field(field_name="id", datatype=DataType.VARCHAR, max_length=128)
    schema.add_field(field_name=vector_field, datatype=DataType.FLOAT_VECTOR, dim=dim)
    indexes = client.prepare_index_params()
    indexes.add_index(field_name=vector_field, index_type="AUTOINDEX", metric_type=metric)
    client.create_collection(collection_name=name, schema=schema, index_params=indexes)
    client.close()


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"dynamic": False}, "dynamic fields"),
        ({"primary_field": "pk"}, "VARCHAR primary key"),
        ({"vector_field": "embedding"}, "missing vector field"),
        ({"dim": 4}, "dimension 4, expected 3"),
        ({"metric": "L2"}, "COSINE index"),
    ],
)
def test_reused_collection_rejects_schema_and_index_mismatches(
    tmp_path: Path, overrides: dict[str, Any], message: str
) -> None:
    pytest.importorskip("pymilvus")
    name = "memu_incompatible"
    _create_incompatible_collection(tmp_path, name, **overrides)
    index = MilvusVectorIndex(uri=str(tmp_path / "milvus.db"), collection_name=name)
    try:
        with pytest.raises(ValueError, match=message):
            index.upsert("a", _unit_vec([1.0, 0.0, 0.0]))
    finally:
        index.close()


def test_inmemory_backend_routes_segment_search_through_milvus(tmp_path: Path) -> None:
    pytest.importorskip("pymilvus")
    config = DatabaseConfig.model_validate({
        "metadata_store": {"provider": "inmemory"},
        "vector_index": {
            "provider": "milvus",
            "uri": str(tmp_path / "milvus.db"),
            "collection_name": "memu_e2e",
        },
    })
    db = build_database(config=config, user_model=_UserScope)
    try:
        repo = db.recall_file_segment_repo

        alpha = repo.create_segment(
            recall_file_id="f1",
            text="alpha",
            track="memory",
            embedding=_unit_vec([1.0, 0.0, 0.0]),
            user_data={"user_id": "u1", "agent_id": "a1"},
        )
        beta = repo.create_segment(
            recall_file_id="f1",
            text="beta",
            track="memory",
            embedding=_unit_vec([0.0, 1.0, 0.0]),
            user_data={"user_id": "u1", "agent_id": "a1"},
        )
        gamma = repo.create_segment(
            recall_file_id="f2",
            text="gamma",
            track="memory",
            embedding=_unit_vec([0.0, 0.0, 1.0]),
            user_data={"user_id": "u2", "agent_id": "a1"},
        )

        # Search scoped to u1: should only return alpha/beta, alpha first.
        hits = repo.vector_search_segments(
            query_vec=_unit_vec([1.0, 0.0, 0.0]),
            top_k=5,
            where={"user_id": "u1"},
        )
        ids = [segment.id for segment, _ in hits]
        assert ids[0] == alpha.id
        assert set(ids) == {alpha.id, beta.id}
        assert gamma.id not in ids

        # Delete propagates to Milvus.
        repo.delete_segment(alpha.id)
        hits = repo.vector_search_segments(
            query_vec=_unit_vec([1.0, 0.0, 0.0]),
            top_k=5,
            where={"user_id": "u1"},
        )
        assert alpha.id not in {segment.id for segment, _ in hits}

        # Recreating a segment with a new embedding upserts it into Milvus.
        repo.delete_segment(beta.id)
        beta = repo.create_segment(
            recall_file_id="f1",
            text="beta",
            track="memory",
            embedding=_unit_vec([1.0, 0.0, 0.0]),
            user_data={"user_id": "u1", "agent_id": "a1"},
        )
        hits = repo.vector_search_segments(
            query_vec=_unit_vec([1.0, 0.0, 0.0]),
            top_k=5,
            where={"user_id": "u1"},
        )
        assert hits and hits[0][0].id == beta.id
    finally:
        db.close()


def test_inmemory_stores_isolate_and_cleanup_shared_collection(tmp_path: Path) -> None:
    from pymilvus import MilvusClient

    pytest.importorskip("pymilvus")
    uri = str(tmp_path / "milvus.db")
    collection_name = "memu_shared"
    config = DatabaseConfig.model_validate({
        "metadata_store": {"provider": "inmemory"},
        "vector_index": {
            "provider": "milvus",
            "uri": uri,
            "collection_name": collection_name,
            "consistency_level": "Strong",
        },
    })
    first = build_database(config=config, user_model=_UserScope)
    second = build_database(config=config, user_model=_UserScope)
    first_closed = False
    second_closed = False
    try:
        first_segment = first.recall_file_segment_repo.create_segment(
            recall_file_id="first",
            text="first",
            embedding=_unit_vec([0.0, 1.0, 0.0]),
            user_data={"user_id": "shared", "agent_id": "a1"},
        )
        second_segment = second.recall_file_segment_repo.create_segment(
            recall_file_id="second",
            text="second",
            embedding=_unit_vec([1.0, 0.0, 0.0]),
            user_data={"user_id": "shared", "agent_id": "a1"},
        )

        first_hits = first.recall_file_segment_repo.vector_search_segments(
            _unit_vec([1.0, 0.0, 0.0]), 1, where={"user_id": "shared"}
        )
        second_hits = second.recall_file_segment_repo.vector_search_segments(
            _unit_vec([1.0, 0.0, 0.0]), 1, where={"user_id": "shared"}
        )
        assert [segment.id for segment, _ in first_hits] == [first_segment.id]
        assert [segment.id for segment, _ in second_hits] == [second_segment.id]

        first.close()
        first_closed = True
        remaining = second.recall_file_segment_repo.vector_search_segments(
            _unit_vec([1.0, 0.0, 0.0]), 1, where={"user_id": "shared"}
        )
        assert [segment.id for segment, _ in remaining] == [second_segment.id]

        second.close()
        second_closed = True
        raw = MilvusClient(uri=uri)
        try:
            assert raw.has_collection(collection_name=collection_name)
            assert raw.search(
                collection_name=collection_name,
                data=[_unit_vec([1.0, 0.0, 0.0])],
                limit=5,
                search_params={"metric_type": "COSINE"},
            ) == [[]]
        finally:
            raw.close()
    finally:
        if not first_closed:
            first.close()
        if not second_closed:
            second.close()


def test_inmemory_backend_milvus_filters_segment_metadata(tmp_path: Path) -> None:
    pytest.importorskip("pymilvus")
    config = DatabaseConfig.model_validate({
        "metadata_store": {"provider": "inmemory"},
        "vector_index": {
            "provider": "milvus",
            "uri": str(tmp_path / "milvus.db"),
            "collection_name": "memu_metadata_filter",
        },
    })
    db = build_database(config=config, user_model=_UserScope)
    try:
        repo = db.recall_file_segment_repo

        memory = repo.create_segment(
            recall_file_id="f1",
            text="memory alpha",
            track="memory",
            embedding=_unit_vec([1.0, 0.0, 0.0]),
            user_data={"user_id": "u1", "agent_id": "a1"},
        )
        skill = repo.create_segment(
            recall_file_id="f2",
            text="skill alpha",
            track="skill",
            embedding=_unit_vec([1.0, 0.1, 0.0]),
            user_data={"user_id": "u1", "agent_id": "a1"},
        )

        hits = repo.vector_search_segments(
            query_vec=_unit_vec([1.0, 0.0, 0.0]),
            top_k=5,
            where={"track": "skill"},
        )
        assert [segment.id for segment, _ in hits] == [skill.id]
        assert memory.id not in {segment.id for segment, _ in hits}

        hits = repo.vector_search_segments(
            query_vec=_unit_vec([1.0, 0.0, 0.0]),
            top_k=5,
            where={"recall_file_id__in": ["f2"]},
        )
        assert [segment.id for segment, _ in hits] == [skill.id]
    finally:
        db.close()


def test_inmemory_backend_clear_segments_propagates_to_milvus(tmp_path: Path) -> None:
    pytest.importorskip("pymilvus")
    config = DatabaseConfig.model_validate({
        "metadata_store": {"provider": "inmemory"},
        "vector_index": {
            "provider": "milvus",
            "uri": str(tmp_path / "milvus.db"),
            "collection_name": "memu_clear",
        },
    })
    db = build_database(config=config, user_model=_UserScope)
    try:
        repo = db.recall_file_segment_repo
        for i in range(3):
            repo.create_segment(
                recall_file_id="f1",
                text=f"segment-{i}",
                track="memory",
                embedding=_unit_vec([1.0, float(i), 0.0]),
                user_data={"user_id": "u1", "agent_id": "a1"},
            )

        repo.clear_segments(where={"user_id": "u1"})
        hits = repo.vector_search_segments(
            query_vec=_unit_vec([1.0, 0.0, 0.0]),
            top_k=5,
            where={"user_id": "u1"},
        )
        assert hits == []
    finally:
        db.close()


async def test_progressive_retrieve_uses_milvus_segment_index(tmp_path: Path) -> None:
    pytest.importorskip("pymilvus")
    service = MemoryService(
        database_config={
            "metadata_store": {"provider": "inmemory"},
            "vector_index": {
                "provider": "milvus",
                "uri": str(tmp_path / "milvus.db"),
                "collection_name": "memu_progressive",
            },
        },
        user_config={"model": _UserScope},
    )
    fake: Any = _FakeEmbeddingClient()
    service._embedding_pool._cache["default"] = fake
    service._embedding_pool._cache["embedding"] = fake
    try:
        await service.commit_results(
            recall_files=[
                {"name": "Profile", "track": "memory", "description": "alpha", "content": "# P\nalpha coffee"},
                {"name": "Deploy", "track": "skill", "description": "beta deploy", "content": "beta deploy"},
            ],
            user={"user_id": "u1", "agent_id": "a1"},
        )

        result = await service.progressive_retrieve("coffee", where={"user_id": "u1"})

        assert result["segments"][0]["text"] == "alpha coffee"
        assert result["files"][0]["name"] == "Profile"

        await service.commit_results(
            recall_files=[
                {"name": "Profile", "track": "memory", "description": "gamma", "content": "# P\ngamma tea"},
            ],
            user={"user_id": "u1", "agent_id": "a1"},
        )
        old_result = await service.progressive_retrieve("coffee", where={"user_id": "u1"})
        new_result = await service.progressive_retrieve("gamma", where={"user_id": "u1"})
        assert "alpha coffee" not in {segment["text"] for segment in old_result["segments"]}
        assert new_result["segments"][0]["text"] == "gamma tea"
    finally:
        service.database.close()


async def test_failed_embedding_does_not_mutate_milvus_or_metadata(tmp_path: Path) -> None:
    pytest.importorskip("pymilvus")
    service = MemoryService(
        database_config={
            "metadata_store": {"provider": "inmemory"},
            "vector_index": {
                "provider": "milvus",
                "uri": str(tmp_path / "milvus.db"),
                "collection_name": "memu_embedding_failure",
                "consistency_level": "Strong",
            },
        },
        user_config={"model": _UserScope},
    )
    fake: Any = _FakeEmbeddingClient()
    service._embedding_pool._cache["default"] = fake
    service._embedding_pool._cache["embedding"] = fake
    try:
        await service.commit_results(
            recall_files=[
                {"name": "Profile", "track": "memory", "description": "alpha", "content": "alpha coffee"},
            ],
            user={"user_id": "u1", "agent_id": "a1"},
        )
        before_files = await service.list_all_recall_files(where={"user_id": "u1"})
        before_search = await service.progressive_retrieve("coffee", where={"user_id": "u1"})

        service._embedding_pool._cache["embedding"] = _FailingEmbeddingClient()
        with pytest.raises(RuntimeError, match="embedding unavailable"):
            await service.commit_results(
                recall_files=[
                    {"name": "Profile", "track": "memory", "description": "beta", "content": "beta deploy"},
                    {"name": "New", "track": "memory", "description": "gamma", "content": "gamma"},
                ],
                user={"user_id": "u1", "agent_id": "a1"},
            )

        service._embedding_pool._cache["embedding"] = fake
        assert await service.list_all_recall_files(where={"user_id": "u1"}) == before_files
        assert await service.progressive_retrieve("coffee", where={"user_id": "u1"}) == before_search
    finally:
        service.database.close()
