"""End-to-end tests for the three agentic entry points.

``commit_results`` -> ``list_all_recall_files`` -> ``progressive_retrieve``
against the inmemory and sqlite backends, with a fake embedding client so no
network is involved. This is the service's whole public surface.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from memu.app import MemoryService
from memu.app.memorize.input import MemorizeInput, MessageInput
from memu.app.memorize.lifecycle import MemorizeWorkspace, commit_memorize, prepare_memorize
from memu.hosts import retrieval
from memu.hosts.bridging.recall_files import read_recall_file


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
    assert by_track == [("memory", "profile"), ("skill", "deploy-checklist")]


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
    assert file_names[0] == "profile"
    # Committed resources land on the workspace track and are retrievable.
    assert [r["url"] for r in result["resources"]] == ["/workspace/notes.md"]


async def test_recommit_updates_content_and_segments(service: MemoryService) -> None:
    await _seed(service)
    await service.commit_results(
        recall_files=[{"name": "Profile", "track": "memory", "description": "who", "content": "# P\nlikes tea"}]
    )

    listed = await service.list_all_recall_files()
    profile = next(f for f in listed["recall_files"] if f["name"] == "profile")
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
    profile = next(f for f in listed["recall_files"] if f["name"] == "profile")
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
    assert [f["name"] for f in listed["recall_files"]] == ["a"]

    with pytest.raises(ValueError, match="Unknown filter field"):
        await service.list_all_recall_files(where={"nope": "x"})


async def test_progressive_retrieve_rejects_empty_query(service: MemoryService) -> None:
    with pytest.raises(ValueError, match="empty_query"):
        await service.progressive_retrieve("   ")


async def test_retrieve_rollup_fetches_only_hit_files(service: MemoryService) -> None:
    """Roll-up must not list the whole scoped corpus on every retrieve.

    :meth:`AgenticMixin._collect_files` needs only the :class:`RecallFile` rows
    that top segments point at, so it should issue an ``id__in`` fetch — a full
    ``list_recall_files`` read for a handful of ids is wasted work that grows
    with the store. The response surface stays identical.
    """
    await _seed(service)
    repo = service._get_database().recall_file_repo
    real_list = repo.list_recall_files
    seen: list[dict[str, Any]] = []

    def spying_list(where: Any = None) -> Any:
        seen.append(where or {})
        return real_list(where)

    repo.list_recall_files = spying_list  # type: ignore[method-assign]

    result = await service.progressive_retrieve("coffee")

    assert len(seen) == 1  # the roll-up fetch; nothing else lists files
    hit_ids = {seg["recall_file_id"] for seg in result["segments"]}
    assert set(seen[0].get("id__in", [])) == hit_ids


async def test_retrieve_rollup_short_circuits_when_no_segments(service: MemoryService) -> None:
    """No segment hits means no file fetch at all, not an empty full listing."""
    await _seed(service)
    repo = service._get_database().recall_file_repo
    real_list = repo.list_recall_files
    calls: list[dict[str, Any]] = []

    def spying_list(where: Any = None) -> Any:
        calls.append(where or {})
        return real_list(where)

    repo.list_recall_files = spying_list  # type: ignore[method-assign]
    segment_repo = service._get_database().recall_file_segment_repo

    def no_hits(query_vec: Any, top_k: int, where: Any = None) -> Any:
        return []

    segment_repo.vector_search_segments = no_hits  # type: ignore[method-assign]

    await service.progressive_retrieve("nothing matches")
    assert calls == []


async def test_sqlite_resource_commit_sees_writes_from_another_instance(tmp_path: Any) -> None:
    """Two SQLiteStore instances on the same DB file share ground truth, matching
    PostgresResourceRepo's always-fresh reads: an unfiltered ``list_resources`` must
    not shortcut to a per-instance cache once that cache is non-empty, or a sibling
    instance's later write becomes invisible and a same-url recommit duplicates it.
    """
    dsn = f"sqlite:///{tmp_path}/memu.sqlite3"
    service_a = make_service({"metadata_store": {"provider": "sqlite", "dsn": dsn}})
    service_b = make_service({"metadata_store": {"provider": "sqlite", "dsn": dsn}})

    await service_a.commit_results(resource=[{"path": "/workspace/notes.md", "description": "v1"}])
    # First unfiltered read on a fresh instance always hits the DB, so this warms
    # service_b's cache with notes.md too.
    await service_b.commit_results(resource=[{"path": "/workspace/other.md", "description": "other"}])

    await service_a.commit_results(resource=[{"path": "/workspace/extra.md", "description": "a's version"}])
    committed = await service_b.commit_results(resource=[{"path": "/workspace/extra.md", "description": "b's version"}])
    assert len(committed["resources"]) == 1

    fresh = make_service({"metadata_store": {"provider": "sqlite", "dsn": dsn}})
    rows = fresh._get_database().resource_repo.list_resources()
    matches = [r for r in rows.values() if r.url == "/workspace/extra.md"]
    assert len(matches) == 1
    assert matches[0].caption == "b's version"


@pytest.mark.parametrize("track", ["memory", "skill"])
@pytest.mark.parametrize("reverse", [False, True])
async def test_canonical_names_deduplicate_before_writing_and_mirror_last_content(
    service: MemoryService, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, track: str, reverse: bool
) -> None:
    records = [
        {"name": "Project Preferences", "track": track, "description": "first", "content": "likes coffee"},
        {"name": "project-preferences", "track": track, "description": "last", "content": "deploy notes"},
    ]
    if reverse:
        records.reverse()
    original = deepcopy(records)
    result = await service.commit_results(recall_files=records)

    assert len(result["recall_files"]) == 1
    stored = result["recall_files"][0]
    assert stored["name"] == "project-preferences"
    assert stored["content"] == records[-1]["content"]
    assert stored["description"] == records[-1]["description"]
    assert len((await service.list_all_recall_files())["recall_files"]) == 1
    segments = service._get_database().recall_file_segment_repo.list_segments_for_file(stored["id"])
    expected = (
        records[-1]["content"]
        if track == "memory"
        else f"name: project-preferences\ndescription: {records[-1]['description']}"
    )
    assert [segment.text for segment in segments] == [expected]
    assert records == original

    monkeypatch.setattr(retrieval, "BASE_DIR", str(tmp_path / "mirrors"))
    shaped = retrieval._shape_for_agent(await service.progressive_retrieve("coffee deploy notes"))
    assert len(shaped["files"]) == 1
    path = Path(shaped["files"][0]["path"])
    assert path.name == "project-preferences.md"
    assert read_recall_file(path, track) == {
        "name": stored["name"],
        "track": track,
        "description": stored["description"],
        "content": stored["content"],
    }


@pytest.mark.parametrize("track", ["memory", "skill"])
async def test_canonical_names_recommit_updates_existing_id(service: MemoryService, track: str) -> None:
    item = {"name": "project-preferences", "track": track, "description": "coffee", "content": "likes coffee"}
    first = (await service.commit_results(recall_files=[item]))["recall_files"][0]
    counter = CountingEmbeddingClient()
    service._embedding_pool._cache["embedding"] = counter
    same = (await service.commit_results(recall_files=[{**item, "name": " PROJECT__preferences "}]))["recall_files"][0]
    assert same["id"] == first["id"]
    assert same["created_at"] == first["created_at"]
    assert counter.calls == 0
    changed = (
        await service.commit_results(recall_files=[{**item, "name": "project preferences", "content": "likes tea"}])
    )["recall_files"][0]
    assert changed["id"] == first["id"]
    assert changed["content"] == "likes tea"
    assert len((await service.list_all_recall_files())["recall_files"]) == 1


@pytest.mark.parametrize(
    "name,expected",
    [
        (" Project Preferences ", "project-preferences"),
        ("project__preferences", "project-preferences"),
        ("--project---preferences--", "project-preferences"),
        ("project\t \npreferences", "project-preferences"),
        ("项目 偏好", "项目-偏好"),
        ("CAFÉ Notes", "café-notes"),
        ("ProjectPreferences", "projectpreferences"),
        ("v2-notes", "v2-notes"),
    ],
)
async def test_canonical_name_rules(service: MemoryService, name: str, expected: str) -> None:
    result = await service.commit_results(recall_files=[{"name": name, "content": "notes"}])
    assert result["recall_files"][0]["name"] == expected


async def test_canonical_name_unicode_lowercase_expansion_is_idempotent(service: MemoryService) -> None:
    first = (await service.commit_results(recall_files=[{"name": "İSTANBUL Notes", "content": "notes"}]))[
        "recall_files"
    ][0]
    assert first["name"] == "i\u0307stanbul-notes"
    second = (await service.commit_results(recall_files=[{"name": first["name"], "content": "updated notes"}]))[
        "recall_files"
    ][0]
    assert second["id"] == first["id"]
    assert second["content"] == "updated notes"
    assert len((await service.list_all_recall_files())["recall_files"]) == 1


@pytest.mark.parametrize(
    "name",
    [
        "___",
        "---",
        "project%20preferences",
        "project/preferences",
        "project\\preferences",
        "../project",
        "project.preferences",
        "notes!",
        "\u0307notes",
        "notes-\u0307",
    ],
)
async def test_canonical_name_invalid_input_writes_nothing(service: MemoryService, name: str) -> None:
    with pytest.raises(ValueError, match="recall-file name"):
        await service.commit_results(
            recall_files=[{"name": "valid", "content": "notes"}, {"name": name, "content": "bad"}],
            resource=[{"path": "/notes", "description": "notes"}],
        )
    assert (await service.list_all_recall_files())["recall_files"] == []
    assert service._get_database().resource_repo.list_resources() == {}


async def test_canonical_name_deduplication_respects_user_and_track(service: MemoryService) -> None:
    for user, track, name in [
        ("alice", "memory", "Project Preferences"),
        ("alice", "skill", "project_preferences"),
        ("bob", "memory", "project-preferences"),
    ]:
        await service.commit_results(
            recall_files=[{"name": name, "track": track, "content": user}], user={"user_id": user}
        )
    alice = (await service.list_all_recall_files(where={"user_id": "alice"}))["recall_files"]
    bob = (await service.list_all_recall_files(where={"user_id": "bob"}))["recall_files"]
    assert {(f["track"], f["name"], f["content"]) for f in alice} == {
        ("memory", "project-preferences", "alice"),
        ("skill", "project-preferences", "alice"),
    }
    assert [(f["name"], f["content"]) for f in bob] == [("project-preferences", "bob")]


async def test_canonical_names_do_not_migrate_legacy_records(service: MemoryService) -> None:
    repo = service._get_database().recall_file_repo
    legacy = repo.get_or_create_recall_file(
        name="project preferences", description="legacy", embedding=[1.0, 0.0, 0.0, 0.0], user_data={}, track="memory"
    )
    repo.update_recall_file(recall_file_id=legacy.id, content="keep the legacy content")

    canonical = (await service.commit_results(recall_files=[{"name": "project preferences", "content": "new notes"}]))[
        "recall_files"
    ][0]

    assert canonical["id"] != legacy.id
    listed = (await service.list_all_recall_files())["recall_files"]
    assert {(f["name"], f["content"]) for f in listed} == {
        ("project preferences", "keep the legacy content"),
        ("project-preferences", "new notes"),
    }


async def test_canonical_names_keep_skipping_missing_and_blank_names(service: MemoryService) -> None:
    result = await service.commit_results(recall_files=[{}, {"name": ""}, {"name": " \t\n "}])
    assert result["recall_files"] == []
    assert (await service.list_all_recall_files())["recall_files"] == []


@pytest.mark.parametrize("track", ["memory", "skill"])
async def test_canonical_name_prepare_edit_commit_round_trip(
    service: MemoryService, tmp_path: Path, track: str
) -> None:
    original = (
        await service.commit_results(recall_files=[{"name": "Project Preferences", "track": track, "content": "notes"}])
    )["recall_files"][0]
    workspace = MemorizeWorkspace(tmp_path / "workspace")
    await prepare_memorize(
        MemorizeInput(items=[MessageInput(role="user", content="hello")]),
        workspace,
        service,
        verify_command="memu verify",
    )
    path = workspace.base / track / "project-preferences.md"
    assert read_recall_file(path, track)["name"] == "project-preferences"
    path.write_text("---\nname: PROJECT preferences\ndescription: notes\n---\nupdated notes", encoding="utf-8")
    committed = (await commit_memorize(workspace, service))["recall_files"]
    assert len(committed) == 1
    assert committed[0]["id"] == original["id"]
    assert committed[0]["name"] == "project-preferences"
    await prepare_memorize(
        MemorizeInput(items=[MessageInput(role="user", content="next")]),
        workspace,
        service,
        verify_command="memu verify",
    )
    assert read_recall_file(path, track)["content"] == "updated notes"
    assert read_recall_file(path, track)["name"] == "project-preferences"
