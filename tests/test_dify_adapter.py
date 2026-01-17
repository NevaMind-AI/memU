from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from memu.app.service import MemoryService
from memu.integrations.dify_adapter import get_memu_service, router

# Create valid app for testing
app = FastAPI()
app.include_router(router)


@pytest.fixture
def mock_service():
    service = MagicMock(spec=MemoryService)
    service.memorize = AsyncMock()
    service.retrieve = AsyncMock()
    return service


@pytest.fixture
def client(mock_service):
    # Override dependency with mock
    app.dependency_overrides[get_memu_service] = lambda: mock_service
    return TestClient(app)


def test_add_memory_success(client, mock_service):
    # Setup mock
    mock_service.memorize.return_value = {"resource": {"id": "res-123"}, "items": [{}, {}]}

    payload = {"query": "User likes blue.", "user_id": "u1"}
    response = client.post("/dify/memory/add", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "Successfully memorized" in data["result"]
    assert data["metadata"]["resource_id"] == "res-123"
    assert data["metadata"]["items_created"] == 2

    # Verify mock call
    assert mock_service.memorize.called
    kwargs = mock_service.memorize.call_args.kwargs
    assert kwargs["user"] == {"user_id": "u1"}
    assert ".txt" in kwargs["resource_url"]


def test_search_memory_success(client, mock_service):
    # Setup mock
    mock_service.retrieve.return_value = {
        "items": [{"summary": "Item 1"}, {"summary": "Item 2"}],
        "categories": [{"name": "Cat1", "summary": "Cat Summary"}],
    }

    payload = {"query": "What does user like?", "user_id": "u1"}
    response = client.post("/dify/memory/search", json=payload)

    assert response.status_code == 200
    data = response.json()

    # Verify formatted text
    assert "Item 1" in data["result"]
    assert "Cat1" in data["result"]
    assert data["metadata"]["item_count"] == 2

    # Verify mock call
    assert mock_service.retrieve.called
    kwargs = mock_service.retrieve.call_args.kwargs
    assert kwargs["where"] == {"user_id": "u1"}
    assert kwargs["queries"][0]["content"]["text"] == "What does user like?"


def test_missing_query(client):
    response = client.post("/dify/memory/add", json={"user_id": "u1"})
    assert response.status_code == 422  # Validation error from Pydantic
