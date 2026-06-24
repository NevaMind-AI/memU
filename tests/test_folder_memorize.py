"""Tests for the workspace memorize backbone: scanning, diffing, cascade sync.

Covers ``memu.blob.folder`` plus the additive ``MemoryService.memorize_workspace``
entry point. The single-file ``memorize`` is intentionally untouched and is not
exercised here. Export of the memory file tree is added in a later step, so these
tests stay focused on scan -> diff -> cascade -> manifest.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from memu.app import MemoryService
from memu.blob.folder import (
    MANIFEST_FILENAME,
    diff_folder,
    infer_modality,
    load_manifest,
    manifest_from_scan,
    save_manifest,
    scan_folder,
)

# -- folder module: scan / modality / manifest / diff ------------------------


def test_infer_modality_by_extension() -> None:
    assert infer_modality("a.json") == "conversation"
    assert infer_modality("a.txt") == "document"
    assert infer_modality("a.MD") == "document"
    assert infer_modality("a.png") == "image"
    assert infer_modality("a.mp4") == "video"
    assert infer_modality("a.mp3") == "audio"
    assert infer_modality("a.unknownext") is None


def test_scan_folder_recurses_skips_unknown_and_hidden(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("alpha", encoding="utf-8")
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "b.md").write_text("beta", encoding="utf-8")
    (tmp_path / "skip.bin").write_text("binary", encoding="utf-8")  # unknown ext
    (tmp_path / ".hidden.txt").write_text("hidden", encoding="utf-8")  # hidden file
    (tmp_path / MANIFEST_FILENAME).write_text("{}", encoding="utf-8")  # manifest

    scanned = scan_folder(tmp_path)

    assert set(scanned) == {"a.txt", "nested/b.md"}
    assert scanned["a.txt"].modality == "document"
    assert scanned["nested/b.md"].modality == "document"
    assert scanned["a.txt"].content_hash != scanned["nested/b.md"].content_hash


def test_manifest_roundtrip_and_diff(tmp_path: Path) -> None:
    (tmp_path / "keep.txt").write_text("keep", encoding="utf-8")
    (tmp_path / "change.txt").write_text("v1", encoding="utf-8")
    (tmp_path / "gone.txt").write_text("bye", encoding="utf-8")

    first = scan_folder(tmp_path)
    save_manifest(tmp_path, manifest_from_scan(first))
    assert load_manifest(tmp_path) == manifest_from_scan(first)

    # Mutate the folder: modify one file, delete another, add a new one.
    (tmp_path / "change.txt").write_text("v2", encoding="utf-8")
    (tmp_path / "gone.txt").unlink()
    (tmp_path / "new.md").write_text("fresh", encoding="utf-8")

    second = scan_folder(tmp_path)
    diff = diff_folder(second, load_manifest(tmp_path))

    assert [f.rel_path for f in diff.added] == ["new.md"]
    assert [f.rel_path for f in diff.modified] == ["change.txt"]
    assert diff.deleted == ["gone.txt"]
    assert diff.has_changes and diff.has_removals


def test_diff_added_only_has_no_removals(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    diff = diff_folder(scan_folder(tmp_path), {})
    assert [f.rel_path for f in diff.added] == ["a.txt"]
    assert not diff.has_removals


# -- service-level: cascade delete & orchestration ---------------------------


def _service() -> MemoryService:
    return MemoryService(
        llm_profiles={"default": {"api_key": "test-key"}},
        database_config={"metadata_store": {"provider": "inmemory"}},
    )


def _seed_resource_with_item(service: MemoryService, *, url: str, category_id: str, user: dict[str, Any]) -> str:
    """Create a resource + one item + one relation, returning the resource id."""
    store = service.database
    res = store.resource_repo.create_resource(
        url=url,
        modality="document",
        local_path=url,
        caption="cap",
        embedding=None,
        user_data=dict(user),
    )
    item = store.memory_item_repo.create_item(
        resource_id=res.id,
        memory_type="profile",
        summary=f"summary for {url}",
        embedding=[0.0],
        user_data=dict(user),
    )
    store.category_item_repo.link_item_category(item.id, category_id, dict(user))
    return res.id


async def test_cascade_delete_removes_resource_items_relations(monkeypatch) -> None:
    service = _service()
    store = service.database
    user = {"user_id": "u1"}
    ctx = service._get_context()
    category_id = "cat-1"

    keep_id = _seed_resource_with_item(service, url="/folder/keep.txt", category_id=category_id, user=user)
    drop_id = _seed_resource_with_item(service, url="/folder/drop.txt", category_id=category_id, user=user)

    patched: list[dict[str, Any]] = []

    async def _fake_patch(updates, *, ctx, store, llm_client=None) -> None:
        patched.append(updates)

    monkeypatch.setattr(service, "_patch_category_summaries", _fake_patch)

    removed = await service._cascade_delete_by_urls({"/folder/drop.txt"}, ctx=ctx, store=store, user_scope=user)

    assert [r.id for r in removed] == [drop_id]
    remaining = store.resource_repo.list_resources(where=user)
    assert keep_id in remaining
    assert drop_id not in remaining
    # The dropped resource's item and relation are gone; the kept one's survive.
    items = store.memory_item_repo.list_items(where=user)
    assert all(it.resource_id == keep_id for it in items.values())
    relations = store.category_item_repo.list_relations(where=user)
    assert len(relations) == 1
    # Discarded content was fed to the summary recompute as (before, None).
    assert patched and category_id in patched[0]
    assert patched[0][category_id][1] is None


async def test_memorize_workspace_sync_add_modify_delete(tmp_path: Path, monkeypatch) -> None:
    service = _service()
    store = service.database
    user = {"user_id": "u1"}

    # Avoid LLM-dependent paths; exercise scan -> diff -> cascade -> manifest.
    async def _noop_categories(*a, **k) -> None:
        return None

    async def _noop_patch(updates, *, ctx, store, llm_client=None) -> None:
        return None

    async def _fake_memorize_one(*, resource_url, modality, user_scope, ctx, store) -> dict[str, Any]:
        res = store.resource_repo.create_resource(
            url=resource_url,
            modality=modality,
            local_path=resource_url,
            caption="cap",
            embedding=None,
            user_data=dict(user_scope or {}),
        )
        store.memory_item_repo.create_item(
            resource_id=res.id,
            memory_type="profile",
            summary=f"summary {resource_url}",
            embedding=[0.0],
            user_data=dict(user_scope or {}),
        )
        return {"resources": [res], "response": {"items": [{"summary": "x"}]}}

    monkeypatch.setattr(service, "_ensure_categories_ready", _noop_categories)
    monkeypatch.setattr(service, "_patch_category_summaries", _noop_patch)
    monkeypatch.setattr(service, "_memorize_one", _fake_memorize_one)

    (tmp_path / "a.txt").write_text("a-v1", encoding="utf-8")
    (tmp_path / "b.md").write_text("b-v1", encoding="utf-8")

    # First sync: both files added.
    first = await service.memorize_workspace(folder=str(tmp_path), user=user)
    assert sorted(first["added"]) == ["a.txt", "b.md"]
    assert first["modified"] == [] and first["deleted"] == []
    assert len(store.resource_repo.list_resources(where=user)) == 2
    # Manifest persisted in the folder.
    manifest_path = tmp_path / MANIFEST_FILENAME
    assert manifest_path.exists()
    assert set(json.loads(manifest_path.read_text(encoding="utf-8"))) == {"a.txt", "b.md"}

    # Second sync: modify a.txt, delete b.md, add c.txt.
    (tmp_path / "a.txt").write_text("a-v2", encoding="utf-8")
    (tmp_path / "b.md").unlink()
    (tmp_path / "c.txt").write_text("c-v1", encoding="utf-8")

    second = await service.memorize_workspace(folder=str(tmp_path), user=user)
    assert second["added"] == ["c.txt"]
    assert second["modified"] == ["a.txt"]
    assert second["deleted"] == ["b.md"]

    root = tmp_path.resolve()
    urls = {r.url for r in store.resource_repo.list_resources(where=user).values()}
    assert urls == {str(root / "a.txt"), str(root / "c.txt")}
    assert set(json.loads(manifest_path.read_text(encoding="utf-8"))) == {"a.txt", "c.txt"}


async def test_memorize_workspace_exports_when_enabled(tmp_path: Path, monkeypatch) -> None:
    """When memory files are enabled, a workspace sync refreshes the markdown tree."""
    out_dir = tmp_path / "out"
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    service = MemoryService(
        llm_profiles={"default": {"api_key": "test-key"}},
        database_config={"metadata_store": {"provider": "inmemory"}},
        memory_files_config={"enabled": True, "output_dir": str(out_dir)},
    )
    user = {"user_id": "u1"}

    async def _noop_categories(*a, **k) -> None:
        return None

    async def _fake_memorize_one(*, resource_url, modality, user_scope, ctx, store) -> dict[str, Any]:
        res = store.resource_repo.create_resource(
            url=resource_url,
            modality=modality,
            local_path=resource_url,
            caption="cap",
            embedding=None,
            user_data=dict(user_scope or {}),
        )
        return {"resources": [res], "response": {"items": []}}

    exported: list[Any] = []
    real_export = service._memory_file_exporter.export

    def _spy_export(database, *, where=None, **kwargs):
        exported.append(where)
        return real_export(database, where=where, **kwargs)

    monkeypatch.setattr(service, "_ensure_categories_ready", _noop_categories)
    monkeypatch.setattr(service, "_memorize_one", _fake_memorize_one)
    monkeypatch.setattr(service._memory_file_exporter, "export", _spy_export)

    (src_dir / "a.txt").write_text("hello", encoding="utf-8")
    await service.memorize_workspace(folder=str(src_dir), user=user)

    # Export ran (scoped to the user) and produced the root index on disk.
    assert exported == [user]
    assert (out_dir / "INDEX.md").exists()


async def test_memorize_workspace_export_failure_does_not_fail_sync(tmp_path: Path, monkeypatch) -> None:
    """An export error is best-effort: the sync still completes and persists state."""
    service = MemoryService(
        llm_profiles={"default": {"api_key": "test-key"}},
        database_config={"metadata_store": {"provider": "inmemory"}},
        memory_files_config={"enabled": True, "output_dir": str(tmp_path / "out")},
    )
    user = {"user_id": "u1"}

    async def _noop_categories(*a, **k) -> None:
        return None

    async def _fake_memorize_one(*, resource_url, modality, user_scope, ctx, store) -> dict[str, Any]:
        res = store.resource_repo.create_resource(
            url=resource_url,
            modality=modality,
            local_path=resource_url,
            caption="cap",
            embedding=None,
            user_data=dict(user_scope or {}),
        )
        return {"resources": [res], "response": {"items": []}}

    def _boom(database, *, where=None, **kwargs):
        raise RuntimeError("export blew up")  # noqa: TRY003

    monkeypatch.setattr(service, "_ensure_categories_ready", _noop_categories)
    monkeypatch.setattr(service, "_memorize_one", _fake_memorize_one)
    monkeypatch.setattr(service._memory_file_exporter, "export", _boom)

    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
    result = await service.memorize_workspace(folder=str(tmp_path), user=user)

    assert result["added"] == ["a.txt"]
    assert (tmp_path / MANIFEST_FILENAME).exists()  # manifest still persisted
