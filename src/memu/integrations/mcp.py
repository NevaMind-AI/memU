import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from memu import MemoryService


class MemUMCPServer:
    """Standardized MCP Server implementation for MemU."""

    def __init__(self, memory_service: MemoryService, name: str = "memu"):
        if FastMCP is None:
            raise ImportError('mcp is not installed. Install it with `pip install "memu-py[mcp]"`')

        self.service = memory_service
        self.mcp = FastMCP(name=name)
        self._setup_tools()

    def _setup_tools(self) -> None:
        @self.mcp.tool()
        async def get_memory(query: str, user_id: str = "default_user") -> str:
            """Retrieve memory based on a natural language query.

            Args:
                query: The question or topic to retrieve memory for.
                user_id: The ID of the user to scope the memory to.
            """
            result = await self.service.retrieve(
                queries=[{"role": "user", "content": query}],
                where={"user_id": user_id},
                method="rag",
            )
            return json.dumps(result, indent=2)

        @self.mcp.tool()
        async def search_memory(
            query: str,
            user_id: str = "default_user",
            method: str = "rag",
            limit: int = 5,
        ) -> str:
            """Perform an advanced search in memory using RAG or LLM reasoning.

            Args:
                query: The search query.
                user_id: The ID of the user.
                method: The retrieval method ('rag' for fast, 'llm' for deep reasoning).
                limit: Maximum number of items to return.
            """
            result = await self.service.retrieve(
                queries=[{"role": "user", "content": query}],
                where={"user_id": user_id},
                method=method,
                limit=limit,
            )
            return json.dumps(result, indent=2)

        @self.mcp.tool()
        async def search_items(query: str, user_id: str = "default_user", limit: int = 10) -> str:
            """List specific memory items matching a query without full RAG reasoning.

            Args:
                query: The search text for items.
                user_id: The ID of the user.
                limit: Maximum number of items to return.
            """
            result = await self.service.list_memory_items(query=query, where={"user_id": user_id}, limit=limit)
            return json.dumps(result, indent=2)

        @self.mcp.tool()
        async def memorize(content: str, user_id: str = "default_user", modality: str = "conversation") -> str:
            """Inject new information into memory (Proactive Learning).

            Args:
                content: The text content to memorize.
                user_id: The ID of the user.
                modality: The type of content ('conversation', 'document', etc).
            """
            result = await self.service.memorize(resource_url=content, modality=modality, user={"user_id": user_id})
            return json.dumps(result, indent=2)

        @self.mcp.tool()
        async def list_categories(user_id: str = "default_user") -> str:
            """List hierarchical memory categories and their summaries.

            Args:
                user_id: The ID of the user.
            """
            result = await self.service.list_memory_categories(where={"user_id": user_id})
            return json.dumps(result, indent=2)

        @self.mcp.tool()
        async def create_memory_item(
            content: str,
            categories: list[str],
            memory_type: str = "fact",
            user_id: str = "default_user",
        ) -> str:
            """Manually create a specific memory item.

            Args:
                content: The content of the memory.
                categories: List of category names to associate with.
                memory_type: Type of memory ('fact', 'preference', 'skill', 'relationship').
                user_id: The ID of the user.
            """
            result = await self.service.create_memory_item(
                memory_type=memory_type,
                memory_content=content,
                memory_categories=categories,
                user={"user_id": user_id},
            )
            return json.dumps(result, indent=2)

        @self.mcp.tool()
        async def update_memory_item(
            item_id: str,
            content: str | None = None,
            categories: list[str] | None = None,
            memory_type: str | None = None,
            user_id: str = "default_user",
        ) -> str:
            """Update an existing memory item.

            Args:
                item_id: The ID of the memory item to update.
                content: New content (optional).
                categories: New list of categories (optional).
                memory_type: New memory type (optional).
                user_id: The ID of the user.
            """
            result = await self.service.update_memory_item(
                memory_id=item_id,
                memory_type=memory_type,
                memory_content=content,
                memory_categories=categories,
                user={"user_id": user_id},
            )
            return json.dumps(result, indent=2)

        @self.mcp.tool()
        async def delete_memory_item(item_id: str, user_id: str = "default_user") -> str:
            """Delete a specific memory item.

            Args:
                item_id: The ID of the memory item to delete.
                user_id: The ID of the user.
            """
            result = await self.service.delete_memory_item(memory_id=item_id, user={"user_id": user_id})
            return json.dumps(result, indent=2)

    def run(self) -> None:
        """Run the MCP server."""
        self.mcp.run()


def create_mcp_server(memory_service: MemoryService, **kwargs: Any) -> MemUMCPServer:
    """Helper to create and return a MemUMCPServer instance."""
    return MemUMCPServer(memory_service, **kwargs)
