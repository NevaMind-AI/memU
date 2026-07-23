"""End-to-end tests for the three agentic entry points.

``commit_results`` -> ``list_all_recall_files`` -> ``progressive_retrieve``
against the inmemory and sqlite backends, with a fake embedding client so no
network is involved. This is the service's whole public surface.
"""

from __future__ import annotations

from typing import Any

import pytest

from memu.app import MemoryService


class FakeEmbeddingClient:
    """Deterministic embeddings: similar strings share a prefix dimension.

    Returns ``(vectors, raw_response)`` like every real client
    (:class:`memu.embedding.base.EmbeddingClient`) — a fake returning a bare
    list is exactly what let the tuple-consumption bug (#499) through.
    """

    embed_model = "fake"

    async def embed(self, inputs: list[str]) -> tuple[list[list[float]], None]:
        vectors = []
        for text in inputs:
            lowered = text.lower()
            vectors.append([
                1.0 if "coffee" in lowered else 0.0,
                1.0 if "deploy" in lowered else 0.0,
                1.0 if "notes" in lowered else 0.0,
                float(len(lowered) % 5) / 10.0,
            ])
        return vectors, None


def make_service(database_config: dict[str, Any]) -> MemoryService:
    service = MemoryService(database_config=database_config)
    fake = FakeEmbeddingClient()
    service._embedding_pool._cache["default"] = fake
    service._embedding_pool._cache["embedding"] = fake
    return service


@pytest.fixture(params=["inmemory", "sqlite"])
def service(request: pytest.FixtureRequest, tmp_path: Any) -> MemoryService:
    if request.param == "inmemory":
        return make_service({"metadata_store": {"provider": "inmemory"}})
    return make_service({"metadata_store": {"provider": "sqlite", "dsn": f"sqlite:///{tmp_path}/memu.sqlite3"}})


async def _seed(service: MemoryService) -> dict[str, Any]:
    return await service.commit_results(
        recall_files=[
            {"name": "Profile", "track": "memory", "description": "who the user is", "content": "# P\nlikes coffee"},
            {"name": "deploy-checklist", "track": "skill", "description": "how to deploy", "content": "step 1"},
        ],
        resource=[{"path": "/workspace/notes.md", "description": "meeting notes"}],
    )


async def test_commit_then_list_covers_both_tracks(service: MemoryService) -> None:
    result = await _seed(service)
    assert len(result["recall_files"]) == 2
    assert len(result["resources"]) == 1
    # Embeddings never leak out of the persistence API.
    assert all("embedding" not in f for f in result["recall_files"])

    listed = await service.list_all_recall_files()
    by_track = sorted((f["track"], f["name"]) for f in listed["recall_files"])
    assert by_track == [("memory", "Profile"), ("skill", "deploy-checklist")]


async def test_progressive_retrieve_ranks_all_three_layers(service: MemoryService) -> None:
    await _seed(service)
    result = await service.progressive_retrieve("coffee")

    assert next(seg["text"] for seg in result["segments"]) == "likes coffee"
    file_names = [f["name"] for f in result["files"]]
    assert file_names[0] == "Profile"
    # Committed resources land on the workspace track and are retrievable.
    assert [r["url"] for r in result["resources"]] == ["/workspace/notes.md"]


async def test_recommit_updates_content_and_segments(service: MemoryService) -> None:
    await _seed(service)
    await service.commit_results(
        recall_files=[{"name": "Profile", "track": "memory", "description": "who", "content": "# P\nlikes tea"}]
    )

    listed = await service.list_all_recall_files()
    profile = next(f for f in listed["recall_files"] if f["name"] == "Profile")
    assert profile["content"] == "# P\nlikes tea"

    result = await service.progressive_retrieve("tea time")
    assert "likes coffee" not in [seg["text"] for seg in result["segments"]]


class CountingEmbeddingClient(FakeEmbeddingClient):
    """Wraps the fake to count ``embed`` calls, so tests can assert re-embeds."""

    def __init__(self) -> None:
        self.calls = 0

    async def embed(self, inputs: list[str]) -> tuple[list[list[float]], None]:
        self.calls += 1
        return await super().embed(inputs)


async def test_recommit_reembeds_description_only_when_changed(service: MemoryService) -> None:
    counter = CountingEmbeddingClient()
    service._embedding_pool._cache["default"] = counter
    service._embedding_pool._cache["embedding"] = counter

    file = {"name": "Profile", "track": "memory", "description": "who the user is", "content": "# P\nlikes coffee"}
    await service.commit_results(recall_files=[file])

    # Recommit with identical description and content: nothing needs embedding.
    counter.calls = 0
    await service.commit_results(recall_files=[dict(file)])
    assert counter.calls == 0

    # Recommit with a changed description: the file-level vector is refreshed exactly once
    # (memory segments are per content line, so the unchanged content stays put).
    counter.calls = 0
    await service.commit_results(recall_files=[{**file, "description": "the user profile"}])
    assert counter.calls == 1

    listed = await service.list_all_recall_files()
    profile = next(f for f in listed["categories"] if f["name"] == "Profile")
    assert profile["description"] == "the user profile"


async def test_recommit_updates_skill_description_and_segment(service: MemoryService) -> None:
    file = {"name": "deploy-checklist", "track": "skill", "description": "how to deploy", "content": "step 1"}
    await service.commit_results(recall_files=[file])
    await service.commit_results(recall_files=[{**file, "description": "deploy the app"}])

    listed = await service.list_all_recall_files()
    skill = next(f for f in listed["categories"] if f["name"] == "deploy-checklist")
    assert skill["description"] == "deploy the app"

    # The skill's single segment is ``name: ...\ndescription: ...``, so it re-embeds too.
    result = await service.progressive_retrieve("deploy")
    seg_texts = [seg["text"] for seg in result["segments"]]
    assert "name: deploy-checklist\ndescription: deploy the app" in seg_texts
    assert "name: deploy-checklist\ndescription: how to deploy" not in seg_texts


async def test_where_scope_filters_and_rejects_unknown_fields(service: MemoryService) -> None:
    await service.commit_results(
        recall_files=[{"name": "A", "track": "memory", "description": "d", "content": "alpha"}],
        user={"user_id": "u1"},
    )
    await service.commit_results(
        recall_files=[{"name": "B", "track": "memory", "description": "d", "content": "beta"}],
        user={"user_id": "u2"},
    )

    listed = await service.list_all_recall_files(where={"user_id": "u1"})
    assert [f["name"] for f in listed["recall_files"]] == ["A"]

    with pytest.raises(ValueError, match="Unknown filter field"):
        await service.list_all_recall_files(where={"nope": "x"})


async def test_progressive_retrieve_rejects_empty_query(service: MemoryService) -> None:
    with pytest.raises(ValueError, match="empty_query"):
        await service.progressive_retrieve("   ")
