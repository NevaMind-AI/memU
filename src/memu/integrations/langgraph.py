from __future__ import annotations

import contextlib
import logging
import os
import tempfile
import uuid
from typing import Any

from pydantic import BaseModel, Field

from memu.app.service import MemoryService

# Try to import from langchain_core, but allow failure if not installed yet
try:
    from langchain_core.tools import BaseTool, StructuredTool
except ImportError:
    # Define dummy BaseTool/StructuredTool for development/inspection purposes
    # if dependencies aren't present.
    class BaseTool:
        pass

    class StructuredTool:
        @classmethod
        def from_function(cls, *args, **kwargs):
            pass


# Setup logger
logger = logging.getLogger("memu.integrations.langgraph")


class MemUIntegrationError(Exception):
    """Base exception for MemU integration issues."""


class MemUConnectionError(MemUIntegrationError):
    """Exception raised when there is a connection issue with MemU service."""


class SaveRecallInput(BaseModel):
    """Input schema for the save_memory tool.

    Attributes:
        content: The text content or information to save/remember.
        user_id: The unique identifier of the user.
        metadata: Additional metadata related to the memory.
    """

    content: str = Field(description="The text content or information to save/remember.")
    user_id: str = Field(description="The unique identifier of the user.")
    metadata: dict[str, Any] | None = Field(default=None, description="Additional metadata related to the memory.")


class SearchRecallInput(BaseModel):
    """Input schema for the search_memory tool.

    Attributes:
        query: The search query to retrieve relevant memories.
        user_id: The unique identifier of the user.
        limit: Number of memories to retrieve.
        metadata_filter: Optional filter to apply to memory metadata.
        min_relevance_score: Minimum relevance score for retrieved memories.
    """

    query: str = Field(description="The search query to retrieve relevant memories.")
    user_id: str = Field(description="The unique identifier of the user.")
    limit: int = Field(default=5, description="Number of memories to retrieve.")
    metadata_filter: dict[str, Any] | None = Field(
        default=None, description="Optional filter for memory metadata (e.g., {'category': 'work'})."
    )
    min_relevance_score: float = Field(default=0.0, description="Minimum relevance score (0.0 to 1.0) for results.")


class MemULangGraphTools:
    """Adapter to expose MemU as a set of Tools for LangGraph/LangChain agents.

    This class provides a bridge between the MemU MemoryService and LangChain's
    tooling ecosystem, allowing agents to persist and retrieve information
    seamlessly.

    Args:
        memory_service: An instance of MemU MemoryService.

    Example:
        service = MemoryService(...)
        tools_bucket = MemULangGraphTools(service)
        tools = tools_bucket.tools()
    """

    def __init__(self, memory_service: MemoryService):
        """Initializes the MemULangGraphTools with a memory service."""
        self.memory_service = memory_service

    def tools(self) -> list[BaseTool]:
        """Return a list of tools compatible with LangGraph.

        Returns:
            A list of BaseTool objects (save_memory and search_memory).
        """
        return [
            self.save_memory_tool(),
            self.search_memory_tool(),
        ]

    def save_memory_tool(self) -> BaseTool:
        """Creates a tool to save information into MemU.

        Returns:
            A StructuredTool for saving memories.
        """

        async def _save(content: str, user_id: str, metadata: dict | None = None) -> str:
            """Internal implementation of save_memory.

            Args:
                content: The information to remember.
                user_id: The user associated with the memory.
                metadata: Optional metadata.

            Returns:
                A success or error message string.
            """
            logger.info("Entering save_memory_tool for user_id: %s", user_id)
            # Create a temporary file to hold the content, as MemU ingest expects a file path
            filename = f"memu_input_{uuid.uuid4()}.txt"
            temp_dir = tempfile.gettempdir()
            file_path = os.path.join(temp_dir, filename)

            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

                # Call MemU memorize
                logger.debug("Calling memory_service.memorize with temporary file: %s", file_path)
                await self.memory_service.memorize(
                    resource_url=file_path,
                    modality="conversation",
                    user={"user_id": user_id, **(metadata or {})},
                )
                logger.info("Successfully saved memory for user_id: %s", user_id)
            except Exception as e:
                error_msg = f"Failed to save memory for user {user_id}: {e!s}"
                logger.exception(error_msg)
                raise MemUIntegrationError(error_msg) from e
            finally:
                # Cleanup temp file
                if os.path.exists(file_path):
                    with contextlib.suppress(OSError):
                        os.remove(file_path)
                        logger.debug("Cleaned up temporary file: %s", file_path)

            return "Memory saved successfully."

        return StructuredTool.from_function(
            func=None,  # Async only
            coroutine=_save,
            name="save_memory",
            description="Save a piece of information, conversation snippet, or memory for a user.",
            args_schema=SaveRecallInput,
        )

    def search_memory_tool(self) -> BaseTool:
        """Creates a tool to search for information in MemU.

        Returns:
            A StructuredTool for searching memories.
        """

        async def _search(
            query: str,
            user_id: str,
            limit: int = 5,
            metadata_filter: dict | None = None,
            min_relevance_score: float = 0.0,
        ) -> str:
            """Internal implementation of search_memory.

            Args:
                query: The search query.
                user_id: The user whose memories to search.
                limit: Maximum number of results to return.
                metadata_filter: Optional metadata filter.
                min_relevance_score: Minimum relevance score (0.0 to 1.0).

            Returns:
                A formatted string containing retrieved memories or a 'not found' message.
            """
            logger.info("Entering search_memory_tool for user_id: %s, query: '%s'", user_id, query)
            try:
                # MemU retrieve expects a list of query objects
                queries = [{"role": "user", "content": query}]

                # Configure the retrieval scope via 'where'
                where_filter = {"user_id": user_id}
                if metadata_filter:
                    where_filter.update(metadata_filter)

                logger.debug("Calling memory_service.retrieve with where_filter: %s", where_filter)
                result = await self.memory_service.retrieve(
                    queries=queries,
                    where=where_filter,
                )
                logger.info("Successfully retrieved memories for user_id: %s", user_id)
            except Exception as e:
                error_msg = f"Failed to search memory for user {user_id}: {e!s}"
                logger.exception(error_msg)
                raise MemUIntegrationError(error_msg) from e

            # Format the result into a readable string for the LLM
            items = result.get("items", [])

            # Apply client-side relevance filter if requested
            if min_relevance_score > 0:
                items = [item for item in items if item.get("score", 1.0) >= min_relevance_score]

            if not items:
                logger.info("No memories found for user_id: %s", user_id)
                return "No relevant memories found."

            response_text = "Retrieved Memories:\n"
            # MemU returns items as dicts
            for idx, item in enumerate(items[:limit]):
                summary = item.get("summary", "")
                score = item.get("score", "N/A")
                response_text += f"{idx + 1}. [Score: {score}] {summary}\n"

            return response_text

        return StructuredTool.from_function(
            func=None,
            coroutine=_search,
            name="search_memory",
            description="Search for relevant memories or information for a user based on a query.",
            args_schema=SearchRecallInput,
        )


class MemUNode:
    """A production-ready node for LangGraph that wraps MemU tools.

    This class serves as a high-level integration point for LangGraph state
    machines, allowing for automated memory management within a graph.
    """

    def __init__(self, memory_service: MemoryService):
        """Initializes the node with a MemU service."""
        self.tools_bucket = MemULangGraphTools(memory_service)

    def get_tools(self) -> list[BaseTool]:
        """Returns the MemU tools for graph use."""
        return self.tools_bucket.tools()

    async def __call__(self, state: Any) -> dict[str, Any]:
        """Executes the node logic (placeholder for future graph state logic).

        Args:
            state: The current LangGraph state.

        Returns:
            A dictionary of updates to the state.
        """
        logger.info("MemUNode called with state: %s", state)
        return {"memu_status": "active"}
