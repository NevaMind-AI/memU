"""
MemU SDK HTTP Client

Provides HTTP client for interacting with MemU API services.
"""

from datetime import datetime
import os
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import httpx
from pydantic import ValidationError

from .exceptions import (
    MemuAPIException,
    MemuAuthenticationException,
    MemuConnectionException,
    MemuValidationException,
)
from .models import (
    ChatRequest,
    ChatResponse,
    DefaultCategoriesRequest,
    DefaultCategoriesResponse,
    DeleteMemoryRequest,
    DeleteMemoryResponse,
    MemorizeRequest,
    MemorizeResponse,
    MemorizeTaskStatusResponse,
    RelatedClusteredCategoriesRequest,
    RelatedClusteredCategoriesResponse,
    RelatedMemoryItemsRequest,
    RelatedMemoryItemsResponse,
    MemorizeTaskSummaryReadyRequest,
    MemorizeTaskSummaryReadyResponse,
)

from ...utils.logging import get_logger

logger = get_logger(__name__)


class MemuClient:
    """HTTP client for MemU API services"""

    def __init__(
        self,
        base_url: str = None,
        api_key: str = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        **kwargs,
    ):
        """
        Initialize MemU SDK client

        Args:
            base_url: Base URL for MemU API server
            api_key: API key for authentication
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
            **kwargs: Additional httpx client parameters
        """
        self.base_url = base_url or os.getenv(
            "MEMU_API_BASE_URL", "http://localhost:8000"
        )
        self.api_key = api_key or os.getenv("MEMU_API_KEY")
        self.timeout = timeout
        self.max_retries = max_retries

        if not self.base_url:
            raise ValueError(
                "base_url is required. Set MEMU_API_BASE_URL environment variable or pass base_url parameter."
            )

        if not self.api_key:
            raise ValueError(
                "api_key is required. Set MEMU_API_KEY environment variable or pass api_key parameter."
            )

        # Ensure base_url ends with /
        if not self.base_url.endswith("/"):
            self.base_url += "/"

        # Configure httpx client
        client_kwargs = {
            "timeout": self.timeout,
            "headers": {
                "User-Agent": "MemU-Python-SDK/0.1.3",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            **kwargs,
        }

        self._client = httpx.Client(**client_kwargs)

        logger.info(f"MemU SDK client initialized with base_url: {self.base_url}")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

    def close(self):
        """Close the HTTP client"""
        if hasattr(self, "_client"):
            self._client.close()

    def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Dict[str, Any] = None,
        params: Dict[str, Any] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Make HTTP request with error handling and retries

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (relative to base_url)
            json_data: JSON request body
            params: Query parameters
            **kwargs: Additional request parameters

        Returns:
            Dict[str, Any]: Response JSON data

        Raises:
            MemuAPIException: For API errors
            MemuConnectionException: For connection errors
        """
        url = urljoin(self.base_url, endpoint)

        # Prepare query parameters if provided
        if params is None:
            params = {}

        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(
                    f"Making {method} request to {url} (attempt {attempt + 1})"
                )

                response = self._client.request(
                    method=method, url=url, json=json_data, params=params, **kwargs
                )

                # Handle HTTP status codes
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 422:
                    error_data = response.json()
                    raise MemuValidationException(
                        f"Validation error: {error_data}",
                        status_code=response.status_code,
                        response_data=error_data,
                    )
                elif response.status_code == 401:
                    raise MemuAuthenticationException(
                        "Authentication failed. Check your API key.",
                        status_code=response.status_code,
                    )
                elif response.status_code == 403:
                    raise MemuAuthenticationException(
                        "Access forbidden. Check your API key permissions.",
                        status_code=response.status_code,
                    )
                else:
                    error_msg = f"API request failed with status {response.status_code}"
                    try:
                        error_data = response.json()
                        error_msg += f": {error_data}"
                    except Exception:
                        error_msg += f": {response.text}"

                    raise MemuAPIException(error_msg, status_code=response.status_code)

            except httpx.RequestError as e:
                if attempt == self.max_retries:
                    raise MemuConnectionException(
                        f"Connection error after {self.max_retries + 1} attempts: {str(e)}"
                    )
                else:
                    logger.warning(
                        f"Request failed (attempt {attempt + 1}), retrying: {str(e)}"
                    )
                    continue
            except (
                MemuAPIException,
                MemuValidationException,
                MemuAuthenticationException,
            ):
                # Don't retry these errors
                raise

    def memorize_conversation(
        self,
        conversation: str | list[dict[str, str]],
        user_id: str,
        user_name: str,
        agent_id: str,
        agent_name: str,
        session_date: str | None = None,
    ) -> MemorizeResponse:
        """
        Start a Celery task to memorize conversation text with agent processing

        Args:
            conversation: Conversation content to memorize, either as a string or a list of dictionaries
            user_id: User identifier
            user_name: User display name
            agent_id: Agent identifier
            agent_name: Agent display name
            session_date: Session date in ISO 8601 format (optional)

        Returns:
            MemorizeResponse: Task ID and status for tracking the memorization process

        Raises:
            MemuValidationException: For validation errors
            MemuAPIException: For API errors
            MemuConnectionException: For connection errors
        """
        try:
            _conversation = {}
            if isinstance(conversation, str):
                _conversation["conversation_text"] = conversation
            elif isinstance(conversation, list):
                _conversation["conversation"] = conversation
            else:
                raise ValueError("Conversation must be as a string for flatten text, or as a list of dictionaries for structured messages")

            if session_date:
                # We now force a format check
                try:
                    _ = datetime.fromisoformat(session_date)
                except Exception as e:
                    raise ValueError(f"Failed to validate session date: {session_date}. Please confirm it matches the ISO 8601 format")
            else:
                session_date = datetime.now().astimezone().isoformat()

            # Create request model
            request_data = MemorizeRequest(
                **_conversation,
                user_id=user_id,
                user_name=user_name,
                agent_id=agent_id,
                agent_name=agent_name,
                session_date=session_date,
            )

            logger.info(
                f"Starting memorization for user {user_id} and agent {agent_id}"
            )

            # Make API request
            response_data = self._make_request(
                method="POST",
                endpoint="api/v2/memory/memorize",
                json_data=request_data.model_dump(),
            )

            # Parse response
            response = MemorizeResponse(**response_data)
            logger.info(f"Memorization task started: {response.task_id}")

            return response

        except ValidationError as e:
            raise MemuValidationException(f"Request validation failed: {str(e)}")

    def get_task_status(self, task_id: str) -> MemorizeTaskStatusResponse:
        """
        Get the status of a memorization task

        Args:
            task_id: Task identifier returned from memorize_conversation

        Returns:
            MemorizeTaskStatusResponse: Task status, progress, and results

        Raises:
            MemuValidationException: For validation errors
            MemuAPIException: For API errors
            MemuConnectionException: For connection errors
        """
        try:
            logger.info(f"Getting status for task: {task_id}")

            # Make API request to the correct endpoint
            response_data = self._make_request(
                method="GET", endpoint=f"api/v2/memory/memorize/status/{task_id}"
            )

            # Parse response using the model
            response = MemorizeTaskStatusResponse(**response_data)
            logger.debug(f"Task {task_id} status: {response.status}")

            return response

        except ValidationError as e:
            raise MemuValidationException(f"Response validation failed: {str(e)}")

    def retrieve_default_categories(
        self,
        *,
        user_id,
        agent_id: str | None = None,
        want_memory_items: bool = False,
    ) -> DefaultCategoriesResponse:
        """
        Retrieve default categories for a project

        Args:
            user_id: User ID
            agent_id: Agent ID (None for all agents)
            want_memory_items: Whether to return memory items instead of summary

        Returns:
            DefaultCategoriesResponse: Default categories information

        Raises:
            MemuValidationException: For validation errors
            MemuAPIException: For API errors
            MemuConnectionException: For connection errors
        """
        try:
            # Create request model
            request_data = DefaultCategoriesRequest(
                user_id=user_id, agent_id=agent_id, want_memory_items=want_memory_items
            )

            # Make API request
            response_data = self._make_request(
                method="POST",
                endpoint="api/v2/memory/retrieve/default-categories",
                json_data=request_data.model_dump(),
            )

            # Parse response
            response = DefaultCategoriesResponse(**response_data)
            logger.info(f"Retrieved {response.total_categories} categories")

            return response

        except ValidationError as e:
            raise MemuValidationException(f"Request validation failed: {str(e)}")

    def retrieve_related_memory_items(
        self,
        *,
        user_id: str,
        agent_id: str | None = None,
        query: str,
        top_k: int = 10,
        min_similarity: float = 0.3,
        include_categories: Optional[List[str]] = None,
    ) -> RelatedMemoryItemsResponse:
        """
        Retrieve related memory items for a user query

        Args:
            user_id: User ID
            agent_id: Agent ID (None for all agents)
            query: Search query for memory retrieval
            top_k: Number of top results to return
            min_similarity: Minimum similarity threshold
            include_categories: Categories to include in search

        Returns:
            RelatedMemoryItemsResponse: Related memory items

        Raises:
            MemuValidationException: For validation errors
            MemuAPIException: For API errors
            MemuConnectionException: For connection errors
        """
        try:
            # Create request model
            request_data = RelatedMemoryItemsRequest(
                user_id=user_id,
                agent_id=agent_id,
                query=query,
                top_k=top_k,
                min_similarity=min_similarity,
                include_categories=include_categories,
            )

            logger.info(
                f"Retrieving related memories for user {user_id}, query: '{query}'"
            )

            # Make API request
            response_data = self._make_request(
                method="POST",
                endpoint="api/v2/memory/retrieve/related-memory-items",
                json_data=request_data.model_dump(),
            )

            # Parse response
            response = RelatedMemoryItemsResponse(**response_data)
            logger.info(f"Retrieved {response.total_found} related memories")

            return response

        except ValidationError as e:
            raise MemuValidationException(f"Request validation failed: {str(e)}")

    def retrieve_related_clustered_categories(
        self,
        *,
        user_id: str,
        agent_id: str | None = None,
        category_query: str,
        top_k: int = 5,
        min_similarity: float = 0.3,
        want_summary: bool = True,
    ) -> RelatedClusteredCategoriesResponse:
        """
        Retrieve related clustered categories for a user

        Args:
            user_id: User ID
            agent_id: Agent ID (None for all agents)
            category_query: Category search query
            top_k: Number of top categories to return
            min_similarity: Minimum similarity threshold
            want_summary: Whether to return summary instead of raw memory items

        Returns:
            RelatedClusteredCategoriesResponse: Related clustered categories

        Raises:
            MemuValidationException: For validation errors
            MemuAPIException: For API errors
            MemuConnectionException: For connection errors
        """
        try:
            # Create request model
            request_data = RelatedClusteredCategoriesRequest(
                user_id=user_id,
                agent_id=agent_id,
                category_query=category_query,
                top_k=top_k,
                min_similarity=min_similarity,
                want_summary=want_summary,
            )

            logger.info(
                f"Retrieving clustered categories for user {user_id}, query: '{category_query}'"
            )

            # Make API request
            response_data = self._make_request(
                method="POST",
                endpoint="api/v2/memory/retrieve/related-clustered-categories",
                json_data=request_data.model_dump(),
            )

            # Parse response
            response = RelatedClusteredCategoriesResponse(**response_data)
            logger.info(
                f"Retrieved {response.total_categories_found} clustered categories"
            )

            return response

        except ValidationError as e:
            raise MemuValidationException(f"Request validation failed: {str(e)}")

    def delete_memories(
        self,
        user_id: str,
        agent_id: str | None = None,
    ) -> DeleteMemoryResponse:
        """
        Delete memories for a given user. If agent_id is provided, delete only that agent's memories; 
        otherwise delete all memories for the user within the project.

        Args:
            user_id: User identifier
            agent_id: Agent identifier (optional, delete all user memories if not provided)

        Returns:
            DeleteMemoryResponse: Response with deletion status and count

        Raises:
            MemuValidationException: For validation errors
            MemuAPIException: For API errors
            MemuConnectionException: For connection errors
        """
        try:
            # Create request model
            request_data = DeleteMemoryRequest(
                user_id=user_id,
                agent_id=agent_id,
            )

            logger.info(
                f"Deleting memories for user {user_id}"
                + (f" and agent {agent_id}" if agent_id else " (all agents)")
            )

            # Make API request
            response_data = self._make_request(
                method="POST",
                endpoint="api/v2/memory/delete",
                json_data=request_data.model_dump(),
            )

            # Parse response
            response = DeleteMemoryResponse(**response_data)
            logger.info(
                f"Successfully deleted memories: {response.deleted_count} memories deleted"
            )

            return response

        except ValidationError as e:
            raise MemuValidationException(f"Request validation failed: {str(e)}")

    def chat(
        self,
        *,
        user_id: str,
        agent_id: str,
        message: str,
        user_name: Optional[str] = None,
        agent_name: Optional[str] = None,
        system: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs,
    ) -> ChatResponse:
        """
        Send a chat message to the agent with memory-enhanced conversation
        
        Args:
            user_id: User identifier
            agent_id: Agent identifier  
            message: User message content
            user_name: User display name (optional)
            agent_name: Agent display name (optional)
            system: System message content (optional)
            model: Chat LLM model (optional)
            **kwargs: Additional parameters for LLM (e.g., temperature, max_tokens, etc.)
        
        Returns:
            ChatResponse: AI response with token usage information
            
        Raises:
            MemuValidationException: For validation errors
            MemuAPIException: For API errors
            MemuConnectionException: For connection errors
        """
        try:
            # Create request model
            request_data = ChatRequest(
                user_id=user_id,
                user_name=user_name,
                agent_id=agent_id,
                agent_name=agent_name,
                message=message,
                system=system,
                model=model,
                kwargs=kwargs,
            )

            logger.info(
                f"Sending chat message for user {user_id} and agent {agent_id}"
            )

            # Make API request
            response_data = self._make_request(
                method="POST",
                endpoint="api/v2/chat",
                json_data=request_data.model_dump(),
            )

            # Parse response
            response = ChatResponse(**response_data)
            logger.info(f"Chat response received: {len(response.message)} characters")

            return response

        except ValidationError as e:
            raise MemuValidationException(f"Request validation failed: {str(e)}")
