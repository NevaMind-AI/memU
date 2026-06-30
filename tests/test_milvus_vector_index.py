from __future__ import annotations

import math
from pathlib import Path

import pytest
from pydantic import BaseModel

from memu.app.settings import DatabaseConfig
from memu.database.factory import build_database
from memu.database.vector_index.milvus import MilvusVectorIndex, _build_filter_expr, _format_scalar


class _UserScope(BaseModel):
    user_id: str = ""
    agent_id: str = ""


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


def test_inmemory_backend_routes_search_through_milvus(tmp_path: Path) -> None:
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
        repo = db.memory_item_repo

        alpha = repo.create_item(
            resource_id="r1",
            memory_type="profile",
            summary="alpha",
            embedding=_unit_vec([1.0, 0.0, 0.0]),
            user_data={"user_id": "u1", "agent_id": "a1"},
        )
        beta = repo.create_item(
            resource_id="r1",
            memory_type="profile",
            summary="beta",
            embedding=_unit_vec([0.0, 1.0, 0.0]),
            user_data={"user_id": "u1", "agent_id": "a1"},
        )
        gamma = repo.create_item(
            resource_id="r1",
            memory_type="profile",
            summary="gamma",
            embedding=_unit_vec([0.0, 0.0, 1.0]),
            user_data={"user_id": "u2", "agent_id": "a1"},
        )

        # Search scoped to u1: should only return alpha/beta, alpha first.
        hits = repo.vector_search_items(
            query_vec=_unit_vec([1.0, 0.0, 0.0]),
            top_k=5,
            where={"user_id": "u1"},
        )
        ids = [hid for hid, _ in hits]
        assert ids[0] == alpha.id
        assert set(ids) == {alpha.id, beta.id}
        assert gamma.id not in ids

        # Delete propagates to Milvus.
        repo.delete_item(alpha.id)
        hits = repo.vector_search_items(
            query_vec=_unit_vec([1.0, 0.0, 0.0]),
            top_k=5,
            where={"user_id": "u1"},
        )
        assert alpha.id not in {hid for hid, _ in hits}

        # Update with a new embedding re-upserts.
        repo.update_item(item_id=beta.id, embedding=_unit_vec([1.0, 0.0, 0.0]))
        hits = repo.vector_search_items(
            query_vec=_unit_vec([1.0, 0.0, 0.0]),
            top_k=5,
            where={"user_id": "u1"},
        )
        assert hits and hits[0][0] == beta.id
    finally:
        db.close()


def test_inmemory_backend_milvus_filters_core_metadata(tmp_path: Path) -> None:
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
        repo = db.memory_item_repo

        profile = repo.create_item(
            resource_id="r1",
            memory_type="profile",
            summary="profile",
            embedding=_unit_vec([1.0, 0.0, 0.0]),
            user_data={"user_id": "u1", "agent_id": "a1"},
        )
        event = repo.create_item(
            resource_id="r2",
            memory_type="event",
            summary="event",
            embedding=_unit_vec([1.0, 0.1, 0.0]),
            user_data={"user_id": "u1", "agent_id": "a1"},
        )

        hits = repo.vector_search_items(
            query_vec=_unit_vec([1.0, 0.0, 0.0]),
            top_k=5,
            where={"memory_type": "event"},
        )
        assert [hid for hid, _ in hits] == [event.id]
        assert profile.id not in {hid for hid, _ in hits}

        hits = repo.vector_search_items(
            query_vec=_unit_vec([1.0, 0.0, 0.0]),
            top_k=5,
            where={"resource_id__in": ["r2"]},
        )
        assert [hid for hid, _ in hits] == [event.id]
    finally:
        db.close()


def test_inmemory_backend_clear_items_propagates_to_milvus(tmp_path: Path) -> None:
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
        repo = db.memory_item_repo
        for i in range(3):
            repo.create_item(
                resource_id="r1",
                memory_type="profile",
                summary=f"item-{i}",
                embedding=_unit_vec([1.0, float(i), 0.0]),
                user_data={"user_id": "u1", "agent_id": "a1"},
            )

        repo.clear_items(where={"user_id": "u1"})
        hits = repo.vector_search_items(
            query_vec=_unit_vec([1.0, 0.0, 0.0]),
            top_k=5,
            where={"user_id": "u1"},
        )
        assert hits == []
    finally:
        db.close()
