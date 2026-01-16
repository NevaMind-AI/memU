"""
MemU OpenAgents Adapter - Agent-level memory integration.

This adapter follows the OpenAgents BaseModAdapter pattern to provide
long-term memory capabilities to any agent in an OpenAgents network.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from memu.adapters.openagents.tools import (
    TOOL_SCHEMAS,
    get_memory,
    list_memories,
    memorize,
    retrieve,
    set_memu_service,
)

if TYPE_CHECKING:
    from memu.app.service import MemoryService

logger = logging.getLogger(__name__)


class MemUOpenAgentsAdapter:
    """
    OpenAgents adapter for MemU long-term memory.

    This adapter provides memory tools that can be registered with any
    OpenAgents agent, enabling persistent memory across conversations
    and agent restarts.

    Usage:
        from memu.app.service import MemoryService
        from memu.adapters.openagents import MemUOpenAgentsAdapter

        # Initialize MemU service
        service = MemoryService(
            llm_profiles={"default": {...}, "embedding": {...}},
            database_config={"metadata_store": {"provider": "sqlite"}},
        )

        # Create adapter
        adapter = MemUOpenAgentsAdapter(service=service)

        # Get tools for agent registration
        tools = adapter.get_tools()

        # Or use with OpenAgents agent
        agent.register_tools(adapter.get_tools())
    """

    def __init__(
        self,
        service: MemoryService,
        *,
        mod_name: str = "memu",
        auto_memorize: bool = False,
    ):
        """
        Initialize the MemU adapter.

        Args:
            service: MemoryService instance for memory operations
            mod_name: Name for this mod (default: "memu")
            auto_memorize: If True, automatically memorize agent conversations
        """
        self.service = service
        self.mod_name = mod_name
        self.auto_memorize = auto_memorize
        self.agent_id: str | None = None
        self._initialized = False

        # Set global service for tool functions
        set_memu_service(service)

        # Tool function mapping
        self._tool_funcs: dict[str, Callable[..., str]] = {
            "memorize": memorize,
            "retrieve": retrieve,
            "list_memories": list_memories,
            "get_memory": get_memory,
        }

    def initialize(self, agent_id: str | None = None) -> bool:
        """
        Initialize the adapter for an agent.

        Args:
            agent_id: Optional agent ID for scoping

        Returns:
            True if initialization successful
        """
        self.agent_id = agent_id
        self._initialized = True
        logger.info(f"MemU adapter initialized for agent: {agent_id or 'global'}")
        return True

    def shutdown(self) -> bool:
        """
        Shutdown the adapter.

        Returns:
            True if shutdown successful
        """
        self._initialized = False
        logger.info(f"MemU adapter shutdown for agent: {self.agent_id or 'global'}")
        return True

    def get_tools(self) -> list[dict[str, Any]]:
        """
        Get tool configurations for OpenAgents.

        Returns:
            List of tool configurations with name, description, input_schema, func
        """
        tools = []
        for name, schema in TOOL_SCHEMAS.items():
            tool_config = {
                "name": schema["name"],
                "description": schema["description"],
                "input_schema": schema["input_schema"],
                "func": self._tool_funcs[name],
            }
            tools.append(tool_config)
        return tools

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        """
        Get tool schemas for YAML configuration.

        Returns:
            List of tool schemas for agent YAML config
        """
        return list(TOOL_SCHEMAS.values())

    async def call_tool(self, tool_name: str, **kwargs: Any) -> str:
        """
        Call a MemU tool by name.

        Args:
            tool_name: Name of the tool to call
            **kwargs: Tool arguments

        Returns:
            Tool result as string
        """
        if tool_name not in self._tool_funcs:
            return f"❌ Unknown tool: {tool_name}"

        func = self._tool_funcs[tool_name]

        # Add agent_id as user_id if not provided
        if self.agent_id and "user_id" not in kwargs:
            kwargs["user_id"] = self.agent_id

        try:
            # Tools are sync, but we might be in async context
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Run in executor to avoid blocking
                result = await loop.run_in_executor(None, lambda: func(**kwargs))
            else:
                result = func(**kwargs)
            return result
        except Exception as e:
            logger.exception(f"Tool {tool_name} failed")
            return f"❌ Tool error: {e!s}"

    async def memorize_conversation(
        self,
        messages: list[dict[str, str]],
        user_id: str | None = None,
    ) -> str:
        """
        Memorize a conversation history.

        Args:
            messages: List of message dicts with 'role' and 'content'
            user_id: Optional user ID for scoping

        Returns:
            Status message
        """
        # Format conversation as text
        lines = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            lines.append(f"[{role}]: {content}")

        conversation_text = "\n".join(lines)

        return await self.call_tool(
            "memorize",
            content=conversation_text,
            modality="conversation",
            user_id=user_id or self.agent_id,
        )

    async def retrieve_context(
        self,
        query: str,
        top_k: int = 5,
        user_id: str | None = None,
    ) -> str:
        """
        Retrieve relevant context for a query.

        Args:
            query: The query to find context for
            top_k: Maximum results
            user_id: Optional user ID for scoping

        Returns:
            Retrieved context as formatted string
        """
        return await self.call_tool(
            "retrieve",
            query=query,
            top_k=top_k,
            user_id=user_id or self.agent_id,
        )

    def __repr__(self) -> str:
        return f"MemUOpenAgentsAdapter(agent_id={self.agent_id!r}, initialized={self._initialized})"
