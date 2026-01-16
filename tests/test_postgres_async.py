import os

import pytest

from memu.database.models import MemoryType
from memu.database.postgres.postgres import PostgresStore


@pytest.fixture
def postgres_dsn() -> str:
    return os.environ.get("POSTGRES_DSN", "postgresql+psycopg://postgres:postgres@localhost:5432/memu_test")


@pytest.fixture
async def postgres_store(postgres_dsn: str) -> PostgresStore:
    from pydantic import BaseModel

    class TestScope(BaseModel):
        user_id: str

    store = PostgresStore(
        dsn=postgres_dsn,
        ddl_mode="create",
        vector_provider="pgvector",
        scope_model=TestScope,
    )

    yield store

    await store.close_async()
    store._sessions.close()


@pytest.mark.asyncio
class TestAsyncResourceRepo:

    async def test_create_resource_async(self, postgres_store: PostgresStore) -> None:
        resource = await postgres_store.resource_repo.create_resource_async(
            url="http://example.com/test.txt",
            modality="text",
            local_path="/tmp/test.txt",
            caption="Test resource",
            embedding=[0.1, 0.2, 0.3],
            user_data={"user_id": "test_user"},
        )

        assert resource.id is not None
        assert resource.url == "http://example.com/test.txt"
        assert resource.modality == "text"
        assert postgres_store.resource_repo.resources[resource.id] == resource

    async def test_list_resources_async(self, postgres_store: PostgresStore) -> None:
        await postgres_store.resource_repo.create_resource_async(
            url="http://example.com/test1.txt",
            modality="text",
            local_path="/tmp/test1.txt",
            caption="Test resource 1",
            embedding=None,
            user_data={"user_id": "test_user"},
        )

        resources = await postgres_store.resource_repo.list_resources_async(
            where={"user_id": "test_user"}
        )

        assert len(resources) == 1
        assert "http://example.com/test1.txt" in {r.url for r in resources.values()}

    async def test_clear_resources_async(self, postgres_store: PostgresStore) -> None:
        await postgres_store.resource_repo.create_resource_async(
            url="http://example.com/to_delete.txt",
            modality="text",
            local_path="/tmp/to_delete.txt",
            caption="To be deleted",
            embedding=None,
            user_data={"user_id": "clear_user"},
        )

        deleted = await postgres_store.resource_repo.clear_resources_async(
            where={"user_id": "clear_user"}
        )

        assert len(deleted) == 1
        assert "http://example.com/to_delete.txt" in {r.url for r in deleted.values()}


@pytest.mark.asyncio
class TestAsyncMemoryItemRepo:

    async def test_create_item_async(self, postgres_store: PostgresStore) -> None:
        item = await postgres_store.memory_item_repo.create_item_async(
            memory_type=MemoryType.CONVERSATION,
            summary="Test memory",
            embedding=[0.1, 0.2, 0.3],
            user_data={"user_id": "test_user"},
        )

        assert item.id is not None
        assert item.summary == "Test memory"
        assert item.memory_type == MemoryType.CONVERSATION
        assert postgres_store.memory_item_repo.items[item.id] == item

    async def test_list_items_async(self, postgres_store: PostgresStore) -> None:
        await postgres_store.memory_item_repo.create_item_async(
            memory_type=MemoryType.CONVERSATION,
            summary="Test item 1",
            embedding=None,
            user_data={"user_id": "test_user"},
        )

        items = await postgres_store.memory_item_repo.list_items_async(
            where={"user_id": "test_user"}
        )

        assert len(items) == 1
        assert "Test item 1" in {i.summary for i in items.values()}

    async def test_update_item_async(self, postgres_store: PostgresStore) -> None:
        item = await postgres_store.memory_item_repo.create_item_async(
            memory_type=MemoryType.CONVERSATION,
            summary="Original summary",
            embedding=None,
            user_data={"user_id": "test_user"},
        )

        updated = await postgres_store.memory_item_repo.update_item_async(
            item_id=item.id,
            summary="Updated summary",
            embedding=[0.4, 0.5, 0.6],
        )

        assert updated.summary == "Updated summary"

    async def test_delete_item_async(self, postgres_store: PostgresStore) -> None:
        item = await postgres_store.memory_item_repo.create_item_async(
            memory_type=MemoryType.CONVERSATION,
            summary="To be deleted",
            embedding=None,
            user_data={"user_id": "test_user"},
        )

        await postgres_store.memory_item_repo.delete_item_async(item.id)

        found = await postgres_store.memory_item_repo.get_item_async(item.id)
        assert found is None

    async def test_vector_search_items_async(self, postgres_store: PostgresStore) -> None:
        await postgres_store.memory_item_repo.create_item_async(
            memory_type=MemoryType.CONVERSATION,
            summary="Apple fruit",
            embedding=[1.0, 0.0, 0.0],
            user_data={"user_id": "test_user"},
        )
        await postgres_store.memory_item_repo.create_item_async(
            memory_type=MemoryType.CONVERSATION,
            summary="Orange fruit",
            embedding=[0.0, 1.0, 0.0],
            user_data={"user_id": "test_user"},
        )

        results = await postgres_store.memory_item_repo.vector_search_items_async(
            query_vec=[1.0, 0.0, 0.0],
            top_k=1,
            where={"user_id": "test_user"},
        )

        assert len(results) == 1
        assert results[0][1] > 0.9  # High similarity


@pytest.mark.asyncio
class TestAsyncMemoryCategoryRepo:

    async def test_get_or_create_category_async(self, postgres_store: PostgresStore) -> None:
        category = await postgres_store.memory_category_repo.get_or_create_category_async(
            name="test_category",
            description="Test category description",
            embedding=[0.1, 0.2, 0.3],
            user_data={"user_id": "test_user"},
        )

        assert category.id is not None
        assert category.name == "test_category"
        assert postgres_store.memory_category_repo.categories[category.id] == category

        category2 = await postgres_store.memory_category_repo.get_or_create_category_async(
            name="test_category",
            description="Different description",
            embedding=[0.1, 0.2, 0.3],
            user_data={"user_id": "test_user"},
        )

        assert category2.id == category.id

    async def test_list_categories_async(self, postgres_store: PostgresStore) -> None:
        await postgres_store.memory_category_repo.get_or_create_category_async(
            name="cat1",
            description="Category 1",
            embedding=None,
            user_data={"user_id": "test_user"},
        )

        categories = await postgres_store.memory_category_repo.list_categories_async(
            where={"user_id": "test_user"}
        )

        assert len(categories) == 1
        assert "cat1" in {c.name for c in categories.values()}

    async def test_update_category_async(self, postgres_store: PostgresStore) -> None:
        category = await postgres_store.memory_category_repo.get_or_create_category_async(
            name="to_update",
            description="Original",
            embedding=None,
            user_data={"user_id": "test_user"},
        )

        updated = await postgres_store.memory_category_repo.update_category_async(
            category_id=category.id,
            description="Updated description",
        )

        assert updated.description == "Updated description"


@pytest.mark.asyncio
class TestAsyncCategoryItemRepo:

    async def test_link_item_category_async(self, postgres_store: PostgresStore) -> None:
        item = await postgres_store.memory_item_repo.create_item_async(
            memory_type=MemoryType.CONVERSATION,
            summary="Test item",
            embedding=None,
            user_data={"user_id": "test_user"},
        )
        category = await postgres_store.memory_category_repo.get_or_create_category_async(
            name="test_cat",
            description="Test category",
            embedding=None,
            user_data={"user_id": "test_user"},
        )

        relation = await postgres_store.category_item_repo.link_item_category_async(
            item_id=item.id,
            cat_id=category.id,
            user_data={"user_id": "test_user"},
        )

        assert relation.item_id == item.id
        assert relation.category_id == category.id

    async def test_unlink_item_category_async(self, postgres_store: PostgresStore) -> None:
        item = await postgres_store.memory_item_repo.create_item_async(
            memory_type=MemoryType.CONVERSATION,
            summary="Test item",
            embedding=None,
            user_data={"user_id": "test_user"},
        )
        category = await postgres_store.memory_category_repo.get_or_create_category_async(
            name="test_cat",
            description="Test category",
            embedding=None,
            user_data={"user_id": "test_user"},
        )
        await postgres_store.category_item_repo.link_item_category_async(
            item_id=item.id,
            cat_id=category.id,
            user_data={"user_id": "test_user"},
        )

        await postgres_store.category_item_repo.unlink_item_category_async(
            item_id=item.id,
            cat_id=category.id,
        )

        categories = await postgres_store.category_item_repo.get_item_categories_async(item.id)
        assert len(categories) == 0

    async def test_get_item_categories_async(self, postgres_store: PostgresStore) -> None:
        item = await postgres_store.memory_item_repo.create_item_async(
            memory_type=MemoryType.CONVERSATION,
            summary="Test item",
            embedding=None,
            user_data={"user_id": "test_user"},
        )
        category1 = await postgres_store.memory_category_repo.get_or_create_category_async(
            name="cat1",
            description="Category 1",
            embedding=None,
            user_data={"user_id": "test_user"},
        )
        category2 = await postgres_store.memory_category_repo.get_or_create_category_async(
            name="cat2",
            description="Category 2",
            embedding=None,
            user_data={"user_id": "test_user"},
        )

        await postgres_store.category_item_repo.link_item_category_async(
            item_id=item.id,
            cat_id=category1.id,
            user_data={"user_id": "test_user"},
        )
        await postgres_store.category_item_repo.link_item_category_async(
            item_id=item.id,
            cat_id=category2.id,
            user_data={"user_id": "test_user"},
        )

        categories = await postgres_store.category_item_repo.get_item_categories_async(item.id)

        assert len(categories) == 2


@pytest.mark.asyncio
class TestAsyncSessionManager:

    async def test_async_session_manager_creation(self, postgres_dsn: str) -> None:
        from memu.database.postgres.session import AsyncSessionManager

        async_manager = AsyncSessionManager(dsn=postgres_dsn)

        session = async_manager.session()
        assert session is not None

        await async_manager.close()

    async def test_dsn_conversion(self) -> None:
        from memu.database.postgres.session import AsyncSessionManager

        # Test conversion
        assert (
            AsyncSessionManager._convert_to_async_dsn("postgresql://localhost/db")
            == "postgresql+asyncpg://localhost/db"
        )
        assert (
            AsyncSessionManager._convert_to_async_dsn("postgres://localhost/db")
            == "postgresql+asyncpg://localhost/db"
        )
        # Already converted
        assert (
            AsyncSessionManager._convert_to_async_dsn("postgresql+asyncpg://localhost/db")
            == "postgresql+asyncpg://localhost/db"
        )


@pytest.mark.asyncio
class TestAsyncDatabaseClose:

    async def test_close_async(self, postgres_store: PostgresStore) -> None:
        await postgres_store.close_async()

        from pydantic import BaseModel

        class TestScope(BaseModel):
            user_id: str

        new_store = PostgresStore(
            dsn=postgres_store.dsn,
            ddl_mode="validate",
            vector_provider="pgvector",
            scope_model=TestScope,
        )

        await new_store.close_async()
        new_store._sessions.close()
