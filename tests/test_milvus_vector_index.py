from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

from memu.app import MemoryService
from memu.app.settings import DatabaseConfig
from memu.database.factory import build_database
from memu.database.vector_index.milvus import (
    MilvusVectorIndex,
    _build_filter_expr,
    _cosine_distance_to_similarity,
    _format_scalar,
)


class _UserScope(BaseModel):
    user_id: str = ""
    agent_id: str = ""


class _FakeEmbeddingClient:
    embed_model = "fake"

    async def embed(self, inputs: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in inputs:
            lowered = text.lower()
            vectors.append([
                1.0 if "alpha" in lowered or "coffee" in lowered else 0.0,
                1.0 if "beta" in lowered or "deploy" in lowered else 0.0,
                1.0 if "gamma" in lowered else 0.0,
            ])
        return vectors


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


def test_milvus_cosine_distance_is_converted_to_similarity() -> None:
    assert _cosine_distance_to_similarity(0.0) == pytest.approx(1.0)
    assert _cosine_distance_to_similarity(1.0) == pytest.approx(0.0)
    assert _cosine_distance_to_similarity(2.0) == pytest.approx(-1.0)


def test_milvus_requires_inmemory_metadata_store() -> None:
    config = DatabaseConfig.model_validate({
        "metadata_store": {"provider": "sqlite", "dsn": "sqlite:///memu.db"},
        "vector_index": {"provider": "milvus"},
    })
    with pytest.raises(ValueError, match="inmemory"):
        build_database(config=config, user_model=_UserScope)


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
        ids = [hid for hid, _ in hits]
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
        assert alpha.id not in {hid for hid, _ in hits}

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
        assert hits and hits[0][0] == beta.id
    finally:
        db.close()


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
        assert [hid for hid, _ in hits] == [skill.id]
        assert memory.id not in {hid for hid, _ in hits}

        hits = repo.vector_search_segments(
            query_vec=_unit_vec([1.0, 0.0, 0.0]),
            top_k=5,
            where={"recall_file_id__in": ["f2"]},
        )
        assert [hid for hid, _ in hits] == [skill.id]
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
    finally:
        service.database.close()
