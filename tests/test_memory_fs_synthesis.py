from __future__ import annotations

from pathlib import Path

from memu.app import MemoryService
from memu.memory_fs import FileDescription, MemoryFileExporter, MemorySynthesizer

_MEMORY_MD = "## Profile\nThe user is a coffee enthusiast.\n\n## Preferences\nPrefers pour-over."


class _FakeChatClient:
    """Stand-in LLM client: returns a canned memory document."""

    async def chat(self, prompt: str, system_prompt: str | None = None) -> str:
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


async def test_synthesizer_parses_memory() -> None:
    synth = MemorySynthesizer()
    memory_body = await synth.synthesize(_descriptions(), chat=_FakeChatClient().chat)

    assert "## Profile" in memory_body
    assert "pour-over" in memory_body.lower()


async def test_synthesizer_empty_when_no_descriptions() -> None:
    synth = MemorySynthesizer()
    assert await synth.synthesize([], chat=_FakeChatClient().chat) == ""


def test_synthesizer_helpers() -> None:
    synth = MemorySynthesizer()
    assert synth._clean_markdown("```markdown\n# Hi\n```") == "# Hi"


def test_build_synthesis_descriptions_uses_structured_items() -> None:
    """Synthesis input is sourced from extracted entries, with a summary fallback."""
    from memu.database.models import Entry, Resource

    res_with_items = Resource(
        id="r1", lane="source", url="docs/a.txt", modality="document", local_path="a.txt", summary="raw caption a"
    )
    res_without_items = Resource(
        id="r2", lane="source", url="docs/b.txt", modality="document", local_path="b.txt", summary="raw caption b"
    )
    items = [
        Entry(id="i1", lane="memory", source_id="r1", entry_type="knowledge", text="Alpha fact."),
        Entry(id="i2", lane="memory", source_id="r1", entry_type="profile", text="Beta trait."),
    ]

    descriptions = MemoryFileExporter.build_synthesis_descriptions([res_with_items, res_without_items], items)
    by_url = {d.url: d.description for d in descriptions}

    # r1 is composed from its structured entries, not the summary.
    assert by_url["docs/a.txt"] == "[knowledge] Alpha fact.; [profile] Beta trait."
    # r2 has no entries, so it falls back to the summary.
    assert by_url["docs/b.txt"] == "raw caption b"


def test_exporter_override_path(tmp_path: Path) -> None:
    service = MemoryService(
        llm_profiles={"default": {"api_key": "test-key"}},
        database_config={"metadata_store": {"provider": "inmemory"}},
    )
    exporter = MemoryFileExporter(str(tmp_path))

    result = exporter.export(service.database, memory_body="## Profile\nSynthesized.")

    assert "MEMORY.md" in result.written
    assert "Synthesized." in (tmp_path / "MEMORY.md").read_text(encoding="utf-8")


async def test_service_synthesis_wiring(tmp_path: Path, monkeypatch) -> None:
    service = MemoryService(
        llm_profiles={"default": {"api_key": "test-key"}},
        database_config={"metadata_store": {"provider": "inmemory"}},
        memory_files_config={"enabled": True, "output_dir": str(tmp_path), "synthesize": True},
    )
    service.database.resource_repo.create_resource(
        lane="source",
        url="docs/coffee.txt",
        modality="document",
        local_path="coffee.txt",
        summary="The user likes pour-over coffee.",
        embedding=None,
        user_data={"user_id": "u1"},
    )
    monkeypatch.setattr(service, "_get_llm_client", lambda *a, **k: _FakeChatClient())

    result = await service.export_memory_files(user={"user_id": "u1"})

    assert "MEMORY.md" in result["written"]
    memory_text = (tmp_path / "MEMORY.md").read_text(encoding="utf-8")
    assert "The user is a coffee enthusiast." in memory_text


# -- incremental update path -------------------------------------------------

_UPDATE_MEMORY_MD = "## Profile\nThe user is a coffee enthusiast.\n\n## Preferences\nLikes oat milk."


class _InitUpdateChatClient:
    """Returns init vs update payloads based on whether existing content was injected.

    The unified prompt renders ``(empty)`` when there is no prior artifact, so the
    presence of that sentinel marks a from-scratch (init) call.
    """

    async def chat(self, prompt: str, system_prompt: str | None = None) -> str:
        return _MEMORY_MD if "(empty)" in prompt else _UPDATE_MEMORY_MD


async def test_synthesizer_update_merges_into_existing() -> None:
    synth = MemorySynthesizer()
    memory_body = await synth.synthesize(
        _descriptions(),
        existing_memory="## Profile\nOld profile.",
        chat=_InitUpdateChatClient().chat,
    )

    assert "Likes oat milk." in memory_body


async def test_synthesizer_update_noop_without_descriptions() -> None:
    synth = MemorySynthesizer()
    memory_body = await synth.synthesize(
        [],
        existing_memory="## Profile\nKeep me.",
        chat=_InitUpdateChatClient().chat,
    )
    assert memory_body == "## Profile\nKeep me."


def test_exporter_read_helpers_roundtrip(tmp_path: Path) -> None:
    service = MemoryService(
        llm_profiles={"default": {"api_key": "test-key"}},
        database_config={"metadata_store": {"provider": "inmemory"}},
    )
    exporter = MemoryFileExporter(str(tmp_path))

    assert exporter.artifacts_exist() is False
    exporter.export(service.database, memory_body="## Profile\nSynthesized body.")

    assert exporter.artifacts_exist() is True
    assert exporter.read_memory_body() == "## Profile\nSynthesized body."


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
        lane="source",
        url="docs/coffee.txt",
        modality="document",
        local_path="coffee.txt",
        summary="The user likes pour-over coffee.",
        embedding=None,
        user_data={"user_id": "u1"},
    )

    # First pass: no tree yet -> initialization from the full store.
    await service.export_memory_files(user={"user_id": "u1"})
    assert "coffee enthusiast" in (tmp_path / "MEMORY.md").read_text(encoding="utf-8")

    # Second pass: tree exists -> incremental update from the changed resource only.
    changed = repo.create_resource(
        lane="source",
        url="docs/latte.txt",
        modality="document",
        local_path="latte.txt",
        summary="The user enjoys latte art and oat milk.",
        embedding=None,
        user_data={"user_id": "u1"},
    )
    await service._build_memory_files({"user_id": "u1"}, changed=[changed])

    memory_text = (tmp_path / "MEMORY.md").read_text(encoding="utf-8")
    assert "Likes oat milk." in memory_text
