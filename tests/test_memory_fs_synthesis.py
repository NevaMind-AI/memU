from __future__ import annotations

from pathlib import Path

from memu.app import MemoryService
from memu.memory_fs import FileDescription, MemoryFileExporter, MemorySynthesizer

_MEMORY_MD = "## Profile\nThe user is a coffee enthusiast.\n\n## Preferences\nPrefers pour-over."
_SKILL_OVERVIEW = "## Brewing\nThe agent can brew pour-over coffee."


class _FakeChatClient:
    """Stand-in LLM client: returns a canned memory- or skill-overview document.

    The skill-overview prompt is the only one that lists "SKILLS in the library", so
    its presence distinguishes the two synthesis calls.
    """

    async def chat(self, prompt: str, system_prompt: str | None = None) -> str:
        if "SKILLS in the library" in prompt:
            return _SKILL_OVERVIEW
        return _MEMORY_MD


def _descriptions() -> list[FileDescription]:
    return [
        FileDescription(
            url="docs/coffee.txt",
            modality="document",
            description="The user likes pour-over coffee with a 1:16 ratio.",
            resource_id="r1",
        )
    ]


def _skill_files() -> list:
    from memu.database.models import RecallFile

    return [
        RecallFile(
            id="s1",
            name="pour-over",
            description="Brew pour-over",
            content="# Pour-over\nUse a 1:16 ratio.",
            track="skill",
        )
    ]


async def test_synthesize_memory_from_descriptions() -> None:
    synth = MemorySynthesizer()
    body = await synth.synthesize_memory(_descriptions(), chat=_FakeChatClient().chat)
    assert "## Profile" in body
    assert "pour-over" in body.lower()


async def test_synthesize_memory_empty_without_descriptions() -> None:
    synth = MemorySynthesizer()
    assert await synth.synthesize_memory([], chat=_FakeChatClient().chat) == ""
    assert await synth.synthesize_memory([], existing_memory="## Keep", chat=_FakeChatClient().chat) == "## Keep"


async def test_synthesize_skill_overview_from_skill_files() -> None:
    synth = MemorySynthesizer()
    body = await synth.synthesize_skill_overview(_skill_files(), chat=_FakeChatClient().chat)
    assert body == _SKILL_OVERVIEW


async def test_synthesize_skill_overview_empty_without_skills() -> None:
    synth = MemorySynthesizer()
    assert await synth.synthesize_skill_overview([], chat=_FakeChatClient().chat) == ""
    assert await synth.synthesize_skill_overview([], existing_skill="## Keep", chat=_FakeChatClient().chat) == "## Keep"


def test_synthesizer_helpers() -> None:
    synth = MemorySynthesizer()
    assert synth._clean_markdown("```markdown\n# Hi\n```") == "# Hi"
    # Skills are formatted as "## name\nbody" blocks; empty-content skills are dropped.
    from memu.database.models import RecallFile

    formatted = synth._format_skills([
        RecallFile(id="a", name="b-skill", description="", content="body-b", track="skill"),
        RecallFile(id="c", name="a-skill", description="", content="", track="skill"),
    ])
    assert formatted == "## b-skill\nbody-b"


def test_build_synthesis_descriptions_uses_structured_items() -> None:
    """Synthesis input is sourced from extracted items, with a caption fallback."""
    from memu.database.models import RecallEntry, Resource

    res_with_items = Resource(
        id="r1", url="docs/a.txt", modality="document", local_path="a.txt", caption="raw caption a"
    )
    res_without_items = Resource(
        id="r2", url="docs/b.txt", modality="document", local_path="b.txt", caption="raw caption b"
    )
    items = [
        RecallEntry(id="i1", resource_id="r1", memory_type="knowledge", summary="Alpha fact."),
        RecallEntry(id="i2", resource_id="r1", memory_type="profile", summary="Beta trait."),
    ]

    descriptions = MemoryFileExporter.build_synthesis_descriptions([res_with_items, res_without_items], items)
    by_url = {d.url: d.description for d in descriptions}

    # r1 is composed from its structured items, not the caption.
    assert by_url["docs/a.txt"] == "[knowledge] Alpha fact.; [profile] Beta trait."
    # r2 has no items, so it falls back to the caption.
    assert by_url["docs/b.txt"] == "raw caption b"


def _seed_skill(service: MemoryService, *, user: dict[str, str]) -> None:
    """Persist one memory category and one skill-track file in scope."""
    store = service.database
    store.resource_repo.create_resource(
        url="docs/coffee.txt",
        modality="document",
        local_path="coffee.txt",
        caption="The user likes pour-over coffee.",
        embedding=None,
        user_data=dict(user),
    )
    skill = store.recall_file_repo.get_or_create_category(
        name="pour-over",
        description="Brew pour-over coffee",
        embedding=[0.1, 0.2],
        user_data=dict(user),
        track="skill",
    )
    store.recall_file_repo.update_category(category_id=skill.id, content="# Pour-over\nUse a 1:16 ratio.")


def test_exporter_override_path(tmp_path: Path) -> None:
    service = MemoryService(
        llm_profiles={"default": {"api_key": "test-key"}},
        database_config={"metadata_store": {"provider": "inmemory"}},
    )
    _seed_skill(service, user={})
    exporter = MemoryFileExporter(str(tmp_path))

    result = exporter.export(
        service.database,
        memory_body="## Profile\nSynthesized.",
        skill_body="## Brewing\nOverview body.",
    )

    assert "MEMORY.md" in result.written
    assert "SKILL.md" in result.written
    # The skill/ tree mirrors memory/: one file per skill-track RecallFile.
    assert "skill/pour-over.md" in result.written
    assert "Synthesized." in (tmp_path / "MEMORY.md").read_text(encoding="utf-8")
    assert "Overview body." in (tmp_path / "SKILL.md").read_text(encoding="utf-8")
    assert "Use a 1:16 ratio." in (tmp_path / "skill" / "pour-over.md").read_text(encoding="utf-8")


async def test_service_synthesis_wiring(tmp_path: Path, monkeypatch) -> None:
    service = MemoryService(
        llm_profiles={"default": {"api_key": "test-key"}},
        database_config={"metadata_store": {"provider": "inmemory"}},
        memory_files_config={"enabled": True, "output_dir": str(tmp_path), "synthesize": True},
    )
    _seed_skill(service, user={"user_id": "u1"})
    monkeypatch.setattr(service, "_get_llm_client", lambda *a, **k: _FakeChatClient())

    result = await service.export_memory_files(user={"user_id": "u1"})

    assert "MEMORY.md" in result["written"]
    assert "skill/pour-over.md" in result["written"]
    memory_text = (tmp_path / "MEMORY.md").read_text(encoding="utf-8")
    assert "The user is a coffee enthusiast." in memory_text
    skill_text = (tmp_path / "SKILL.md").read_text(encoding="utf-8")
    assert "The agent can brew pour-over coffee." in skill_text


# -- incremental update path -------------------------------------------------

_UPDATE_MEMORY_MD = "## Profile\nThe user is a coffee enthusiast.\n\n## Preferences\nLikes oat milk."


class _InitUpdateChatClient:
    """Returns init vs update payloads based on whether existing content was injected.

    The unified prompt renders ``(empty)`` when there is no prior artifact, so the
    presence of that sentinel marks a from-scratch (init) call.
    """

    async def chat(self, prompt: str, system_prompt: str | None = None) -> str:
        if "SKILLS in the library" in prompt:
            return _SKILL_OVERVIEW
        return _MEMORY_MD if "(empty)" in prompt else _UPDATE_MEMORY_MD


async def test_synthesize_memory_update_merges_into_existing() -> None:
    synth = MemorySynthesizer()
    body = await synth.synthesize_memory(
        _descriptions(),
        existing_memory="## Profile\nOld profile.",
        chat=_InitUpdateChatClient().chat,
    )
    assert "Likes oat milk." in body


def test_exporter_read_helpers_roundtrip(tmp_path: Path) -> None:
    service = MemoryService(
        llm_profiles={"default": {"api_key": "test-key"}},
        database_config={"metadata_store": {"provider": "inmemory"}},
    )
    exporter = MemoryFileExporter(str(tmp_path))

    assert exporter.artifacts_exist() is False
    exporter.export(
        service.database,
        memory_body="## Profile\nSynthesized body.",
        skill_body="## Skills\nSkill overview body.",
    )

    assert exporter.artifacts_exist() is True
    assert exporter.read_memory_body() == "## Profile\nSynthesized body."
    assert exporter.read_skill_body() == "## Skills\nSkill overview body."


async def test_service_init_then_update(tmp_path: Path, monkeypatch) -> None:
    service = MemoryService(
        llm_profiles={"default": {"api_key": "test-key"}},
        database_config={"metadata_store": {"provider": "inmemory"}},
        memory_files_config={
            "enabled": True,
            "output_dir": str(tmp_path),
            "synthesize": True,
        },
    )
    monkeypatch.setattr(service, "_get_llm_client", lambda *a, **k: _InitUpdateChatClient())
    _seed_skill(service, user={"user_id": "u1"})

    repo = service.database.resource_repo

    # First pass: no tree yet -> initialization from the full store.
    init = await service.export_memory_files(user={"user_id": "u1"})
    assert "skill/pour-over.md" in init["written"]
    assert "coffee enthusiast" in (tmp_path / "MEMORY.md").read_text(encoding="utf-8")

    # Second pass: tree exists -> incremental update from the changed resource only.
    changed = repo.create_resource(
        url="docs/latte.txt",
        modality="document",
        local_path="latte.txt",
        caption="The user enjoys latte art and oat milk.",
        embedding=None,
        user_data={"user_id": "u1"},
    )
    await service._build_memory_files({"user_id": "u1"}, changed=[changed])

    memory_text = (tmp_path / "MEMORY.md").read_text(encoding="utf-8")
    assert "Likes oat milk." in memory_text
    # The skill file persists across the incremental update.
    assert (tmp_path / "skill" / "pour-over.md").exists()
