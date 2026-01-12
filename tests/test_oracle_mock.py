import sys
from unittest import mock

import pytest
from pydantic import BaseModel

from memu.database.models import Resource
from memu.database.oracle.oracle import OracleStorage


# Define a Dummy Model for Scope
class User(BaseModel):
    id: str
    username: str


@pytest.fixture
def mock_sqlalchemy():
    with (
        mock.patch("memu.database.oracle.oracle.create_engine") as mock_engine,
        mock.patch("memu.database.oracle.session.create_engine"),
        mock.patch("memu.database.oracle.session.Session") as mock_session_cls,
    ):
        # Setup the mock engine's dispose method
        mock_engine.return_value.dispose.return_value = None

        # Setup the mock session
        session_instance = mock.MagicMock()
        mock_session_cls.return_value = session_instance

        # Configure session context manager
        session_instance.__enter__.return_value = session_instance
        session_instance.__exit__.return_value = None

        yield {"engine": mock_engine, "session_cls": mock_session_cls, "session": session_instance}


def test_oracle_store_flow(mock_sqlalchemy):
    dsn = "oracle+oracledb://testuser:testpass@localhost:1521/?service_name=XE"

    # 1. Instantiate OracleStorage
    store = OracleStorage(dsn=dsn, ddl_mode="create", scope_model=User)

    # Verify engine created for schema check
    mock_sqlalchemy["engine"].assert_called()
    mock_session = mock_sqlalchemy["session"]

    # 2. Create a Resource object
    resource_id = "res-123"
    resource = Resource(
        id=resource_id,
        url="http://example.com/doc",
        modality="text",
        local_path="doc_test.txt",
        caption="A test document",
        embedding=[0.1, 0.2, 0.3],
        created_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-01T00:00:00Z",
    )

    # ...

    created_res = store.resource_repo.create_resource(
        url=resource.url,
        modality=resource.modality,
        local_path=resource.local_path,
        caption=resource.caption,
        embedding=resource.embedding,
        user_data={
            "id": resource_id,
            "username": "testuser",
        },
    )

    # ...

    # Test `list_resources` simulating a DB hit
    # list_resources calls session.scalars().all()
    # We need to mock that return value
    mock_session.scalars.return_value.all.return_value = [created_res]

    fetched = store.resource_repo.list_resources(where={"url": resource.url})

    assert len(fetched) == 1
    assert next(iter(fetched.values())).id == created_res.id

    print("\nTest passed successfully!")


if __name__ == "__main__":
    sys.exit(pytest.main(["-v", __file__]))
