"""Tests for the resource -> file workspace memorize path (ADR 0007 phase 1).

Exercises ``MemoryService._memorize_ws_synthesize_files`` — the two-step route +
per-file synthesis that replaces the entry plane for the chat/skill tracks — including
the ``RecallFile`` upsert and the ``resource -> file`` provenance link.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from memu.app import MemoryService

# Router output (step a): which files to update/create for a source.
_SKILL_ROUTE = '[{"op": "create", "name": "pour-over", "description": "Brew pour-over coffee"}]'
_MEMORY_ROUTE = '[{"op": "create", "name": "Preferences", "description": "User preferences"}]'
# Synthesis output (step b): the file body.
_SKILL_BODY = "# Pour-over\nUse a 1:16 ratio."


class _FakeClient:
    """Fake LLM/embed client that answers the route step and the synthesis step.

    The two steps are distinguished by a marker only the route prompt contains, so a
    single client can serve both ``chat`` calls in the workflow.
    """

    def __init__(self, route: str = _SKILL_ROUTE, body: str = _SKILL_BODY) -> None:
        self._route = route
        self._body = body

    async def chat(self, prompt: str, system_prompt: str | None = None) -> str:
        if "JSON array of operations" in prompt:
            return self._route
        return self._body

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3] for _ in texts]


def _service(tmp_path: Path) -> MemoryService:
    return MemoryService(
        llm_profiles={"default": {"api_key": "test-key"}},
        database_config={"metadata_store": {"provider": "inmemory"}},
        memory_files_config={"enabled": True, "output_dir": str(tmp_path), "synthesize": True},
    )


def _seed_resource(service: MemoryService, *, track: str, user: dict[str, Any]) -> Any:
    return service.database.resource_repo.create_resource(
        url=f"/w/{track}/x.md",
        modality="document",
        local_path=f"/w/{track}/x.md",
        caption=None,
        embedding=None,
        user_data=dict(user),
        track=track,
    )


async def _run_synthesize(
    service: MemoryService,
    client: _FakeClient,
    *,
    track: str,
    user: dict[str, Any],
    text: str = "I brewed pour-over at a 1:16 ratio.",
    resource: Any | None = None,
) -> dict:
    service._get_step_llm_client = lambda *a, **k: client  # type: ignore[method-assign]
    service._get_step_embedding_client = lambda *a, **k: client  # type: ignore[method-assign]
    res = resource if resource is not None else _seed_resource(service, track=track, user=user)
    state = {
        "resources": [res],
        "preprocessed_resources": [{"text": text, "caption": None}],
        "resource_track": track,
        "store": service.database,
        "user": user,
    }
    return await service._memorize_ws_synthesize_files(state, None)


async def test_skill_track_synthesizes_file_and_links_resource(tmp_path: Path) -> None:
    service = _service(tmp_path)
    store = service.database
    user = {"user_id": "u1"}
    res = _seed_resource(service, track="skill", user=user)

    result = await _run_synthesize(service, _FakeClient(), track="skill", user=user, resource=res)

    files = list(result["files"])
    assert len(files) == 1
    skill = files[0]
    assert skill.name == "pour-over"
    assert skill.track == "skill"
    assert skill.description == "Brew pour-over coffee"
    assert skill.content == _SKILL_BODY

    # Persisted as a skill-track RecallFile, isolated from the memory track.
    skill_files = store.recall_file_repo.list_categories(where={"user_id": "u1", "track": "skill"})
    assert [f.name for f in skill_files.values()] == ["pour-over"]
    assert store.recall_file_repo.list_categories(where={"user_id": "u1", "track": "memory"}) == {}

    # A resource -> file provenance link was recorded.
    links = store.recall_file_resource_repo.list_relations(where=user)
    assert len(links) == 1
    assert links[0].resource_id == res.id
    assert links[0].category_id == skill.id


async def test_chat_track_routes_to_memory_track_file(tmp_path: Path) -> None:
    service = _service(tmp_path)
    store = service.database
    user = {"user_id": "u1"}

    result = await _run_synthesize(
        service,
        _FakeClient(route=_MEMORY_ROUTE, body="## Preferences\nLikes strong coffee."),
        track="chat",
        user=user,
        text="I really like strong coffee.",
    )

    files = list(result["files"])
    assert len(files) == 1
    assert files[0].name == "Preferences"
    assert files[0].track == "memory"
    assert store.recall_file_repo.list_categories(where={"user_id": "u1", "track": "skill"}) == {}


async def test_update_op_revises_existing_file_by_name(tmp_path: Path) -> None:
    service = _service(tmp_path)
    store = service.database
    user: dict[str, Any] = {}

    await _run_synthesize(service, _FakeClient(), track="skill", user=user)
    # A second source updates the same skill by exact name.
    revised = _FakeClient(route='[{"op": "update", "name": "pour-over"}]', body="# Pour-over\nUpdated.")
    await _run_synthesize(service, revised, track="skill", user=user)

    skill_files = store.recall_file_repo.list_categories(where={"track": "skill"})
    assert len(skill_files) == 1  # revised in place, not duplicated
    assert next(iter(skill_files.values())).content == "# Pour-over\nUpdated."


async def test_workspace_track_is_resource_only_noop(tmp_path: Path) -> None:
    service = _service(tmp_path)
    store = service.database
    user = {"user_id": "u1"}

    result = await _run_synthesize(service, _FakeClient(), track="workspace", user=user)

    assert result["files"] == []
    assert store.recall_file_repo.list_categories(where={"user_id": "u1"}) == {}
    assert store.recall_file_resource_repo.list_relations(where=user) == []


async def test_empty_source_is_noop(tmp_path: Path) -> None:
    service = _service(tmp_path)
    store = service.database
    user = {"user_id": "u1"}

    result = await _run_synthesize(service, _FakeClient(), track="skill", user=user, text="   ")

    assert result["files"] == []
    assert store.recall_file_repo.list_categories(where={"user_id": "u1", "track": "skill"}) == {}


async def test_skill_track_creates_single_name_description_segment(tmp_path: Path) -> None:
    service = _service(tmp_path)
    store = service.database
    user = {"user_id": "u1"}

    result = await _run_synthesize(service, _FakeClient(), track="skill", user=user)
    skill = next(iter(result["files"]))

    segments = store.recall_file_segment_repo.list_segments_for_file(skill.id)
    assert len(segments) == 1
    assert segments[0].text == "name: pour-over\ndescription: Brew pour-over coffee"
    assert segments[0].embedding == [0.1, 0.2, 0.3]
    # Segment track mirrors the owning file's track (denormalized for filtering).
    assert segments[0].track == "skill"


async def test_memory_track_segments_are_lines_skipping_headings(tmp_path: Path) -> None:
    service = _service(tmp_path)
    store = service.database
    user = {"user_id": "u1"}

    result = await _run_synthesize(
        service,
        _FakeClient(route=_MEMORY_ROUTE, body="## Preferences\nLikes strong coffee.\n\nDrinks it black."),
        track="chat",
        user=user,
    )
    file = next(iter(result["files"]))

    segments = store.recall_file_segment_repo.list_segments_for_file(file.id)
    assert [s.text for s in segments] == ["Likes strong coffee.", "Drinks it black."]
    # Segment track mirrors the owning file's track (chat routes to the "memory" track).
    assert all(s.track == "memory" for s in segments)


async def test_memory_segments_drop_and_add_on_update(tmp_path: Path) -> None:
    service = _service(tmp_path)
    store = service.database
    user = {"user_id": "u1"}

    first = await _run_synthesize(
        service,
        _FakeClient(route=_MEMORY_ROUTE, body="## P\nline a\nline b"),
        track="chat",
        user=user,
    )
    file = next(iter(first["files"]))
    before = {s.text: s.id for s in store.recall_file_segment_repo.list_segments_for_file(file.id)}
    assert set(before) == {"line a", "line b"}

    # An update changes only one line: "line b" -> "line c".
    await _run_synthesize(
        service,
        _FakeClient(route='[{"op": "update", "name": "Preferences"}]', body="## P\nline a\nline c"),
        track="chat",
        user=user,
    )
    after = {s.text: s.id for s in store.recall_file_segment_repo.list_segments_for_file(file.id)}
    assert set(after) == {"line a", "line c"}
    # Unchanged line keeps its original segment (not re-embedded); changed line is fresh.
    assert after["line a"] == before["line a"]
    assert "line b" not in after


async def test_update_op_for_unknown_file_is_dropped(tmp_path: Path) -> None:
    service = _service(tmp_path)
    store = service.database
    user = {"user_id": "u1"}

    result = await _run_synthesize(
        service,
        _FakeClient(route='[{"op": "update", "name": "does-not-exist"}]'),
        track="skill",
        user=user,
    )

    assert result["files"] == []
    assert store.recall_file_repo.list_categories(where={"user_id": "u1", "track": "skill"}) == {}
