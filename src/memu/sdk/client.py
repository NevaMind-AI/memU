"""
MemU Python SDK Client

A fully-featured async/sync client for the MemU Cloud API.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import mimetypes
import time
from pathlib import Path
from typing import Any, cast

import httpx

from memu.sdk.models import (
    MemorizeResult,
    MemoryCategory,
    MemoryItem,
    MemoryResource,
    RetrieveResult,
    TaskStatus,
    TaskStatusEnum,
)

logger = logging.getLogger(__name__)

# Default API configuration
DEFAULT_BASE_URL = "https://api.memu.so"
DEFAULT_TIMEOUT = 60.0
DEFAULT_POLL_INTERVAL = 2.0
DEFAULT_MAX_RETRIES = 3


class MemUClientError(Exception):
    """Base exception for MemU SDK errors."""

    def __init__(self, message: str, status_code: int | None = None, response: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response = response


class MemUAuthenticationError(MemUClientError):
    """Raised when API authentication fails."""

    DEFAULT_MESSAGE = "Authentication failed. Please check your API key."

    def __init__(
        self,
        message: str | None = None,
        status_code: int | None = None,
        response: dict[str, Any] | None = None,
    ):
        super().__init__(message or self.DEFAULT_MESSAGE, status_code, response)


class MemURateLimitError(MemUClientError):
    """Raised when API rate limit is exceeded."""

    def __init__(
        self,
        message: str,
        retry_after: float | None = None,
        status_code: int | None = None,
        response: dict[str, Any] | None = None,
    ):
        super().__init__(message, status_code, response)
        self.retry_after = retry_after


class MemUNotFoundError(MemUClientError):
    """Raised when a requested resource is not found."""

    pass


class MemUValidationError(MemUClientError):
    """Raised when request validation fails."""

    DEFAULT_MESSAGE = "Request validation failed. Please check your request parameters."

    def __init__(
        self,
        message: str | None = None,
        status_code: int | None = None,
        response: dict[str, Any] | None = None,
    ):
        super().__init__(message or self.DEFAULT_MESSAGE, status_code, response)


class MemUClient:
    """
    Async Python client for the MemU Cloud API.

    This client provides a simple, developer-friendly interface for interacting
    with MemU's memory management capabilities. It supports both synchronous
    and asynchronous usage patterns.

    Args:
        api_key: Your MemU API key. Get one at https://memu.so
        base_url: API base URL (default: https://api.memu.so)
        timeout: Request timeout in seconds (default: 60.0)
        max_retries: Maximum number of retry attempts for failed requests (default: 3)

    Example:
        # Async usage
        async with MemUClient(api_key="your_key") as client:
            result = await client.memorize(
                conversation_text="Hello, how are you?",
                user_id="user_123",
                agent_id="agent_123",
            )

        # Sync usage (uses internal event loop)
        client = MemUClient(api_key="your_key")
        result = client.memorize_sync(
            conversation_text="Hello, how are you?",
            user_id="user_123",
            agent_id="agent_123",
        )
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ):
        if not api_key or not api_key.strip():
            msg = "API key is required"
            raise ValueError(msg)

        self._api_key = api_key.strip()
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> MemUClient:
        """Enter async context manager."""
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
            headers=self._default_headers(),
        )
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context manager."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _default_headers(self) -> dict[str, str]:
        """Generate default headers for API requests."""
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "User-Agent": "memu-python-sdk/1.0.0",
        }

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                headers=self._default_headers(),
            )
        return self._client

    def _raise_for_status(
        self,
        response: httpx.Response,
        path: str,
    ) -> None:
        """Raise appropriate exception for error status codes."""
        status = response.status_code
        parsed = self._safe_parse_json(response)

        if status == 401:
            raise MemUAuthenticationError(status_code=401, response=parsed)
        if status == 404:
            raise MemUNotFoundError(path, status_code=404, response=parsed)
        if status == 422:
            raise MemUValidationError(status_code=422, response=parsed)
        if status >= 400:
            msg = f"{status}: {path}"
            raise MemUClientError(msg, status_code=status, response=parsed)

    async def _request(  # noqa: C901
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Make an HTTP request to the API with automatic retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API endpoint path
            json: JSON request body
            params: Query parameters

        Returns:
            Parsed JSON response

        Raises:
            MemUClientError: For various API errors
        """
        client = await self._get_client()
        last_error: Exception | None = None

        for attempt in range(self._max_retries):
            try:
                response = await client.request(method, path, json=json, params=params)
                status = response.status_code

                # Rate limiting - retry if possible
                if status == 429:
                    retry_after = response.headers.get("Retry-After")
                    wait_time = float(retry_after) if retry_after else (2**attempt)
                    if attempt < self._max_retries - 1:
                        logger.warning("Rate limited, retrying in %.1f seconds...", wait_time)
                        await asyncio.sleep(wait_time)
                        continue
                    raise MemURateLimitError(
                        "rate_limit",
                        retry_after=float(retry_after) if retry_after else None,
                        status_code=429,
                        response=self._safe_parse_json(response),
                    )

                # Server errors - retry if possible
                if status >= 500:
                    if attempt < self._max_retries - 1:
                        wait_time = 2**attempt
                        logger.warning("Server error %d, retrying in %.1f seconds...", status, wait_time)
                        await asyncio.sleep(wait_time)
                        continue
                    raise MemUClientError(str(status), status_code=status, response=self._safe_parse_json(response))

                # Client errors - raise immediately
                if status >= 400:
                    self._raise_for_status(response, path)

                return cast(dict[str, Any], self._safe_parse_json(response)) or {}

            except httpx.TimeoutException as e:
                last_error = e
                if attempt < self._max_retries - 1:
                    wait_time = 2**attempt
                    logger.warning("Request timeout, retrying in %.1f seconds...", wait_time)
                    await asyncio.sleep(wait_time)
                    continue
            except httpx.RequestError as e:
                last_error = e
                if attempt < self._max_retries - 1:
                    wait_time = 2**attempt
                    logger.warning("Request error, retrying in %.1f seconds: %s", wait_time, str(e))
                    await asyncio.sleep(wait_time)
                    continue

        msg = f"Request failed after {self._max_retries} attempts"
        raise MemUClientError(msg) from last_error

    @staticmethod
    def _safe_parse_json(response: httpx.Response) -> dict[str, Any] | None:
        """Safely parse JSON response."""
        try:
            return cast(dict[str, Any], response.json())
        except Exception:
            return None

    # =========================================================================
    # MEMORIZE API
    # =========================================================================

    async def memorize(  # noqa: C901
        self,
        *,
        conversation: list[dict[str, Any]] | None = None,
        conversation_text: str | None = None,
        user_id: str,
        agent_id: str,
        user_name: str = "User",
        agent_name: str = "Assistant",
        session_date: str | None = None,
        wait_for_completion: bool = False,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        timeout: float | None = None,
    ) -> MemorizeResult:
        """
        Memorize a conversation and extract structured memory.

        This registers a memorization task that processes the conversation
        and extracts memory items organized into categories.

        Args:
            conversation: List of conversation messages in format
                [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
            conversation_text: Alternative: raw conversation text to memorize
            user_id: User ID for scoping the memory (required)
            agent_id: Agent ID for scoping the memory (required)
            user_name: Display name for the user (default: "User")
            agent_name: Display name for the agent (default: "Assistant")
            session_date: Optional session date in ISO format
            wait_for_completion: If True, poll until the task completes
            poll_interval: Seconds between status checks when waiting
            timeout: Maximum seconds to wait for completion

        Returns:
            MemorizeResult containing task_id and status

        Raises:
            ValueError: If neither conversation nor conversation_text is provided
            MemUClientError: For API errors

        Example:
            # Memorize a conversation
            result = await client.memorize(
                conversation=[
                    {"role": "user", "content": "I love Italian food"},
                    {"role": "assistant", "content": "That's great!"},
                ],
                user_id="user_123",
                agent_id="agent_456",
                wait_for_completion=True
            )
            print(f"Task ID: {result.task_id}")

            # Memorize raw text
            result = await client.memorize(
                conversation_text="User: I love pasta\\nAssistant: Great choice!",
                user_id="user_123",
                agent_id="agent_456"
            )
        """
        if not conversation and not conversation_text:
            msg = "Either conversation or conversation_text must be provided"
            raise ValueError(msg)

        # Build request payload matching API v3 schema
        payload: dict[str, Any] = {
            "user_id": user_id,
            "agent_id": agent_id,
            "user_name": user_name,
            "agent_name": agent_name,
        }

        if conversation:
            payload["conversation"] = conversation
        elif conversation_text:
            payload["conversation_text"] = conversation_text

        if session_date:
            payload["session_date"] = session_date

        # Make the request
        response = await self._request("POST", "/api/v3/memory/memorize", json=payload)

        # Wait for completion if requested
        if wait_for_completion and response.get("task_id"):
            task_id = response["task_id"]
            start_time = time.time()
            effective_timeout = timeout or 300.0  # Default 5 minutes

            while True:
                status = await self.get_task_status(task_id)

                if status.status in (TaskStatusEnum.COMPLETED, TaskStatusEnum.SUCCESS):
                    if status.result:
                        return MemorizeResult(
                            task_id=task_id,
                            resource=status.result.get("resource"),
                            items=[
                                MemoryItem(**item) if isinstance(item, dict) else item
                                for item in status.result.get("items", [])
                            ],
                            categories=[
                                MemoryCategory(**cat) if isinstance(cat, dict) else cat
                                for cat in status.result.get("categories", [])
                            ],
                        )
                    return MemorizeResult(task_id=task_id)

                if status.status == TaskStatusEnum.FAILED:
                    msg = f"Memorization task failed: {status.message}"
                    raise MemUClientError(msg)

                # Check timeout
                if time.time() - start_time > effective_timeout:
                    msg = f"Memorization task timed out after {effective_timeout} seconds"
                    raise MemUClientError(msg)

                await asyncio.sleep(poll_interval)

        # Return immediate result
        return MemorizeResult(
            task_id=response.get("task_id"),
            resource=response.get("resource"),
            items=[MemoryItem(**item) if isinstance(item, dict) else item for item in response.get("items", [])],
            categories=[
                MemoryCategory(**cat) if isinstance(cat, dict) else cat for cat in response.get("categories", [])
            ],
        )

    async def get_task_status(self, task_id: str) -> TaskStatus:
        """
        Get the status of a memorization task.

        Args:
            task_id: The task ID returned from memorize()

        Returns:
            TaskStatus with current progress and results

        Example:
            status = await client.get_task_status("task_abc123")
            if status.status == TaskStatusEnum.COMPLETED:
                print(f"Task completed: {status.result}")
        """
        response = await self._request("GET", f"/api/v3/memory/memorize/status/{task_id}")
        return TaskStatus(**response)

    # =========================================================================
    # RETRIEVE API
    # =========================================================================

    async def retrieve(
        self,
        query: str | list[dict[str, Any]],
        *,
        user_id: str,
        agent_id: str,
    ) -> RetrieveResult:
        """
        Retrieve relevant memories based on a query.

        Searches the memory store for relevant memory items.

        Args:
            query: Query string or list of conversation messages
            user_id: User ID for scoping (required)
            agent_id: Agent ID for scoping (required)

        Returns:
            RetrieveResult containing matching categories, items, and resources

        Example:
            # Simple text query
            result = await client.retrieve(
                query="What are the user's food preferences?",
                user_id="user_123",
                agent_id="agent_456"
            )

            # Conversation-aware query
            result = await client.retrieve(
                query=[
                    {"role": "user", "content": "What do they like?"},
                    {"role": "assistant", "content": "They have several preferences."},
                    {"role": "user", "content": "Tell me about food specifically"}
                ],
                user_id="user_123",
                agent_id="agent_456"
            )

            for item in result.items:
                print(f"[{item.memory_type}] {item.summary}")
        """
        # Build request payload matching API v3 schema
        payload: dict[str, Any] = {
            "user_id": user_id,
            "agent_id": agent_id,
            "query": query,
        }

        response = await self._request("POST", "/api/v3/memory/retrieve", json=payload)

        return RetrieveResult(
            categories=[
                MemoryCategory(**cat) if isinstance(cat, dict) else cat for cat in response.get("categories", [])
            ],
            items=[MemoryItem(**item) if isinstance(item, dict) else item for item in response.get("items", [])],
            resources=[
                MemoryResource(**res) if isinstance(res, dict) else res for res in response.get("resources", [])
            ],
            next_step_query=response.get("next_step_query"),
        )

    # =========================================================================
    # CATEGORIES API
    # =========================================================================

    async def list_categories(
        self,
        *,
        user_id: str,
        agent_id: str | None = None,
    ) -> list[MemoryCategory]:
        """
        List all memory categories.

        Args:
            user_id: User ID for scoping (required)
            agent_id: Agent ID for scoping (optional)

        Returns:
            List of MemoryCategory objects

        Example:
            categories = await client.list_categories(user_id="user_123")
            for cat in categories:
                print(f"{cat.name}: {cat.summary}")
        """
        payload: dict[str, Any] = {"user_id": user_id}

        if agent_id:
            payload["agent_id"] = agent_id

        response = await self._request("POST", "/api/v3/memory/categories", json=payload)

        categories_data = response.get("categories", response) if isinstance(response, dict) else response
        if isinstance(categories_data, list):
            return [MemoryCategory(**cat) if isinstance(cat, dict) else cat for cat in categories_data]
        return []

    # =========================================================================
    # SYNC WRAPPERS
    # =========================================================================

    def memorize_sync(
        self,
        *,
        conversation: list[dict[str, Any]] | None = None,
        conversation_text: str | None = None,
        user_id: str,
        agent_id: str,
        user_name: str = "User",
        agent_name: str = "Assistant",
        session_date: str | None = None,
        wait_for_completion: bool = False,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        timeout: float | None = None,
    ) -> MemorizeResult:
        """
        Synchronous wrapper for memorize().

        See memorize() for full documentation.
        """
        return asyncio.run(
            self.memorize(
                conversation=conversation,
                conversation_text=conversation_text,
                user_id=user_id,
                agent_id=agent_id,
                user_name=user_name,
                agent_name=agent_name,
                session_date=session_date,
                wait_for_completion=wait_for_completion,
                poll_interval=poll_interval,
                timeout=timeout,
            )
        )

    def retrieve_sync(
        self,
        query: str | list[dict[str, Any]],
        *,
        user_id: str,
        agent_id: str,
    ) -> RetrieveResult:
        """
        Synchronous wrapper for retrieve().

        See retrieve() for full documentation.
        """
        return asyncio.run(
            self.retrieve(
                query=query,
                user_id=user_id,
                agent_id=agent_id,
            )
        )

    def list_categories_sync(
        self,
        *,
        user_id: str,
        agent_id: str | None = None,
    ) -> list[MemoryCategory]:
        """
        Synchronous wrapper for list_categories().

        See list_categories() for full documentation.
        """
        return asyncio.run(
            self.list_categories(
                user_id=user_id,
                agent_id=agent_id,
            )
        )

    def get_task_status_sync(self, task_id: str) -> TaskStatus:
        """
        Synchronous wrapper for get_task_status().

        See get_task_status() for full documentation.
        """
        return asyncio.run(self.get_task_status(task_id))

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    @staticmethod
    def _is_local_file(path: str) -> bool:
        """Check if a path is a local file (not a URL)."""
        return not path.startswith(("http://", "https://", "s3://", "gs://"))

    @staticmethod
    def _read_local_file(path: str) -> tuple[bytes, str]:
        """Read a local file and determine its content type."""
        file_path = Path(path)
        if not file_path.exists():
            msg = f"File not found: {path}"
            raise FileNotFoundError(msg)

        content = file_path.read_bytes()
        content_type, _ = mimetypes.guess_type(path)
        return content, content_type or "application/octet-stream"

    @staticmethod
    def _encode_content(content: str | bytes) -> str:
        """Encode content as base64 string."""
        if isinstance(content, str):
            content = content.encode("utf-8")
        return base64.b64encode(content).decode("utf-8")

    async def close(self) -> None:
        """Close the HTTP client connection."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def close_sync(self) -> None:
        """Synchronous wrapper for close()."""
        asyncio.run(self.close())
