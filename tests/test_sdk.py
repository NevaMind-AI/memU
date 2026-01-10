"""
Unit tests for the MemU Python SDK.
"""

from __future__ import annotations

import pytest

from memu.sdk import (
    MemorizeResult,
    MemoryCategory,
    MemoryItem,
    MemoryResource,
    MemUClient,
    RetrieveResult,
    TaskStatus,
)
from memu.sdk.client import (
    MemUAuthenticationError,
    MemUClientError,
    MemUNotFoundError,
    MemURateLimitError,
    MemUValidationError,
)
from memu.sdk.models import TaskStatusEnum


class TestMemUClientInit:
    """Test MemUClient initialization."""

    def test_init_with_valid_api_key(self) -> None:
        """Test that client initializes with valid API key."""
        client = MemUClient(api_key="test_key")
        assert client._api_key == "test_key"
        assert client._base_url == "https://api.memu.so"

    def test_init_with_custom_base_url(self) -> None:
        """Test that client accepts custom base URL."""
        client = MemUClient(api_key="test_key", base_url="https://custom.example.com")
        assert client._base_url == "https://custom.example.com"

    def test_init_strips_trailing_slash(self) -> None:
        """Test that trailing slash is stripped from base URL."""
        client = MemUClient(api_key="test_key", base_url="https://api.example.com/")
        assert client._base_url == "https://api.example.com"

    def test_init_strips_api_key_whitespace(self) -> None:
        """Test that whitespace is stripped from API key."""
        client = MemUClient(api_key="  test_key  ")
        assert client._api_key == "test_key"

    def test_init_raises_on_empty_api_key(self) -> None:
        """Test that empty API key raises ValueError."""
        with pytest.raises(ValueError, match="API key is required"):
            MemUClient(api_key="")

    def test_init_raises_on_whitespace_api_key(self) -> None:
        """Test that whitespace-only API key raises ValueError."""
        with pytest.raises(ValueError, match="API key is required"):
            MemUClient(api_key="   ")


class TestDataModels:
    """Test data model instantiation."""

    def test_memory_item_model(self) -> None:
        """Test MemoryItem model."""
        item = MemoryItem(
            id="item_1",
            summary="User prefers Italian food",
            memory_type="preference",
            category_id="cat_1",
        )
        assert item.id == "item_1"
        assert item.memory_type == "preference"

    def test_memory_category_model(self) -> None:
        """Test MemoryCategory model."""
        category = MemoryCategory(
            id="cat_1",
            name="preferences",
            summary="User preferences",
        )
        assert category.id == "cat_1"
        assert category.name == "preferences"

    def test_memory_resource_model(self) -> None:
        """Test MemoryResource model."""
        resource = MemoryResource(
            id="res_1",
            url="https://example.com/chat.json",
            modality="conversation",
        )
        assert resource.id == "res_1"
        assert resource.modality == "conversation"

    def test_task_status_model(self) -> None:
        """Test TaskStatus model."""
        status = TaskStatus(
            task_id="task_1",
            status=TaskStatusEnum.COMPLETED,
            progress=100,
        )
        assert status.task_id == "task_1"
        assert status.status == TaskStatusEnum.COMPLETED

    def test_memorize_result_model(self) -> None:
        """Test MemorizeResult model."""
        result = MemorizeResult(
            task_id="task_1",
            items=[],
            categories=[],
        )
        assert result.task_id == "task_1"

    def test_retrieve_result_model(self) -> None:
        """Test RetrieveResult model."""
        result = RetrieveResult(
            categories=[],
            items=[],
            resources=[],
        )
        assert len(result.items) == 0


class TestExceptions:
    """Test exception classes."""

    def test_client_error(self) -> None:
        """Test MemUClientError."""
        error = MemUClientError("Test error", status_code=500)
        assert error.message == "Test error"
        assert error.status_code == 500

    def test_authentication_error(self) -> None:
        """Test MemUAuthenticationError."""
        error = MemUAuthenticationError("Invalid key", status_code=401)
        assert isinstance(error, MemUClientError)
        assert error.status_code == 401

    def test_rate_limit_error(self) -> None:
        """Test MemURateLimitError."""
        error = MemURateLimitError("Rate limit", retry_after=30.0, status_code=429)
        assert error.retry_after == 30.0
        assert error.status_code == 429

    def test_not_found_error(self) -> None:
        """Test MemUNotFoundError."""
        error = MemUNotFoundError("Not found", status_code=404)
        assert isinstance(error, MemUClientError)

    def test_validation_error(self) -> None:
        """Test MemUValidationError."""
        error = MemUValidationError("Validation failed", status_code=422)
        assert isinstance(error, MemUClientError)


class TestClientHelpers:
    """Test client helper methods."""

    def test_is_local_file_http(self) -> None:
        """Test that HTTP URLs are not local files."""
        assert not MemUClient._is_local_file("http://example.com/file.json")
        assert not MemUClient._is_local_file("https://example.com/file.json")

    def test_is_local_file_s3(self) -> None:
        """Test that S3 URLs are not local files."""
        assert not MemUClient._is_local_file("s3://bucket/file.json")

    def test_is_local_file_gs(self) -> None:
        """Test that GCS URLs are not local files."""
        assert not MemUClient._is_local_file("gs://bucket/file.json")

    def test_is_local_file_path(self) -> None:
        """Test that paths are local files."""
        assert MemUClient._is_local_file("/path/to/file.json")
        assert MemUClient._is_local_file("./relative/path.json")
        assert MemUClient._is_local_file("file.json")

    def test_encode_content_string(self) -> None:
        """Test encoding string content."""
        encoded = MemUClient._encode_content("hello")
        assert encoded == "aGVsbG8="  # base64 of "hello"

    def test_encode_content_bytes(self) -> None:
        """Test encoding bytes content."""
        encoded = MemUClient._encode_content(b"hello")
        assert encoded == "aGVsbG8="


class TestClientDefaultHeaders:
    """Test default headers generation."""

    def test_default_headers(self) -> None:
        """Test that default headers are correctly generated."""
        client = MemUClient(api_key="test_key")
        headers = client._default_headers()
        assert headers["Authorization"] == "Bearer test_key"
        assert headers["Content-Type"] == "application/json"
        assert "User-Agent" in headers
