from __future__ import annotations

import math
from pathlib import Path

import pytest
from pydantic import BaseModel

pytest.importorskip("pymilvus")

from memu.app.settings import DatabaseConfig
from memu.database.factory import build_database
from memu.database.vector_index.milvus import MilvusVectorIndex


class _UserScope(BaseModel):
    user_id: str = ""
    agent_id: str = ""


def _unit_vec(values: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in values)) or 1.0
    return [v / norm for v in values]


def _make_index(tmp_path: Path, name: str = "memu_test") -> MilvusVectorIndex:
    return MilvusVectorIndex(
        uri=str(tmp_path / "milvus.db"),
        collection_name=name,
    )


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


def test_inmemory_backend_routes_search_through_milvus(tmp_path: Path) -> None:
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


def test_inmemory_backend_clear_items_propagates_to_milvus(tmp_path: Path) -> None:
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
