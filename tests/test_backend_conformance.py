"""Cross-backend conformance suite for the storage layer.

These tests pin the repository contract behavior that must hold identically across
the pluggable backends (currently ``inmemory`` and ``sqlite``; ``postgres`` needs a
live server so it is exercised separately). They guard the Phase 0 fixes:

- ``clear_*`` with a ``where`` scope mutates the shared state in place (no rebinding
  that orphans the ``DatabaseState`` reference).
- the SQLite read path preserves ``extra`` (reinforcement / ref_id / tool metadata).
- deleting an entry / clearing memory leaves no orphan ``ResourceEntry`` relations.
"""

from __future__ import annotations

import sys
from pathlib import Path

src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

import pytest  # noqa: E402

from memu.app.settings import (  # noqa: E402
    DatabaseConfig,
    DefaultUserModel,
    MetadataStoreConfig,
)
from memu.database.factory import build_database  # noqa: E402
from memu.memory_fs.exporter import slugify  # noqa: E402


def _make_inmemory():
    config = DatabaseConfig(metadata_store=MetadataStoreConfig(provider="inmemory"))
    return build_database(config=config, user_model=DefaultUserModel)


def _make_sqlite(tmp_path: Path):
    dsn = f"sqlite:///{tmp_path / 'conformance.db'}"
    config = DatabaseConfig(metadata_store=MetadataStoreConfig(provider="sqlite", dsn=dsn))
    return build_database(config=config, user_model=DefaultUserModel), dsn


@pytest.fixture(params=["inmemory", "sqlite"])
def store(request, tmp_path):
    if request.param == "inmemory":
        db = _make_inmemory()
        yield db
    else:
        db, _dsn = _make_sqlite(tmp_path)
        yield db
        db.close()


def _seed_entry(store, *, text: str, user_id: str, embedding=None):
    res = store.resource_repo.create_resource(
        lane="source",
        url=f"mem://{text}",
        modality="document",
        local_path="",
        summary=text,
        embedding=None,
        user_data={"user_id": user_id},
    )
    entry = store.entry_repo.create_entry(
        lane="memory",
        source_id=res.id,
        entry_kind="knowledge",
        text=text,
        embedding=embedding or [0.1, 0.2, 0.3],
        user_data={"user_id": user_id},
    )
    return res, entry


def _make_doc(store, *, title: str, user_id: str, description: str = "", embedding=None):
    return store.resource_repo.get_or_create_doc(
        lane="memory",
        title=title,
        description=description,
        embedding=embedding or [0.1, 0.2, 0.3],
        user_data={"user_id": user_id},
        slug=slugify(title),
    )


def test_clear_items_with_scope_mutates_shared_state(store):
    """Clearing a scoped subset must not orphan the shared state reference."""
    _seed_entry(store, text="a", user_id="alice")
    _seed_entry(store, text="b", user_id="bob")

    deleted = store.entry_repo.clear_entries({"user_id": "alice"})
    assert len(deleted) == 1

    remaining = store.entry_repo.list_entries()
    texts = {entry.text for entry in remaining.values()}
    assert texts == {"b"}


def test_clear_categories_with_scope_mutates_shared_state(store):
    _make_doc(store, title="alpha", user_id="alice")
    _make_doc(store, title="beta", user_id="bob")

    store.resource_repo.clear_resources({"user_id": "alice"}, lane="memory")
    remaining = store.resource_repo.list_resources(lane="memory")
    titles = {res.title for res in remaining.values()}
    assert titles == {"beta"}


def test_unlink_item_removes_all_relations(store):
    _res, entry = _seed_entry(store, text="linked", user_id="alice")
    cat1 = _make_doc(store, title="c1", user_id="alice")
    cat2 = _make_doc(store, title="c2", user_id="alice")
    store.resource_entry_repo.link_entry_resource(entry.id, cat1.id, user_data={"user_id": "alice"})
    store.resource_entry_repo.link_entry_resource(entry.id, cat2.id, user_data={"user_id": "alice"})
    assert len(store.resource_entry_repo.get_entry_resources(entry.id)) == 2

    removed = store.resource_entry_repo.unlink_entry(entry.id)
    assert len(removed) == 2
    assert store.resource_entry_repo.get_entry_resources(entry.id) == []
    assert store.resource_entry_repo.list_relations() == []


def test_delete_item_leaves_no_orphan_relations(store):
    """The Phase 0 delete fix: unlink relations before deleting the entry."""
    _res, entry = _seed_entry(store, text="doomed", user_id="alice")
    cat = _make_doc(store, title="c", user_id="alice")
    store.resource_entry_repo.link_entry_resource(entry.id, cat.id, user_data={"user_id": "alice"})

    store.resource_entry_repo.unlink_entry(entry.id)
    store.entry_repo.delete_entry(entry.id)

    assert store.entry_repo.get_entry(entry.id) is None
    # No relation should point at the deleted entry.
    assert all(rel.entry_id != entry.id for rel in store.resource_entry_repo.list_relations())


def test_clear_relations_with_scope(store):
    _res, entry = _seed_entry(store, text="r", user_id="alice")
    cat = _make_doc(store, title="c", user_id="alice")
    store.resource_entry_repo.link_entry_resource(entry.id, cat.id, user_data={"user_id": "alice"})

    removed = store.resource_entry_repo.clear_relations({"user_id": "alice"})
    assert len(removed) == 1
    assert store.resource_entry_repo.list_relations({"user_id": "alice"}) == []


def test_extra_round_trips_through_create_and_read(store):
    """``extra`` (tool metadata / ref_id / reinforcement) must survive a read."""
    res = store.resource_repo.create_resource(
        lane="source",
        url="mem://tool",
        modality="document",
        local_path="",
        summary="tool",
        embedding=None,
        user_data={"user_id": "alice"},
    )
    entry = store.entry_repo.create_entry(
        lane="memory",
        source_id=res.id,
        entry_kind="tool",
        text="tool memory",
        embedding=[0.1, 0.2, 0.3],
        user_data={"user_id": "alice"},
        tool_record={"when_to_use": "always"},
    )
    assert entry.extra.get("when_to_use") == "always"

    fetched = store.entry_repo.get_entry(entry.id)
    assert fetched is not None
    assert fetched.extra.get("when_to_use") == "always"


def _reconcile(crud_self, store, *, entry_id, new_cat_names, mapped_old_cat_ids, name_to_id):
    from types import SimpleNamespace

    from memu.app.crud import CRUDMixin

    fake_self = SimpleNamespace(_map_category_names_to_ids=lambda names, ctx: [name_to_id[n] for n in names])
    CRUDMixin._reconcile_update_categories(
        fake_self,  # type: ignore[arg-type]
        memory_id=entry_id,
        new_cat_names=new_cat_names,
        mapped_old_cat_ids=mapped_old_cat_ids,
        content_changed=False,
        old_content="old",
        new_summary="new",
        ctx=None,
        store=store,
        user={"user_id": "alice"},
        propagate=False,
        category_memory_updates={},
    )


def test_update_with_none_categories_keeps_links(store):
    """P0 regression: omitting categories (None) must NOT drop existing links."""
    _res, entry = _seed_entry(store, text="keep", user_id="alice")
    cat = _make_doc(store, title="A", user_id="alice")
    store.resource_entry_repo.link_entry_resource(entry.id, cat.id, user_data={"user_id": "alice"})

    _reconcile(
        None,
        store,
        entry_id=entry.id,
        new_cat_names=None,
        mapped_old_cat_ids=[cat.id],
        name_to_id={"A": cat.id},
    )

    linked = {rel.resource_id for rel in store.resource_entry_repo.get_entry_resources(entry.id)}
    assert linked == {cat.id}


def test_update_with_empty_categories_clears_links(store):
    """An explicit empty list clears links (distinct from omitted/None)."""
    _res, entry = _seed_entry(store, text="clear", user_id="alice")
    cat = _make_doc(store, title="A", user_id="alice")
    store.resource_entry_repo.link_entry_resource(entry.id, cat.id, user_data={"user_id": "alice"})

    _reconcile(
        None,
        store,
        entry_id=entry.id,
        new_cat_names=[],
        mapped_old_cat_ids=[cat.id],
        name_to_id={"A": cat.id},
    )

    assert store.resource_entry_repo.get_entry_resources(entry.id) == []


def test_update_with_new_categories_swaps_links(store):
    _res, entry = _seed_entry(store, text="swap", user_id="alice")
    cat_a = _make_doc(store, title="A", user_id="alice")
    cat_b = _make_doc(store, title="B", user_id="alice")
    store.resource_entry_repo.link_entry_resource(entry.id, cat_a.id, user_data={"user_id": "alice"})

    _reconcile(
        None,
        store,
        entry_id=entry.id,
        new_cat_names=["B"],
        mapped_old_cat_ids=[cat_a.id],
        name_to_id={"A": cat_a.id, "B": cat_b.id},
    )

    linked = {rel.resource_id for rel in store.resource_entry_repo.get_entry_resources(entry.id)}
    assert linked == {cat_b.id}


class _FakeEmbedClient:
    async def embed(self, texts):
        return [[float(len(t)), 1.0, 0.0] for t in texts]


def test_resolve_category_ids_creates_unknown_adaptively(store):
    """Open/adaptive taxonomy: extractor-proposed names are created on first sight."""
    import asyncio
    from types import SimpleNamespace

    from memu.app.memorize import MemorizeMixin
    from memu.app.service import Context

    ctx = Context(categories_ready=True)
    fake_self = SimpleNamespace(
        _get_embedding_client=lambda profile=None: _FakeEmbedClient(),
        _partition_category_names=MemorizeMixin._partition_category_names,
    )

    ids = asyncio.run(
        MemorizeMixin._resolve_category_ids(
            fake_self,  # type: ignore[arg-type]
            ["Programming", "programming", "Cooking"],
            ctx,
            store,
            user={"user_id": "alice"},
        )
    )
    # "Programming"/"programming" collapse (case-insensitive); "Cooking" is distinct.
    assert len(ids) == 2
    titles = {c.title for c in store.resource_repo.list_resources(lane="memory").values()}
    assert titles == {"Programming", "Cooking"}

    # A subsequent call reuses the cached ids and creates nothing new.
    ids2 = asyncio.run(
        MemorizeMixin._resolve_category_ids(
            fake_self,  # type: ignore[arg-type]
            ["Programming"],
            ctx,
            store,
            user={"user_id": "alice"},
        )
    )
    assert ids2 == [ctx.category_name_to_id["programming"]]
    assert len(store.resource_repo.list_resources(lane="memory")) == 2


def test_sqlite_extra_survives_cache_miss(tmp_path):
    """A fresh SQLite store (cold cache) must reconstruct ``extra`` from the DB."""
    db, dsn = _make_sqlite(tmp_path)
    res = db.resource_repo.create_resource(
        lane="source",
        url="mem://tool",
        modality="document",
        local_path="",
        summary="tool",
        embedding=None,
        user_data={"user_id": "alice"},
    )
    entry = db.entry_repo.create_entry(
        lane="memory",
        source_id=res.id,
        entry_kind="tool",
        text="tool memory",
        embedding=[0.1, 0.2, 0.3],
        user_data={"user_id": "alice"},
        tool_record={"when_to_use": "cold-read"},
    )
    entry_id = entry.id
    db.close()

    # Re-open the same DB file: caches are empty, so reads hit the DB read path.
    config = DatabaseConfig(metadata_store=MetadataStoreConfig(provider="sqlite", dsn=dsn))
    db2 = build_database(config=config, user_model=DefaultUserModel)
    try:
        fetched = db2.entry_repo.get_entry(entry_id)
        assert fetched is not None
        assert fetched.extra.get("when_to_use") == "cold-read"

        listed = db2.entry_repo.list_entries()
        assert listed[entry_id].extra.get("when_to_use") == "cold-read"
    finally:
        db2.close()
