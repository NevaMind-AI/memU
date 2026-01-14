import importlib.util
import json
import unittest
from unittest.mock import MagicMock, patch

from memu.database.models import MemoryItem
from memu.database.oracle.oracle import OracleMemoryItemRepo

HAS_ORACLE = importlib.util.find_spec("oracledb") is not None


@unittest.skipIf(not HAS_ORACLE, "oracledb not installed")
class TestOracleMemoryItemRepo(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_connect_patcher = patch("oracledb.connect")
        self.mock_connect = self.mock_connect_patcher.start()

        # Setup mock connection and cursor
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_connect.return_value = self.mock_conn
        self.mock_conn.cursor.return_value.__enter__.return_value = self.mock_cursor

        # Instantiate repo (will trigger _ensure_table which uses cursor)
        self.repo = OracleMemoryItemRepo("user", "pass", "dsn")

    def tearDown(self) -> None:
        self.mock_connect_patcher.stop()

    def test_create_item(self) -> None:
        # Arrange
        resource_id = "res-1"
        memory_type = "profile"  # inferred Literal
        summary = "User likes tacos"
        embedding = [0.1, 0.2, 0.3]
        user_data = {"source": "interview"}

        # Act
        item = self.repo.create_item(
            resource_id=resource_id,
            memory_type=memory_type,  # type: ignore[arg-type]
            summary=summary,
            embedding=embedding,
            user_data=user_data,
        )

        # Assert
        # Check that proper SQL was executed
        # We need to find the call that did the INSERT
        insert_call = None
        for call_args in self.mock_cursor.execute.call_args_list:
            sql = call_args[0][0]
            if "INSERT INTO memory_items" in sql:
                insert_call = call_args
                break

        self.assertIsNotNone(insert_call, "INSERT statement was not executed")
        if insert_call:
            args, _ = insert_call
            params = args[1]
            # Params: [id, resource_id, memory_type, summary, embedding_json, user_data_json, created, updated]
            self.assertEqual(params[1], resource_id)
            self.assertEqual(params[2], memory_type)
            self.assertEqual(params[3], summary)
            self.assertEqual(params[4], json.dumps(embedding))
            self.assertEqual(params[5], json.dumps(user_data))

        # Check returned item
        self.assertIsInstance(item, MemoryItem)
        self.assertEqual(item.resource_id, resource_id)
        self.assertEqual(item.summary, summary)
        self.assertEqual(item.embedding, embedding)

    def test_get_item(self) -> None:
        # Arrange
        item_id = "test-uuid"
        summary = "User likes pizza"
        embedding = [0.9, 0.8, 0.7]
        user_data = {"checked": True}

        # Mock fetchone return value
        # Columns: id, resource_id, memory_type, summary, embedding, user_data, created_at, updated_at
        import pendulum

        now = pendulum.now("UTC")

        self.mock_cursor.fetchone.return_value = (
            item_id,
            "res-2",
            "profile",
            summary,
            json.dumps(embedding),
            json.dumps(user_data),
            now,
            now,
        )

        # Act
        item = self.repo.get_item(item_id)

        # Assert
        self.mock_cursor.execute.assert_called_with(
            "SELECT id, resource_id, memory_type, summary, embedding, user_data, created_at, updated_at FROM memory_items WHERE id = :1",
            [item_id],
        )

        self.assertIsNotNone(item)
        if item:
            self.assertEqual(item.id, item_id)
            self.assertEqual(item.summary, summary)
            self.assertEqual(item.embedding, embedding)
            # Note: user_data might not be in item if MemoryItem model is strict,
            # but we just check what we can.
