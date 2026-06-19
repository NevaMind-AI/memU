from __future__ import annotations

from pathlib import Path

from memu.app import MemoryService
from memu.memory_fs import FileDescription, MemoryFileExporter, MemorySynthesizer

_MEMORY_MD = "## Profile\nThe user is a coffee enthusiast.\n\n## Preferences\nPrefers pour-over."
_UPDATE_MEMORY_MD = "## Profile\nThe user is a coffee enthusiast.\n\n## Preferences\nLikes oat milk."


def _skill_profile(name: str, description: str, body: str) -> str:
    return f"---\nname: {name}\ndescription: {description}\ncategory: technical_skills\n---\n\n{body}\n"


class _FakeChatClient:
    """Stand-in LLM client: returns init vs update MEMORY.md bodies by prompt shape."""

    async def chat(self, prompt: str, system_prompt: str | None = None) -> str:
        if "CURRENT memory document" in prompt:
            return _UPDATE_MEMORY_MD
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


# -- MemorySynthesizer (MEMORY.md only) --------------------------------------


async def test_synthesizer_synthesizes_memory_body() -> None:
    synth = MemorySynthesizer()
    body = await synth.synthesize(_descriptions(), chat=_FakeChatClient().chat)
    assert "## Profile" in body
    assert "coffee enthusiast" in body.lower()


async def test_synthesizer_empty_when_no_descriptions() -> None:
    synth = MemorySynthesizer()
    assert await synth.synthesize([], chat=_FakeChatClient().chat) == ""


async def test_synthesizer_update_merges_into_existing() -> None:
    synth = MemorySynthesizer()
    body = await synth.update(
        _descriptions(),
        existing_memory="## Profile\nOld profile.",
        chat=_FakeChatClient().chat,
    )
    assert "Likes oat milk." in body


async def test_synthesizer_update_noop_without_descriptions() -> None:
    synth = MemorySynthesizer()
    body = await synth.update([], existing_memory="## Profile\nKeep me.", chat=_FakeChatClient().chat)
    assert body == "## Profile\nKeep me."


def test_synthesizer_cleans_code_fences() -> None:
    synth = MemorySynthesizer()
    assert synth._clean_markdown("```markdown\n# Hi\n```") == "# Hi"


# -- skill/ rendered from skill-type memory items ----------------------------


def _seed_skill(service: MemoryService, *, name: str, description: str, body: str, user: dict[str, str]) -> None:
    resource = service.database.resource_repo.create_resource(
        url=f"docs/{name}.txt",
        modality="document",
        local_path=f"{name}.txt",
        caption=f"Source for {name}.",
        embedding=None,
        user_data=dict(user),
    )
    service.database.memory_item_repo.create_item(
        resource_id=resource.id,
        memory_type="skill",
        summary=_skill_profile(name, description, body),
        embedding=[0.1, 0.2],
        user_data=dict(user),
    )


def _service(tmp_path: Path, **memory_files: object) -> MemoryService:
    return MemoryService(
        llm_profiles={"default": {"api_key": "test-key"}},
        database_config={"metadata_store": {"provider": "inmemory"}},
        memory_files_config={"output_dir": str(tmp_path), **memory_files},
    )


async def test_export_renders_skill_tree_from_items(tmp_path: Path) -> None:
    service = _service(tmp_path)
    _seed_skill(
        service,
        name="canary-deployment",
        description="Gradually shift traffic with monitoring.",
        body="# Canary deployment\nShift traffic slowly.",
        user={"user_id": "u1"},
    )

    result = await service.export_memory_files(user={"user_id": "u1"})

    assert "skill/canary-deployment/SKILL.md" in result["written"]
    skill_text = (tmp_path / "skill" / "canary-deployment" / "SKILL.md").read_text(encoding="utf-8")
    assert "# Canary deployment" in skill_text
    index_text = (tmp_path / "SKILL.md").read_text(encoding="utf-8")
    assert "Gradually shift traffic with monitoring." in index_text


def test_exporter_parses_frontmatter_and_dedupes_slugs(tmp_path: Path) -> None:
    service = MemoryService(
        llm_profiles={"default": {"api_key": "test-key"}},
        database_config={"metadata_store": {"provider": "inmemory"}},
    )
    exporter = MemoryFileExporter(str(tmp_path))

    # No frontmatter -> name/description fall back to derived values.
    assert exporter._parse_skill_frontmatter("# Just a heading\nbody") == ("", "")
    name, description = exporter._parse_skill_frontmatter(_skill_profile("brew", "Brew coffee.", "body"))
    assert name == "brew"
    assert description == "Brew coffee."

    items = [
        service.database.memory_item_repo.create_item(
            resource_id="r1",
            memory_type="skill",
            summary=_skill_profile("brew", "Brew coffee.", "first"),
            embedding=[0.1],
            user_data={},
        ),
        service.database.memory_item_repo.create_item(
            resource_id="r2",
            memory_type="skill",
            summary=_skill_profile("brew", "Brew tea too.", "second"),
            embedding=[0.1],
            user_data={},
        ),
        service.database.memory_item_repo.create_item(
            resource_id="r3",
            memory_type="event",
            summary="not a skill",
            embedding=[0.1],
            user_data={},
        ),
    ]
    skills = exporter._skills_from_items(items)
    assert set(skills) == {"brew", "brew-2"}


def test_exporter_memory_body_override(tmp_path: Path) -> None:
    service = MemoryService(
        llm_profiles={"default": {"api_key": "test-key"}},
        database_config={"metadata_store": {"provider": "inmemory"}},
    )
    exporter = MemoryFileExporter(str(tmp_path))

    result = exporter.export(service.database, memory_body="## Profile\nSynthesized.")

    assert "MEMORY.md" in result.written
    assert "Synthesized." in (tmp_path / "MEMORY.md").read_text(encoding="utf-8")
    # No skill items -> the root SKILL.md is still written as an empty index.
    assert "SKILL.md" in result.written
    assert "_No skills yet._" in (tmp_path / "SKILL.md").read_text(encoding="utf-8")


def test_exporter_read_memory_body_roundtrip(tmp_path: Path) -> None:
    service = MemoryService(
        llm_profiles={"default": {"api_key": "test-key"}},
        database_config={"metadata_store": {"provider": "inmemory"}},
    )
    exporter = MemoryFileExporter(str(tmp_path))

    assert exporter.artifacts_exist() is False
    exporter.export(service.database, memory_body="## Profile\nSynthesized body.")

    assert exporter.artifacts_exist() is True
    assert exporter.read_memory_body() == "## Profile\nSynthesized body."


# -- service synthesis wiring ------------------------------------------------


async def test_service_synthesis_wiring(tmp_path: Path, monkeypatch) -> None:
    service = _service(tmp_path, synthesize=True)
    _seed_skill(
        service,
        name="pour-over",
        description="Brew pour-over coffee.",
        body="# Pour-over\nUse a 1:16 ratio.",
        user={"user_id": "u1"},
    )
    monkeypatch.setattr(service, "_get_llm_client", lambda *a, **k: _FakeChatClient())

    result = await service.export_memory_files(user={"user_id": "u1"})

    assert "MEMORY.md" in result["written"]
    assert "skill/pour-over/SKILL.md" in result["written"]
    memory_text = (tmp_path / "MEMORY.md").read_text(encoding="utf-8")
    assert "The user is a coffee enthusiast." in memory_text


async def test_service_init_then_update(tmp_path: Path, monkeypatch) -> None:
    service = _service(tmp_path, synthesize=True)
    monkeypatch.setattr(service, "_get_llm_client", lambda *a, **k: _FakeChatClient())

    _seed_skill(
        service,
        name="pour-over",
        description="Brew pour-over coffee.",
        body="# Pour-over\nUse a 1:16 ratio.",
        user={"user_id": "u1"},
    )

    # First pass: no tree yet -> initialization synthesizes the MEMORY.md body.
    init = await service.export_memory_files(user={"user_id": "u1"})
    assert "skill/pour-over/SKILL.md" in init["written"]
    assert "coffee enthusiast" in (tmp_path / "MEMORY.md").read_text(encoding="utf-8")

    # Second pass: tree exists -> incremental MEMORY.md update from the changed resource.
    changed = service.database.resource_repo.create_resource(
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
    # The skill folder, rebuilt from the persisted skill item, survives.
    assert (tmp_path / "skill" / "pour-over" / "SKILL.md").exists()
    assert "MEMORY.md" in (updated["written"] + updated["unchanged"])
