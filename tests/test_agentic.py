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


async def test_list_all_recall_files_paginates_by_track_name_id(service: MemoryService) -> None:
    # Commit more files than the page size, spread across both tracks.
    limit = 3
    committed = await service.commit_results(
        recall_files=[
            {"name": f"m{i:02d}", "track": "memory", "description": "d", "content": f"line {i}"} for i in range(4)
        ]
        + [{"name": f"s{i:02d}", "track": "skill", "description": "d", "content": f"step {i}"} for i in range(4)],
    )
    assert len(committed["recall_files"]) == 8

    # Walk every page by following next_cursor, as prepare/CLI do.
    seen: list[tuple[str, str]] = []
    pages = 0
    cursor: str | None = None
    while True:
        page = await service.list_all_recall_files(cursor=cursor, limit=limit)
        assert len(page["recall_files"]) <= limit
        seen.extend((f["track"], f["name"]) for f in page["recall_files"])
        pages += 1
        cursor = page["next_cursor"]
        if not cursor:
            break

    # Every file exactly once (no skips/dups), in (track, name) order, and the
    # final page correctly signalled the end.
    expected = sorted([("memory", f"m{i:02d}") for i in range(4)] + [("skill", f"s{i:02d}") for i in range(4)])
    assert seen == expected
    assert pages == 3  # 8 files / page size 3 -> 3,3,2


async def test_list_all_recall_files_rejects_nonpositive_limit(service: MemoryService) -> None:
    with pytest.raises(ValueError, match="limit must be greater than zero"):
        await service.list_all_recall_files(limit=0)


@pytest.mark.parametrize("cursor", ["not-a-cursor", "WyJ0b28iLCAic2hvcnQiXQ==", "WzEsIDIsIDNd"])
async def test_list_all_recall_files_rejects_malformed_cursor(service: MemoryService, cursor: str) -> None:
    with pytest.raises(ValueError, match="invalid cursor"):
        await service.list_all_recall_files(cursor=cursor)


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
    profile = next(f for f in listed["recall_files"] if f["name"] == "Profile")
    assert profile["description"] == "the user profile"


async def test_recommit_updates_skill_description_and_segment(service: MemoryService) -> None:
    file = {"name": "deploy-checklist", "track": "skill", "description": "how to deploy", "content": "step 1"}
    await service.commit_results(recall_files=[file])
    await service.commit_results(recall_files=[{**file, "description": "deploy the app"}])

    listed = await service.list_all_recall_files()
    skill = next(f for f in listed["recall_files"] if f["name"] == "deploy-checklist")
    assert skill["description"] == "deploy the app"

    # The skill's single segment is ``name: ...\ndescription: ...``, so it re-embeds too.
    result = await service.progressive_retrieve("deploy")
    seg_texts = [seg["text"] for seg in result["segments"]]
    assert "name: deploy-checklist\ndescription: deploy the app" in seg_texts
    assert "name: deploy-checklist\ndescription: how to deploy" not in seg_texts


class EmbeddingProviderDown(RuntimeError):
    """What a rate limit or a dead provider looks like to ``commit_results``."""


class FailingEmbeddingClient(FakeEmbeddingClient):
    """Fails the way a rate-limited or unreachable provider does."""

    def __init__(self, *, fail_on_call: int = 1) -> None:
        self.calls = 0
        self._fail_on_call = fail_on_call

    async def embed(self, inputs: list[str]) -> tuple[list[list[float]], None]:
        self.calls += 1
        if self.calls == self._fail_on_call:
            raise EmbeddingProviderDown
        return await super().embed(inputs)


async def test_failed_embedding_leaves_the_store_untouched(service: MemoryService) -> None:
    """A commit that cannot embed must write nothing — not even the items before the failure.

    Each repo call commits its own transaction, so a write reached before the
    failing embed would be permanent. This is the guarantee that makes a failed
    commit safe to simply retry.
    """
    await _seed(service)
    before = await service.list_all_recall_files()
    baseline = await service.progressive_retrieve("coffee")

    service._embedding_pool._cache["embedding"] = FailingEmbeddingClient()
    with pytest.raises(EmbeddingProviderDown):
        await service.commit_results(
            recall_files=[
                {"name": "Profile", "track": "memory", "description": "changed", "content": "# P\nlikes tea"},
                {"name": "brand-new", "track": "memory", "description": "new", "content": "unseen line"},
            ],
            resource=[{"path": "/workspace/notes.md", "description": "rewritten caption"}],
        )

    after = await service.list_all_recall_files()
    assert after["recall_files"] == before["recall_files"]

    # The pre-existing resource survived: its caption embed failed, and the old
    # record must not have been dropped in anticipation of a replacement.
    service._embedding_pool._cache["embedding"] = FakeEmbeddingClient()
    assert await service.progressive_retrieve("coffee") == baseline


async def test_commit_embeds_everything_in_one_batched_call(service: MemoryService) -> None:
    """Files, resources and segments share a single provider round-trip."""
    counter = CountingEmbeddingClient()
    service._embedding_pool._cache["embedding"] = counter

    await service.commit_results(
        recall_files=[
            {"name": "A", "track": "memory", "description": "d", "content": "one\ntwo"},
            {"name": "B", "track": "skill", "description": "e", "content": "step"},
        ],
        resource=[{"path": "/w/a.md", "description": "cap a"}, {"path": "/w/b.md", "description": "cap b"}],
    )
    assert counter.calls == 1


async def test_repeated_path_in_one_payload_commits_once(service: MemoryService) -> None:
    """Two records for one url collapse to one, in the response as well as the store.

    The store always ended up with a single row, but the returned list used to
    carry the superseded record too — so ``memu commit`` printed an inflated
    count and filed it to telemetry.
    """
    committed = await service.commit_results(
        resource=[
            {"path": "/workspace/dup.md", "description": "first"},
            {"path": "/workspace/dup.md", "description": "second"},
        ]
    )
    assert len(committed["resources"]) == 1

    found = await service.progressive_retrieve("second")
    assert [r["url"] for r in found["resources"]] == ["/workspace/dup.md"]
    assert [r["caption"] for r in found["resources"]] == ["second"]


async def test_recommit_updates_the_resource_row_in_place(service: MemoryService) -> None:
    """A url keeps its row across recommits, and an unchanged caption is not re-embedded.

    Delete-then-create churned the id and created_at on every commit — unlike the
    recall-file path, which updates in place — and paid the provider for a caption
    vector each time, because a recreated row has no stored vector to keep.
    """
    counter = CountingEmbeddingClient()
    service._embedding_pool._cache["embedding"] = counter

    record = {"path": "/workspace/notes.md", "description": "meeting notes"}
    original = (await service.commit_results(resource=[record]))["resources"][0]

    counter.calls = 0
    again = (await service.commit_results(resource=[dict(record)]))["resources"][0]
    assert counter.calls == 0
    assert again["id"] == original["id"]
    assert again["created_at"] == original["created_at"]

    # A changed caption is re-embedded, and lands on that same row.
    counter.calls = 0
    changed = (await service.commit_results(resource=[{**record, "description": "deploy notes"}]))["resources"][0]
    assert counter.calls == 1
    assert changed["id"] == original["id"]
    assert changed["caption"] == "deploy notes"
    found = await service.progressive_retrieve("deploy notes")
    assert [r["url"] for r in found["resources"]] == ["/workspace/notes.md"]

    # A record with no description clears the caption and its vector: the commit
    # payload is authoritative for a resource, and an unranked row cannot be recalled.
    cleared = (await service.commit_results(resource=[{"path": "/workspace/notes.md"}]))["resources"][0]
    assert cleared["id"] == original["id"]
    assert cleared["caption"] is None
    assert (await service.progressive_retrieve("deploy notes"))["resources"] == []


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
