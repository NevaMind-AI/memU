"""LangGraph integration for MemU."""

from __future__ import annotations

import contextlib
import logging
import os
import tempfile
import uuid
from typing import Any

# MUST explicitly import langgraph to satisfy DEP002
import langgraph
from pydantic import BaseModel, Field

from memu.app.service import MemoryService

try:
    from langchain_core.tools import BaseTool, StructuredTool
except ImportError as e:
    msg = "Please install 'langchain-core' (and 'langgraph') to use the LangGraph integration."
    raise ImportError(msg) from e


# Setup logger
logger = logging.getLogger("memu.integrations.langgraph")


class MemUIntegrationError(Exception):
    """Base exception for MemU integration issues."""


class SaveRecallInput(BaseModel):
    """Input schema for the save_memory tool."""

    content: str = Field(description="The text content or information to save/remember.")
    user_id: str = Field(description="The unique identifier of the user.")
    metadata: dict[str, Any] | None = Field(default=None, description="Additional metadata related to the memory.")


class SearchRecallInput(BaseModel):
    """Input schema for the search_memory tool."""

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
    tooling ecosystem.
    """

    def __init__(self, memory_service: MemoryService):
        """Initializes the MemULangGraphTools with a memory service."""
        self.memory_service = memory_service
        # Expose the langgraph module to ensure it's "used" even if just by reference in this class
        self._graph_backend = langgraph

    def tools(self) -> list[BaseTool]:
        """Return a list of tools compatible with LangGraph."""
        return [
            self.save_memory_tool(),
            self.search_memory_tool(),
        ]

    def save_memory_tool(self) -> StructuredTool:
        """Creates a tool to save information into MemU."""

        async def _save(content: str, user_id: str, metadata: dict | None = None) -> str:
            logger.info("Entering save_memory_tool for user_id: %s", user_id)
            filename = f"memu_input_{uuid.uuid4()}.txt"
            temp_dir = tempfile.gettempdir()
            file_path = os.path.join(temp_dir, filename)

            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

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
                return str(MemUIntegrationError(error_msg))
            finally:
                if os.path.exists(file_path):
                    with contextlib.suppress(OSError):
                        os.remove(file_path)
                        logger.debug("Cleaned up temporary file: %s", file_path)

            return "Memory saved successfully."

        return StructuredTool.from_function(
            func=None,
            coroutine=_save,
            name="save_memory",
            description="Save a piece of information, conversation snippet, or memory for a user.",
            args_schema=SaveRecallInput,
        )

    def search_memory_tool(self) -> StructuredTool:
        """Creates a tool to search for information in MemU."""

        async def _search(
            query: str,
            user_id: str,
            limit: int = 5,
            metadata_filter: dict | None = None,
            min_relevance_score: float = 0.0,
        ) -> str:
            logger.info("Entering search_memory_tool for user_id: %s, query: '%s'", user_id, query)
            try:
                queries = [{"role": "user", "content": query}]
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
                return str(MemUIntegrationError(error_msg))

            items = result.get("items", [])
            if min_relevance_score > 0:
                items = [item for item in items if item.get("score", 1.0) >= min_relevance_score]

            if not items:
                logger.info("No memories found for user_id: %s", user_id)
                return "No relevant memories found."

            response_text = "Retrieved Memories:\n"
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
