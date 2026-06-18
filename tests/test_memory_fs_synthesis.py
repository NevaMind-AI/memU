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


def test_synthesizer_helpers() -> None:
    synth = MemorySynthesizer()
    assert synth._clean_markdown("```markdown\n# Hi\n```") == "# Hi"
    assert synth._parse_skills("garbage, no array") == {}
    assert synth._parse_skills("[]") == {}
    assert synth._parse_skills('[{"name": "A", "body": ""}]') == {}
    duplicate = '[{"name": "A", "body": "x"}, {"name": "A", "body": "y"}]'
    assert synth._parse_skills(duplicate) == {"a": "x", "a-2": "y"}


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
    assert "skill/brewing/SKILL.md" in result.written
    assert "Synthesized." in (tmp_path / "MEMORY.md").read_text(encoding="utf-8")
    assert "# Brewing" in (tmp_path / "skill" / "brewing" / "SKILL.md").read_text(encoding="utf-8")
    assert "[brewing](./skill/brewing/SKILL.md)" in (tmp_path / "INDEX.md").read_text(encoding="utf-8")


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
