"""
Tests for the uncategorized-fallback feature in MemorizeMixin.

When the LLM extracts a memory item that maps to no configured category,
it is linked to an auto-created "uncategorized" category so it remains
reachable from LLM-mode retrieval (which joins items via category relations).
"""

from __future__ import annotations

from typing import Any

import pytest

from memu.app.memorize import UNCATEGORIZED_CATEGORY_NAME, MemorizeMixin
from memu.app.service import Context
from memu.app.settings import CategoryConfig, DatabaseConfig, DefaultUserModel, MemorizeConfig
from memu.database.factory import build_database
from memu.database.interfaces import Database


class FakeLLMClient:
    """Deterministic stand-in for the embedding and chat client."""

    chat_model = "fake-chat"
    embed_model = "fake-embed"

    async def embed(self, inputs: list[str]) -> list[list[float]]:
        return [[float(len(s) % 5), 0.0, 0.0] for s in inputs]

    async def chat(self, *_: Any, **__: Any) -> str:
        return "fake summary"


def _build_mixin(
    *,
    enable_fallback: bool = True,
    configured_categories: list[CategoryConfig] | None = None,
) -> tuple[MemorizeMixin, Context, Database]:
    cfg = MemorizeConfig(
        memory_categories=configured_categories or [],
        enable_uncategorized_fallback=enable_fallback,
    )
    mixin = MemorizeMixin.__new__(MemorizeMixin)
    mixin.memorize_config = cfg
    mixin.category_configs = list(cfg.memory_categories)
    mixin._get_llm_client = lambda profile=None, step_context=None: FakeLLMClient()  # type: ignore[method-assign]

    db = build_database(
        config=DatabaseConfig.model_validate({"metadata_store": {"provider": "inmemory"}}),
        user_model=DefaultUserModel,
    )
    return mixin, Context(), db


class TestConfigFlag:
    def test_defaults_enabled(self):
        """New deployments get the fallback automatically."""
        assert MemorizeConfig().enable_uncategorized_fallback is True

    def test_can_be_disabled(self):
        cfg = MemorizeConfig(enable_uncategorized_fallback=False)
        assert cfg.enable_uncategorized_fallback is False


class TestInitializeCategories:
    @pytest.mark.asyncio
    async def test_creates_uncategorized_when_no_user_categories(self):
        """Even with empty memory_categories, the fallback is created."""
        mixin, ctx, db = _build_mixin()
        await mixin._initialize_categories(ctx, db)
        assert UNCATEGORIZED_CATEGORY_NAME in ctx.category_name_to_id
        assert ctx.categories_ready is True
        cat_id = ctx.category_name_to_id[UNCATEGORIZED_CATEGORY_NAME]
        assert cat_id in db.memory_category_repo.categories

    @pytest.mark.asyncio
    async def test_appends_uncategorized_alongside_user_categories(self):
        mixin, ctx, db = _build_mixin(configured_categories=[CategoryConfig(name="habits", description="d")])
        await mixin._initialize_categories(ctx, db)
        assert "habits" in ctx.category_name_to_id
        assert UNCATEGORIZED_CATEGORY_NAME in ctx.category_name_to_id

    @pytest.mark.asyncio
    async def test_skipped_when_disabled(self):
        mixin, ctx, db = _build_mixin(enable_fallback=False)
        await mixin._initialize_categories(ctx, db)
        assert UNCATEGORIZED_CATEGORY_NAME not in ctx.category_name_to_id

    @pytest.mark.asyncio
    async def test_fallback_category_has_seeded_summary(self):
        """route_category filters on cat.summary; only the fallback gets one at init."""
        mixin, ctx, db = _build_mixin(configured_categories=[CategoryConfig(name="habits", description="user habits")])
        await mixin._initialize_categories(ctx, db)

        fallback_id = ctx.category_name_to_id[UNCATEGORIZED_CATEGORY_NAME]
        habits_id = ctx.category_name_to_id["habits"]
        assert db.memory_category_repo.categories[fallback_id].summary
        assert not db.memory_category_repo.categories[habits_id].summary

    @pytest.mark.asyncio
    async def test_not_duplicated_if_user_already_configured_it(self):
        """User-defined 'uncategorized' takes precedence; no second copy is added."""
        mixin, ctx, db = _build_mixin(
            configured_categories=[CategoryConfig(name=UNCATEGORIZED_CATEGORY_NAME, description="user-defined")]
        )
        await mixin._initialize_categories(ctx, db)
        assert (
            sum(1 for c in db.memory_category_repo.categories.values() if c.name.lower() == UNCATEGORIZED_CATEGORY_NAME)
            == 1
        )


class TestPersistMemoryItems:
    @pytest.mark.asyncio
    async def test_links_uncategorized_item_to_fallback_category(self):
        """An item with no matching categories ends up linked to the fallback."""
        mixin, ctx, db = _build_mixin(configured_categories=[CategoryConfig(name="habits", description="d")])
        await mixin._initialize_categories(ctx, db)

        items, rels, updates = await mixin._persist_memory_items(
            resource_id="res-1",
            structured_entries=[("profile", "User uses dark mode.", [])],
            ctx=ctx,
            store=db,
            embed_client=FakeLLMClient(),
            user={"user_id": "u1"},
        )

        assert len(items) == 1
        assert len(rels) == 1
        fallback_id = ctx.category_name_to_id[UNCATEGORIZED_CATEGORY_NAME]
        assert rels[0].category_id == fallback_id
        assert fallback_id in updates

    @pytest.mark.asyncio
    async def test_keeps_explicit_category_when_provided(self):
        """If the LLM returns a matching category name, no fallback is applied."""
        mixin, ctx, db = _build_mixin(configured_categories=[CategoryConfig(name="habits", description="d")])
        await mixin._initialize_categories(ctx, db)

        _, rels, _ = await mixin._persist_memory_items(
            resource_id="res-1",
            structured_entries=[("profile", "User journals daily.", ["habits"])],
            ctx=ctx,
            store=db,
            embed_client=FakeLLMClient(),
            user={"user_id": "u1"},
        )

        habits_id = ctx.category_name_to_id["habits"]
        assert [r.category_id for r in rels] == [habits_id]

    @pytest.mark.asyncio
    async def test_no_fallback_when_disabled(self):
        """With the flag off, uncategorized items get no category links at all."""
        mixin, ctx, db = _build_mixin(
            enable_fallback=False,
            configured_categories=[CategoryConfig(name="habits", description="d")],
        )
        await mixin._initialize_categories(ctx, db)

        _, rels, updates = await mixin._persist_memory_items(
            resource_id="res-1",
            structured_entries=[("profile", "User likes oolong tea.", [])],
            ctx=ctx,
            store=db,
            embed_client=FakeLLMClient(),
            user={"user_id": "u1"},
        )

        assert rels == []
        assert updates == {}


class TestUpdateCategorySummaries:
    @pytest.mark.asyncio
    async def test_skips_summary_for_uncategorized_category(self):
        """Heterogeneous uncategorized items should not trigger a summary LLM call."""
        mixin, ctx, db = _build_mixin()
        await mixin._initialize_categories(ctx, db)
        fallback_id = ctx.category_name_to_id[UNCATEGORIZED_CATEGORY_NAME]

        call_count = 0

        class CountingClient(FakeLLMClient):
            async def chat(self, *_: Any, **__: Any) -> str:
                nonlocal call_count
                call_count += 1
                return "should not happen"

        result = await mixin._update_category_summaries(
            {fallback_id: [("item-1", "User uses dark mode.")]},
            ctx,
            db,
            llm_client=CountingClient(),
        )

        assert call_count == 0
        assert result == {}
