import unittest
from unittest.mock import AsyncMock, MagicMock

from memu.app.service import MemoryService
from memu.integrations.dify import DifyToolProvider


class TestDifyToolProvider(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_service = MagicMock(spec=MemoryService)
        self.mock_service.memorize = AsyncMock()
        self.mock_service.retrieve = AsyncMock()
        self.provider = DifyToolProvider(service=self.mock_service)

    async def test_add_memory_success(self):
        # Setup mock return value
        self.mock_service.memorize.return_value = {"resource": {"id": "res-123"}, "items": [{}, {}]}

        query = "This is a test memory."
        user_id = "user-1"

        result = await self.provider.add_memory(query, user_id)

        # Verify service call
        self.assertTrue(self.mock_service.memorize.called)
        _args, kwargs = self.mock_service.memorize.call_args
        self.assertEqual(kwargs["modality"], "document")
        self.assertEqual(kwargs["user"], {"user_id": user_id})
        # Verify temp file was created and passed
        self.assertIn(".txt", kwargs["resource_url"])

        # Verify result
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["resource_id"], "res-123")
        self.assertEqual(result["items_created"], 2)

    async def test_search_memory_success(self):
        # Setup mock return value
        self.mock_service.retrieve.return_value = {
            "items": [{"summary": "Memory 1"}, {"summary": "Memory 2"}],
            "categories": [{"name": "Work", "summary": "Work stuff"}],
        }

        query = "Find memories"
        user_id = "user-1"

        result = await self.provider.search_memory(query, user_id)

        # Verify service call
        self.assertTrue(self.mock_service.retrieve.called)
        kwargs = self.mock_service.retrieve.call_args.kwargs
        self.assertEqual(kwargs["where"], {"user_id": user_id})
        self.assertEqual(kwargs["queries"][0]["content"]["text"], query)

        # Verify result formatting
        self.assertIn("Memory 1", result["result"])
        self.assertIn("Memory 2", result["result"])
        self.assertIn("Work", result["result"])
        self.assertEqual(result["metadata"]["item_count"], 2)

    async def test_add_memory_empty(self):
        result = await self.provider.add_memory("")
        self.assertEqual(result["status"], "error")

    async def test_search_memory_empty(self):
        result = await self.provider.search_memory("")
        self.assertIn("Please provide a query", result["result"])
