from __future__ import annotations

import json
from pathlib import Path

import pytest

from memu.app import MemoryService
from memu.memory_fs import MemoryFileExporter
from memu.memory_fs.exporter import MANIFEST_NAME

# With synthesize=False (the default) the whole tree is LLM-free: MEMORY.md is
# rendered from category summaries and the skill/ tree from the deterministic
# bypass over extracted skill-type memory items. This body seeds one such item.
_SKILL_BODY = "---\nname: pour-over\n---\n# Pour-over brewing\nUse a 1:16 ratio."


def _build_service(output_dir: Path) -> MemoryService:
    return MemoryService(
        llm_profiles={"default": {"api_key": "test-key"}},
        database_config={"metadata_store": {"provider": "inmemory"}},
        memory_files_config={"enabled": True, "output_dir": str(output_dir)},
    )


def _seed(service: MemoryService, *, user: dict[str, str]) -> dict[str, str]:
    store = service.database
    resource = store.resource_repo.create_resource(
        url="docs/coffee.txt",
        modality="document",
        local_path="coffee.txt",
        caption="Notes about the user's coffee preferences.",
        embedding=None,
        user_data=dict(user),
    )
    category = store.memory_category_repo.get_or_create_category(
        name="Preferences",
        description="User preferences, likes and dislikes",
        embedding=[0.1, 0.2],
        user_data=dict(user),
    )
    store.memory_category_repo.update_category(category_id=category.id, summary="The user likes pour-over coffee.")
    skill = store.memory_item_repo.create_item(
        resource_id=resource.id,
        memory_type="skill",
        summary=_SKILL_BODY,
        embedding=[0.1, 0.2],
        user_data=dict(user),
    )
    store.category_item_repo.link_item_category(skill.id, category.id, user_data=dict(user))
    return {"category_id": category.id, "resource_id": resource.id, "skill_id": skill.id}


async def test_export_writes_readme_layout(tmp_path: Path) -> None:
    service = _build_service(tmp_path)
    _seed(service, user={"user_id": "u1"})

    result = await service.export_memory_files(user={"user_id": "u1"})

    assert result["changed"] is True
    assert "INDEX.md" in result["written"]
    assert "MEMORY.md" in result["written"]
    assert "SKILL.md" in result["written"]
    assert "memory/preferences.md" in result["written"]
    assert "skill/pour-over/SKILL.md" in result["written"]

    # MEMORY.md is now an overview that links to each memory/<slug>.md file; the
    # category summary itself lives in memory/preferences.md.
    memory_text = (tmp_path / "MEMORY.md").read_text(encoding="utf-8")
    assert "**Preferences**" in memory_text
    assert "memory/preferences.md" in memory_text

    category_text = (tmp_path / "memory" / "preferences.md").read_text(encoding="utf-8")
    assert "The user likes pour-over coffee." in category_text

    # INDEX.md indexes the raw source files under resource/.
    index_text = (tmp_path / "INDEX.md").read_text(encoding="utf-8")
    assert "coffee.txt" in index_text
    assert "coffee preferences" in index_text

    # The root SKILL.md indexes the synthesized skill/ tree.
    skill_index = (tmp_path / "SKILL.md").read_text(encoding="utf-8")
    assert "skill/pour-over/SKILL.md" in skill_index

    skill_text = (tmp_path / "skill" / "pour-over" / "SKILL.md").read_text(encoding="utf-8")
    assert "Pour-over brewing" in skill_text


async def test_export_is_idempotent_until_data_changes(tmp_path: Path) -> None:
    service = _build_service(tmp_path)
    ids = _seed(service, user={"user_id": "u1"})

    first = await service.export_memory_files(user={"user_id": "u1"})
    assert first["changed"] is True

    second = await service.export_memory_files(user={"user_id": "u1"})
    assert second["changed"] is False
    assert second["written"] == []
    assert "MEMORY.md" in second["unchanged"]

    # Changing only a folder summary rewrites that category's memory/<slug>.md but
    # not MEMORY.md (an overview of links) nor INDEX.md (a file TOC).
    service.database.memory_category_repo.update_category(
        category_id=ids["category_id"],
        summary="The user now prefers espresso.",
    )
    third = await service.export_memory_files(user={"user_id": "u1"})
    assert third["changed"] is True
    assert "memory/preferences.md" in third["written"]
    assert "MEMORY.md" in third["unchanged"]
    assert "INDEX.md" in third["unchanged"]


async def test_export_removes_stale_skill_and_prunes_dirs(tmp_path: Path) -> None:
    service = _build_service(tmp_path)
    _seed(service, user={"user_id": "u1"})

    await service.export_memory_files(user={"user_id": "u1"})
    assert (tmp_path / "skill" / "pour-over" / "SKILL.md").exists()

    # Dropping the skill-type item removes it from the bypass, so its doc goes stale.
    service.database.memory_item_repo.clear_items(where={"user_id": "u1"})
    result = await service.export_memory_files(user={"user_id": "u1"})

    assert "skill/pour-over/SKILL.md" in result["removed"]
    assert not (tmp_path / "skill" / "pour-over").exists()


async def test_export_respects_user_scope(tmp_path: Path) -> None:
    service = _build_service(tmp_path)
    _seed(service, user={"user_id": "u1"})
    service.database.memory_category_repo.get_or_create_category(
        name="Secret",
        description="Other user's folder",
        embedding=[0.3, 0.4],
        user_data={"user_id": "u2"},
    )

    await service.export_memory_files(user={"user_id": "u1"})

    memory_text = (tmp_path / "MEMORY.md").read_text(encoding="utf-8")
    assert "Preferences" in memory_text
    assert "Secret" not in memory_text


async def test_export_disabled_raises(tmp_path: Path) -> None:
    service = MemoryService(
        llm_profiles={"default": {"api_key": "test-key"}},
        database_config={"metadata_store": {"provider": "inmemory"}},
    )
    with pytest.raises(RuntimeError, match="disabled"):
        await service.export_memory_files(user={"user_id": "u1"})


def test_skill_name_from_frontmatter_and_fallbacks(tmp_path: Path) -> None:
    exporter = MemoryFileExporter(str(tmp_path))
    assert exporter._skill_name("---\nname: My Skill\n---\nbody", fallback="x") == "my-skill"
    assert exporter._skill_name("# Heading Title\nbody", fallback="x") == "heading-title"
    assert exporter._skill_name("plain text only", fallback="skill-abc123") == "skill-abc123"


def test_exporter_manifest_roundtrip(tmp_path: Path) -> None:
    exporter = MemoryFileExporter(str(tmp_path))
    exporter._save_manifest({"MEMORY.md": "abc"})
    assert exporter._load_manifest() == {"MEMORY.md": "abc"}

    (tmp_path / MANIFEST_NAME).write_text("not json", encoding="utf-8")
    assert exporter._load_manifest() == {}

    (tmp_path / MANIFEST_NAME).write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    assert exporter._load_manifest() == {}
