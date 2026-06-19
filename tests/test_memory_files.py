from __future__ import annotations

import json
from pathlib import Path

from memu.app import MemoryService
from memu.memory_fs import MemoryFileExporter
from memu.memory_fs.exporter import MANIFEST_NAME

# A skill-type memory item's summary is a full skill profile with frontmatter.
# The exporter parses the frontmatter for the folder slug (name) and the index
# description, and renders the body verbatim into skill/<slug>/SKILL.md.
_SKILL_PROFILE = """---
name: pour-over-brewing
description: Brew pour-over coffee at a 1:16 ratio.
category: preferences
---

# Pour-over brewing

Use a 1:16 coffee-to-water ratio for a clean cup.
"""


def _build_service(output_dir: Path) -> MemoryService:
    return MemoryService(
        llm_profiles={"default": {"api_key": "test-key"}},
        database_config={"metadata_store": {"provider": "inmemory"}},
        memory_files_config={"output_dir": str(output_dir)},
    )


def _seed(service: MemoryService, *, user: dict[str, str], source: Path | None = None) -> dict[str, str]:
    store = service.database
    # A readable local_path makes the exporter copy the raw bytes into resource/.
    if source is not None:
        source.write_text("Raw notes: the user loves pour-over coffee.\n", encoding="utf-8")
    local_path = str(source) if source is not None else "coffee.txt"
    resource = store.resource_repo.create_resource(
        url="docs/coffee.txt",
        modality="document",
        local_path=local_path,
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
    # A skill extracted during memorize drives the skill/ tree.
    skill = store.memory_item_repo.create_item(
        resource_id=resource.id,
        memory_type="skill",
        summary=_SKILL_PROFILE,
        embedding=[0.3, 0.4],
        user_data=dict(user),
    )
    return {"category_id": category.id, "resource_id": resource.id, "skill_id": skill.id}


async def test_export_writes_readme_layout(tmp_path: Path) -> None:
    service = _build_service(tmp_path / "out")
    _seed(service, user={"user_id": "u1"}, source=tmp_path / "coffee.txt")
    out = tmp_path / "out"

    result = await service.export_memory_files(user={"user_id": "u1"})

    assert result["changed"] is True
    assert "INDEX.md" in result["written"]
    assert "MEMORY.md" in result["written"]
    assert "SKILL.md" in result["written"]
    assert "skill/pour-over-brewing/SKILL.md" in result["written"]
    # The raw source file is copied verbatim and the category gets its own file.
    assert "resource/coffee.txt" in result["written"]
    assert "memory/preferences.md" in result["written"]

    memory_text = (out / "MEMORY.md").read_text(encoding="utf-8")
    # MEMORY.md is a deterministic overview that links to each category file.
    assert "## Overview" in memory_text
    assert "**Preferences**" in memory_text
    assert "memory/preferences.md" in memory_text

    # The per-category file holds the actual summary content.
    category_text = (out / "memory" / "preferences.md").read_text(encoding="utf-8")
    assert "# Preferences" in category_text
    assert "The user likes pour-over coffee." in category_text

    # The raw bytes are copied into resource/.
    raw_text = (out / "resource" / "coffee.txt").read_text(encoding="utf-8")
    assert "loves pour-over coffee" in raw_text

    index_text = (out / "INDEX.md").read_text(encoding="utf-8")
    # INDEX.md indexes the raw source files under resource/, not folders/skills.
    assert "## Files" in index_text
    assert "[`coffee.txt`](resource/coffee.txt)" in index_text
    assert "coffee preferences" in index_text
    assert "skill/pour-over" not in index_text

    # The root SKILL.md is a table of contents over the skill/ tree, driven by the
    # frontmatter parsed from each skill-type memory item.
    skill_index = (out / "SKILL.md").read_text(encoding="utf-8")
    assert "skill/pour-over-brewing/SKILL.md" in skill_index
    assert "Brew pour-over coffee at a 1:16 ratio." in skill_index

    # The skill profile is rendered verbatim into its own folder.
    skill_text = (out / "skill" / "pour-over-brewing" / "SKILL.md").read_text(encoding="utf-8")
    assert "# Pour-over brewing" in skill_text
    assert "1:16 coffee-to-water ratio" in skill_text


async def test_export_is_idempotent_until_data_changes(tmp_path: Path) -> None:
    service = _build_service(tmp_path)
    ids = _seed(service, user={"user_id": "u1"})

    first = await service.export_memory_files(user={"user_id": "u1"})
    assert first["changed"] is True

    second = await service.export_memory_files(user={"user_id": "u1"})
    assert second["changed"] is False
    assert second["written"] == []
    assert "MEMORY.md" in second["unchanged"]

    # Changing only a category summary touches its memory/<slug>.md file, but not
    # MEMORY.md (an overview of names/descriptions) or INDEX.md (a TOC).
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
    assert (tmp_path / "skill" / "pour-over-brewing" / "SKILL.md").exists()

    # Removing the skill-type memory item drops its skill folder.
    service.database.memory_item_repo.clear_items(where={"user_id": "u1"})
    result = await service.export_memory_files(user={"user_id": "u1"})

    assert "skill/pour-over-brewing/SKILL.md" in result["removed"]
    assert not (tmp_path / "skill" / "pour-over-brewing").exists()


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


def test_exporter_manifest_roundtrip(tmp_path: Path) -> None:
    exporter = MemoryFileExporter(str(tmp_path))
    exporter._save_manifest({"MEMORY.md": "abc"})
    assert exporter._load_manifest() == {"MEMORY.md": "abc"}

    (tmp_path / MANIFEST_NAME).write_text("not json", encoding="utf-8")
    assert exporter._load_manifest() == {}

    (tmp_path / MANIFEST_NAME).write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    assert exporter._load_manifest() == {}
