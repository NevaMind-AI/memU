import pytest

from memu.app import MemoryService


@pytest.mark.asyncio
class TestUseAsyncConfig:

    async def test_use_async_false_uses_sync_handlers(self) -> None:
        service = MemoryService(
            database_config={
                "metadata_store": {
                    "provider": "inmemory",
                },
                "use_async": False,
            },
        )

        assert service._use_async is False

        list_workflow = service._build_list_memory_items_workflow()
        assert len(list_workflow) == 2

        list_step = list_workflow[0]
        assert list_step.step_id == "list_memory_items"
        import inspect

        assert not inspect.iscoroutinefunction(list_step.handler)

    async def test_use_async_true_uses_async_handlers(self) -> None:
        service = MemoryService(
            database_config={
                "metadata_store": {
                    "provider": "inmemory",
                },
                "use_async": True,
            },
        )

        assert service._use_async is True

        list_workflow = service._build_list_memory_items_workflow()
        assert len(list_workflow) == 2

        list_step = list_workflow[0]
        assert list_step.step_id == "list_memory_items"
        import inspect

        assert inspect.iscoroutinefunction(list_step.handler)

    async def test_default_use_async_is_false(self) -> None:
        service = MemoryService(
            database_config={
                "metadata_store": {
                    "provider": "inmemory",
                },
            },
        )

        assert service._use_async is False

    async def test_clear_workflow_async_handlers(self) -> None:
        service = MemoryService(
            database_config={
                "metadata_store": {
                    "provider": "inmemory",
                },
                "use_async": True,
            },
        )

        import inspect

        clear_workflow = service._build_clear_memory_workflow()
        assert len(clear_workflow) == 4

        for step in clear_workflow[:3]:
            assert inspect.iscoroutinefunction(step.handler), f"{step.step_id} should use async handler"

    async def test_create_workflow_async_handlers(self) -> None:
        service = MemoryService(
            database_config={
                "metadata_store": {
                    "provider": "inmemory",
                },
                "use_async": True,
            },
        )

        import inspect

        create_workflow = service._build_create_memory_item_workflow()
        assert len(create_workflow) == 3

        create_step = create_workflow[0]
        assert create_step.step_id == "create_memory_item"
        assert inspect.iscoroutinefunction(create_step.handler)

    async def test_update_workflow_async_handlers(self) -> None:
        service = MemoryService(
            database_config={
                "metadata_store": {
                    "provider": "inmemory",
                },
                "use_async": True,
            },
        )

        import inspect

        update_workflow = service._build_update_memory_item_workflow()

        update_step = update_workflow[0]
        assert update_step.step_id == "update_memory_item"
        assert inspect.iscoroutinefunction(update_step.handler)

    async def test_delete_workflow_async_handlers(self) -> None:
        service = MemoryService(
            database_config={
                "metadata_store": {
                    "provider": "inmemory",
                },
                "use_async": True,
            },
        )

        import inspect

        delete_workflow = service._build_delete_memory_item_workflow()

        delete_step = delete_workflow[0]
        assert delete_step.step_id == "delete_memory_item"
        assert inspect.iscoroutinefunction(delete_step.handler)
