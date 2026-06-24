from __future__ import annotations

from pathlib import Path

from memu.app import MemoryService
from memu.memory_fs import FileDescription, MemoryFileExporter, MemorySynthesizer

_MEMORY_MD = "## Profile\nThe user is a coffee enthusiast.\n\n## Preferences\nPrefers pour-over."
_SKILLS_JSON = '[{"name": "Pour Over", "body": "# Pour-over\\nUse a 1:16 ratio."}]'


class _FakeChatClient:
    """Stand-in LLM client: returns canned memory/skill responses by prompt shape."""

    async def chat(self, prompt: str, system_prompt: str | None = None) -> str:
        if "JSON array" in prompt:
            return _SKILLS_JSON
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


async def test_synthesizer_parses_memory_and_skills() -> None:
    synth = MemorySynthesizer()
    result = await synth.synthesize(_descriptions(), chat=_FakeChatClient().chat)

    assert "## Profile" in result.memory_body
    assert "pour-over" in result.memory_body.lower()
    assert result.skills == {"pour-over": "# Pour-over\nUse a 1:16 ratio."}


async def test_synthesizer_empty_when_no_descriptions() -> None:
    synth = MemorySynthesizer()
    result = await synth.synthesize([], chat=_FakeChatClient().chat)
    assert result.memory_body == ""
    assert result.skills == {}


async def test_synthesize_skills_only_decoupled_from_memory() -> None:
    """The skill bypass can be built on its own, without touching MEMORY.md."""
    synth = MemorySynthesizer()
    skills = await synth.synthesize_skills(_descriptions(), chat=_FakeChatClient().chat)
    assert skills == {"pour-over": "# Pour-over\nUse a 1:16 ratio."}


async def test_synthesize_skills_empty_without_descriptions() -> None:
    synth = MemorySynthesizer()
    assert await synth.synthesize_skills([], chat=_FakeChatClient().chat) == {}


def test_synthesizer_helpers() -> None:
    synth = MemorySynthesizer()
    assert synth._clean_markdown("```markdown\n# Hi\n```") == "# Hi"
    assert synth._parse_skills("garbage, no array") == {}
    assert synth._parse_skills("[]") == {}
    assert synth._parse_skills('[{"name": "A", "body": ""}]') == {}
    duplicate = '[{"name": "A", "body": "x"}, {"name": "A", "body": "y"}]'
    assert synth._parse_skills(duplicate) == {"a": "x", "a-2": "y"}


def test_build_synthesis_descriptions_uses_structured_items() -> None:
    """Synthesis input is sourced from extracted items, with a caption fallback."""
    from memu.database.models import MemoryItem, Resource

    res_with_items = Resource(
        id="r1", url="docs/a.txt", modality="document", local_path="a.txt", caption="raw caption a"
    )
    res_without_items = Resource(
        id="r2", url="docs/b.txt", modality="document", local_path="b.txt", caption="raw caption b"
    )
    items = [
        MemoryItem(id="i1", resource_id="r1", memory_type="knowledge", summary="Alpha fact."),
        MemoryItem(id="i2", resource_id="r1", memory_type="profile", summary="Beta trait."),
    ]

    descriptions = MemoryFileExporter.build_synthesis_descriptions([res_with_items, res_without_items], items)
    by_url = {d.url: d.description for d in descriptions}

    # r1 is composed from its structured items, not the caption.
    assert by_url["docs/a.txt"] == "[knowledge] Alpha fact.; [profile] Beta trait."
    # r2 has no items, so it falls back to the caption.
    assert by_url["docs/b.txt"] == "raw caption b"


def test_exporter_override_path(tmp_path: Path) -> None:
    service = MemoryService(
        llm_profiles={"default": {"api_key": "test-key"}},
        database_config={"metadata_store": {"provider": "inmemory"}},
    )
    exporter = MemoryFileExporter(str(tmp_path))

    result = exporter.export(
        service.database,
        memory_body="## Profile\nSynthesized.",
        skills={"brewing": "# Brewing\nbody"},
    )

    assert "MEMORY.md" in result.written
    assert "SKILL.md" in result.written
    assert "skill/brewing/SKILL.md" in result.written
    assert "Synthesized." in (tmp_path / "MEMORY.md").read_text(encoding="utf-8")
    assert "# Brewing" in (tmp_path / "skill" / "brewing" / "SKILL.md").read_text(encoding="utf-8")
    # The synthesized skill/ tree is indexed by the root SKILL.md.
    assert "skill/brewing/SKILL.md" in (tmp_path / "SKILL.md").read_text(encoding="utf-8")


async def test_service_synthesis_wiring(tmp_path: Path, monkeypatch) -> None:
    service = MemoryService(
        llm_profiles={"default": {"api_key": "test-key"}},
        database_config={"metadata_store": {"provider": "inmemory"}},
        memory_files_config={"enabled": True, "output_dir": str(tmp_path), "synthesize": True},
    )
    service.database.resource_repo.create_resource(
        url="docs/coffee.txt",
        modality="document",
        local_path="coffee.txt",
        caption="The user likes pour-over coffee.",
        embedding=None,
        user_data={"user_id": "u1"},
    )
    monkeypatch.setattr(service, "_get_llm_client", lambda *a, **k: _FakeChatClient())

    result = await service.export_memory_files(user={"user_id": "u1"})

    assert "MEMORY.md" in result["written"]
    assert "skill/pour-over/SKILL.md" in result["written"]
    memory_text = (tmp_path / "MEMORY.md").read_text(encoding="utf-8")
    assert "The user is a coffee enthusiast." in memory_text


# -- incremental update path -------------------------------------------------

_UPDATE_MEMORY_MD = "## Profile\nThe user is a coffee enthusiast.\n\n## Preferences\nLikes oat milk."
_UPDATE_SKILLS_JSON = '[{"name": "Latte Art", "body": "# Latte art\\nPour slowly."}]'


class _InitUpdateChatClient:
    """Returns init vs update payloads based on whether existing content was injected.

    The unified prompt renders ``(empty)``/``(none)`` when there is no prior artifact,
    so the presence of those sentinels marks a from-scratch (init) call.
    """

    async def chat(self, prompt: str, system_prompt: str | None = None) -> str:
        if "JSON array" in prompt:
            return _SKILLS_JSON if "(none)" in prompt else _UPDATE_SKILLS_JSON
        return _MEMORY_MD if "(empty)" in prompt else _UPDATE_MEMORY_MD


async def test_synthesizer_update_merges_into_existing() -> None:
    synth = MemorySynthesizer()
    result = await synth.synthesize(
        _descriptions(),
        existing_memory="## Profile\nOld profile.",
        existing_skills={"pour-over": "# Pour-over\nUse a 1:16 ratio."},
        chat=_InitUpdateChatClient().chat,
    )

    assert "Likes oat milk." in result.memory_body
    # Existing skill is preserved, the new one is upserted alongside it.
    assert result.skills["pour-over"] == "# Pour-over\nUse a 1:16 ratio."
    assert result.skills["latte-art"] == "# Latte art\nPour slowly."


async def test_synthesizer_update_noop_without_descriptions() -> None:
    synth = MemorySynthesizer()
    existing_skills = {"pour-over": "# Pour-over"}
    result = await synth.synthesize(
        [],
        existing_memory="## Profile\nKeep me.",
        existing_skills=existing_skills,
        chat=_InitUpdateChatClient().chat,
    )
    assert result.memory_body == "## Profile\nKeep me."
    assert result.skills == existing_skills


async def test_update_skills_only_upserts_and_preserves() -> None:
    """Skill-only incremental update keeps untouched skills and upserts new ones."""
    synth = MemorySynthesizer()
    skills = await synth.synthesize_skills(
        _descriptions(),
        existing_skills={"pour-over": "# Pour-over\nUse a 1:16 ratio."},
        chat=_InitUpdateChatClient().chat,
    )
    assert skills["pour-over"] == "# Pour-over\nUse a 1:16 ratio."
    assert skills["latte-art"] == "# Latte art\nPour slowly."


async def test_update_skills_noop_without_descriptions() -> None:
    synth = MemorySynthesizer()
    existing = {"pour-over": "# Pour-over"}
    assert await synth.synthesize_skills([], existing_skills=existing, chat=_InitUpdateChatClient().chat) == existing


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
        skills={"brewing": "# Brewing\nbody"},
    )

    assert exporter.artifacts_exist() is True
    assert exporter.read_memory_body() == "## Profile\nSynthesized body."
    assert exporter.read_skills() == {"brewing": "# Brewing\nbody"}


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

    repo = service.database.resource_repo
    repo.create_resource(
        url="docs/coffee.txt",
        modality="document",
        local_path="coffee.txt",
        caption="The user likes pour-over coffee.",
        embedding=None,
        user_data={"user_id": "u1"},
    )

    # First pass: no tree yet -> initialization from the full store.
    init = await service.export_memory_files(user={"user_id": "u1"})
    assert "skill/pour-over/SKILL.md" in init["written"]
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
    updated = await service._build_memory_files({"user_id": "u1"}, changed=[changed])

    memory_text = (tmp_path / "MEMORY.md").read_text(encoding="utf-8")
    assert "Likes oat milk." in memory_text
    assert "skill/latte-art/SKILL.md" in (updated["written"] + updated["unchanged"])
    # The originally-initialized skill survives the incremental update.
    assert (tmp_path / "skill" / "pour-over" / "SKILL.md").exists()
