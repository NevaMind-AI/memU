"""Cross-backend conformance suite for the storage layer.

These tests pin the repository contract behavior that must hold identically across
the pluggable backends (currently ``inmemory`` and ``sqlite``; ``postgres`` needs a
live server so it is exercised separately). They guard the Phase 0 fixes:

- ``clear_*`` with a ``where`` scope mutates the shared state in place (no rebinding
  that orphans the ``DatabaseState`` reference).
- the SQLite read path preserves ``extra`` (reinforcement / ref_id / tool metadata).
- deleting an item / clearing memory leaves no orphan ``CategoryItem`` relations.
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


def _seed_item(store, *, summary: str, user_id: str, embedding=None):
    res = store.resource_repo.create_resource(
        url=f"mem://{summary}",
        modality="document",
        local_path="",
        caption=summary,
        embedding=None,
        user_data={"user_id": user_id},
    )
    item = store.memory_item_repo.create_item(
        resource_id=res.id,
        memory_type="knowledge",
        summary=summary,
        embedding=embedding or [0.1, 0.2, 0.3],
        user_data={"user_id": user_id},
    )
    return res, item


def test_clear_items_with_scope_mutates_shared_state(store):
    """Clearing a scoped subset must not orphan the shared state reference."""
    _seed_item(store, summary="a", user_id="alice")
    _seed_item(store, summary="b", user_id="bob")

    deleted = store.memory_item_repo.clear_items({"user_id": "alice"})
    assert len(deleted) == 1

    remaining = store.memory_item_repo.list_items()
    summaries = {item.summary for item in remaining.values()}
    assert summaries == {"b"}


def test_clear_categories_with_scope_mutates_shared_state(store):
    store.memory_category_repo.get_or_create_category(
        name="alpha", description="", embedding=[0.1, 0.2, 0.3], user_data={"user_id": "alice"}
    )
    store.memory_category_repo.get_or_create_category(
        name="beta", description="", embedding=[0.1, 0.2, 0.3], user_data={"user_id": "bob"}
    )

    store.memory_category_repo.clear_categories({"user_id": "alice"})
    remaining = store.memory_category_repo.list_categories()
    names = {cat.name for cat in remaining.values()}
    assert names == {"beta"}


def test_unlink_item_removes_all_relations(store):
    _res, item = _seed_item(store, summary="linked", user_id="alice")
    cat1 = store.memory_category_repo.get_or_create_category(
        name="c1", description="", embedding=[0.1, 0.2, 0.3], user_data={"user_id": "alice"}
    )
    cat2 = store.memory_category_repo.get_or_create_category(
        name="c2", description="", embedding=[0.1, 0.2, 0.3], user_data={"user_id": "alice"}
    )
    store.category_item_repo.link_item_category(item.id, cat1.id, user_data={"user_id": "alice"})
    store.category_item_repo.link_item_category(item.id, cat2.id, user_data={"user_id": "alice"})
    assert len(store.category_item_repo.get_item_categories(item.id)) == 2

    removed = store.category_item_repo.unlink_item(item.id)
    assert len(removed) == 2
    assert store.category_item_repo.get_item_categories(item.id) == []
    assert store.category_item_repo.list_relations() == []


def test_delete_item_leaves_no_orphan_relations(store):
    """The Phase 0 delete fix: unlink relations before deleting the item."""
    _res, item = _seed_item(store, summary="doomed", user_id="alice")
    cat = store.memory_category_repo.get_or_create_category(
        name="c", description="", embedding=[0.1, 0.2, 0.3], user_data={"user_id": "alice"}
    )
    store.category_item_repo.link_item_category(item.id, cat.id, user_data={"user_id": "alice"})

    store.category_item_repo.unlink_item(item.id)
    store.memory_item_repo.delete_item(item.id)

    assert store.memory_item_repo.get_item(item.id) is None
    # No relation should point at the deleted item.
    assert all(rel.item_id != item.id for rel in store.category_item_repo.list_relations())


def test_clear_relations_with_scope(store):
    _res, item = _seed_item(store, summary="r", user_id="alice")
    cat = store.memory_category_repo.get_or_create_category(
        name="c", description="", embedding=[0.1, 0.2, 0.3], user_data={"user_id": "alice"}
    )
    store.category_item_repo.link_item_category(item.id, cat.id, user_data={"user_id": "alice"})

    removed = store.category_item_repo.clear_relations({"user_id": "alice"})
    assert len(removed) == 1
    assert store.category_item_repo.list_relations({"user_id": "alice"}) == []


def test_extra_round_trips_through_create_and_read(store):
    """``extra`` (tool metadata / ref_id / reinforcement) must survive a read."""
    res = store.resource_repo.create_resource(
        url="mem://tool",
        modality="document",
        local_path="",
        caption="tool",
        embedding=None,
        user_data={"user_id": "alice"},
    )
    item = store.memory_item_repo.create_item(
        resource_id=res.id,
        memory_type="tool",
        summary="tool memory",
        embedding=[0.1, 0.2, 0.3],
        user_data={"user_id": "alice"},
        tool_record={"when_to_use": "always"},
    )
    assert item.extra.get("when_to_use") == "always"

    fetched = store.memory_item_repo.get_item(item.id)
    assert fetched is not None
    assert fetched.extra.get("when_to_use") == "always"


def _reconcile(crud_self, store, *, item_id, new_cat_names, mapped_old_cat_ids, name_to_id):
    from types import SimpleNamespace

    from memu.app.crud import CRUDMixin

    fake_self = SimpleNamespace(_map_category_names_to_ids=lambda names, ctx: [name_to_id[n] for n in names])
    CRUDMixin._reconcile_update_categories(
        fake_self,  # type: ignore[arg-type]
        memory_id=item_id,
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
    _res, item = _seed_item(store, summary="keep", user_id="alice")
    cat = store.memory_category_repo.get_or_create_category(
        name="A", description="", embedding=[0.1, 0.2, 0.3], user_data={"user_id": "alice"}
    )
    store.category_item_repo.link_item_category(item.id, cat.id, user_data={"user_id": "alice"})

    _reconcile(
        None,
        store,
        item_id=item.id,
        new_cat_names=None,
        mapped_old_cat_ids=[cat.id],
        name_to_id={"A": cat.id},
    )

    linked = {rel.category_id for rel in store.category_item_repo.get_item_categories(item.id)}
    assert linked == {cat.id}


def test_update_with_empty_categories_clears_links(store):
    """An explicit empty list clears links (distinct from omitted/None)."""
    _res, item = _seed_item(store, summary="clear", user_id="alice")
    cat = store.memory_category_repo.get_or_create_category(
        name="A", description="", embedding=[0.1, 0.2, 0.3], user_data={"user_id": "alice"}
    )
    store.category_item_repo.link_item_category(item.id, cat.id, user_data={"user_id": "alice"})

    _reconcile(
        None,
        store,
        item_id=item.id,
        new_cat_names=[],
        mapped_old_cat_ids=[cat.id],
        name_to_id={"A": cat.id},
    )

    assert store.category_item_repo.get_item_categories(item.id) == []


def test_update_with_new_categories_swaps_links(store):
    _res, item = _seed_item(store, summary="swap", user_id="alice")
    cat_a = store.memory_category_repo.get_or_create_category(
        name="A", description="", embedding=[0.1, 0.2, 0.3], user_data={"user_id": "alice"}
    )
    cat_b = store.memory_category_repo.get_or_create_category(
        name="B", description="", embedding=[0.1, 0.2, 0.3], user_data={"user_id": "alice"}
    )
    store.category_item_repo.link_item_category(item.id, cat_a.id, user_data={"user_id": "alice"})

    _reconcile(
        None,
        store,
        item_id=item.id,
        new_cat_names=["B"],
        mapped_old_cat_ids=[cat_a.id],
        name_to_id={"A": cat_a.id, "B": cat_b.id},
    )

    linked = {rel.category_id for rel in store.category_item_repo.get_item_categories(item.id)}
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
    names = {c.name for c in store.memory_category_repo.list_categories().values()}
    assert names == {"Programming", "Cooking"}

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
    assert len(store.memory_category_repo.list_categories()) == 2


def test_sqlite_extra_survives_cache_miss(tmp_path):
    """A fresh SQLite store (cold cache) must reconstruct ``extra`` from the DB."""
    db, dsn = _make_sqlite(tmp_path)
    res = db.resource_repo.create_resource(
        url="mem://tool",
        modality="document",
        local_path="",
        caption="tool",
        embedding=None,
        user_data={"user_id": "alice"},
    )
    item = db.memory_item_repo.create_item(
        resource_id=res.id,
        memory_type="tool",
        summary="tool memory",
        embedding=[0.1, 0.2, 0.3],
        user_data={"user_id": "alice"},
        tool_record={"when_to_use": "cold-read"},
    )
    item_id = item.id
    db.close()

    # Re-open the same DB file: caches are empty, so reads hit the DB read path.
    config = DatabaseConfig(metadata_store=MetadataStoreConfig(provider="sqlite", dsn=dsn))
    db2 = build_database(config=config, user_model=DefaultUserModel)
    try:
        fetched = db2.memory_item_repo.get_item(item_id)
        assert fetched is not None
        assert fetched.extra.get("when_to_use") == "cold-read"

        listed = db2.memory_item_repo.list_items()
        assert listed[item_id].extra.get("when_to_use") == "cold-read"
    finally:
        db2.close()
