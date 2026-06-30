from __future__ import annotations

from pathlib import Path

from memu.app import MemoryService

# A skill-synthesis response in the per-file format: name + description + body.
_SKILLS_JSON = (
    '[{"name": "pour-over", "description": "Brew pour-over coffee", "body": "# Pour-over\\nUse a 1:16 ratio."}]'
)


class _FakeSkillClient:
    """Stand-in client exposing both chat (skill JSON) and embed (fixed vector)."""

    def __init__(self, payload: str = _SKILLS_JSON) -> None:
        self._payload = payload

    async def chat(self, prompt: str, system_prompt: str | None = None) -> str:
        return self._payload

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3] for _ in texts]


def _service(tmp_path: Path) -> MemoryService:
    return MemoryService(
        llm_profiles={"default": {"api_key": "test-key"}},
        database_config={"metadata_store": {"provider": "inmemory"}},
        memory_files_config={"enabled": True, "output_dir": str(tmp_path), "synthesize": True},
    )


async def _run_skill_step(service: MemoryService, client: _FakeSkillClient, state: dict) -> dict:
    service._get_step_llm_client = lambda *a, **k: client  # type: ignore[method-assign]
    service._get_step_embedding_client = lambda *a, **k: client  # type: ignore[method-assign]
    return await service._memorize_generate_skills(state, None)


async def test_skill_step_persists_skill_track_recall_file(tmp_path: Path) -> None:
    service = _service(tmp_path)
    store = service.database
    state = {
        "preprocessed_resources": [{"text": "I brewed pour-over at a 1:16 ratio.", "caption": None}],
        "store": store,
        "user": {"user_id": "u1"},
    }

    result = await _run_skill_step(service, _FakeSkillClient(), state)

    skills = list(result["skills"])
    assert len(skills) == 1
    skill = skills[0]
    assert skill.name == "pour-over"
    assert skill.track == "skill"
    assert skill.description == "Brew pour-over coffee"
    assert skill.content == "# Pour-over\nUse a 1:16 ratio."

    # Persisted as a skill-track RecallFile, isolated from the memory track.
    skill_files = store.recall_file_repo.list_categories(where={"user_id": "u1", "track": "skill"})
    assert [f.name for f in skill_files.values()] == ["pour-over"]
    memory_files = store.recall_file_repo.list_categories(where={"user_id": "u1", "track": "memory"})
    assert memory_files == {}


async def test_skill_step_revises_existing_skill_by_name(tmp_path: Path) -> None:
    service = _service(tmp_path)
    store = service.database
    state = {
        "preprocessed_resources": [{"text": "pour-over notes", "caption": None}],
        "store": store,
        "user": {},
    }

    await _run_skill_step(service, _FakeSkillClient(), state)
    revised = '[{"name": "pour-over", "description": "Brew pour-over coffee", "body": "# Pour-over\\nUpdated."}]'
    await _run_skill_step(service, _FakeSkillClient(revised), state)

    skill_files = store.recall_file_repo.list_categories(where={"track": "skill"})
    # Same name -> revised in place, not duplicated.
    assert len(skill_files) == 1
    assert next(iter(skill_files.values())).content == "# Pour-over\nUpdated."


async def test_skill_step_noop_when_synthesize_disabled(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.memory_files_config.synthesize = False
    store = service.database
    state = {
        "preprocessed_resources": [{"text": "pour-over notes", "caption": None}],
        "store": store,
        "user": {},
    }

    result = await _run_skill_step(service, _FakeSkillClient(), state)

    assert "skills" not in result
    assert store.recall_file_repo.list_categories(where={"track": "skill"}) == {}
