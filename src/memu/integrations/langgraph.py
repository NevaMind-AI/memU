from __future__ import annotations

import contextlib
import os
import tempfile
import uuid
from typing import Any

from pydantic import BaseModel, Field

# Try to import from langchain_core, but allow failure if not installed yet
try:
    from langchain_core.tools import BaseTool, StructuredTool
except ImportError:
    # Define dummy BaseTool/StructuredTool for development/inspection purposes
    # if dependencies aren't present.
    # Ideally, the user installs dependencies before running this.
    class BaseTool:
        pass

    class StructuredTool:
        @classmethod
        def from_function(cls, *args, **kwargs):
            pass


from memu.app.service import MemoryService


class SaveRecallInput(BaseModel):
    content: str = Field(description="The text content or information to save/remember.")
    user_id: str = Field(description="The unique identifier of the user.")
    metadata: dict[str, Any] | None = Field(default=None, description="Additional metadata related to the memory.")


class SearchRecallInput(BaseModel):
    query: str = Field(description="The search query to retrieve relevant memories.")
    user_id: str = Field(description="The unique identifier of the user.")
    limit: int = Field(default=5, description="Number of memories to retrieve.")


class MemULangGraphTools:
    """
    Adapter to expose MemU as a set of Tools for LangGraph/LangChain agents.

    Usage:
        service = MemoryService(...)
        tools_bucket = MemULangGraphTools(service)
        tools = tools_bucket.tools()

        # Add to LangGraph ToolNode
        tool_node = ToolNode(tools)
    """

    def __init__(self, memory_service: MemoryService):
        self.memory_service = memory_service

    def tools(self) -> list[BaseTool]:
        """Return a list of tools compatible with LangGraph."""
        return [
            self.save_memory_tool(),
            self.search_memory_tool(),
        ]

    def save_memory_tool(self) -> BaseTool:
        async def _save(content: str, user_id: str, metadata: dict | None = None) -> str:
            # Create a temporary file to hold the content, as MemU ingest expects a file path
            # or URL.
            filename = f"memu_input_{uuid.uuid4()}.txt"
            temp_dir = tempfile.gettempdir()
            file_path = os.path.join(temp_dir, filename)

            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

                # Call MemU memorize
                await self.memory_service.memorize(
                    resource_url=file_path,
                    modality="conversation",
                    user={"user_id": user_id, **(metadata or {})},
                )
            except Exception as e:
                return f"Error saving memory: {e!s}"
            finally:
                # Cleanup temp file
                if os.path.exists(file_path):
                    with contextlib.suppress(OSError):
                        os.remove(file_path)

            return "Memory saved successfully."

        return StructuredTool.from_function(
            func=None,  # Async only
            coroutine=_save,
            name="save_memory",
            description="Save a piece of information, conversation snippet, or memory for a user.",
            args_schema=SaveRecallInput,
        )

    def search_memory_tool(self) -> BaseTool:
        async def _search(query: str, user_id: str, limit: int = 5) -> str:
            try:
                # MemU retrieve expects a list of query objects (chat history context)
                # For a simple tool, we treat the single query as the latest user message.
                queries = [{"role": "user", "content": query}]

                # We can configure the retrieval scope via 'where'
                where_filter = {"user_id": user_id}

                # We might want to override top_k if dynamic config supported,
                # but for now we rely on the service config.
                result = await self.memory_service.retrieve(
                    queries=queries,
                    where=where_filter,
                )
            except Exception as e:
                return f"Error searching memory: {e!s}"

            # Format the result into a readable string for the LLM
            response_text = "Retrieved Memories:\n"

            items = result.get("items", [])
            if not items:
                return "No relevant memories found."

            # MemU returns items as dicts (dumped models)
            for idx, item in enumerate(items[:limit]):
                summary = item.get("summary", "")
                # potentially include timestamp or other metadata
                response_text += f"{idx + 1}. {summary}\n"

            return response_text

        return StructuredTool.from_function(
            func=None,
            coroutine=_search,
            name="search_memory",
            description="Search for relevant memories or information for a user based on a query.",
            args_schema=SearchRecallInput,
        )
