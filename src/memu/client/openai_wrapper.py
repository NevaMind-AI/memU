"""
OpenAI Client Wrapper for Auto-Recall Memory Injection.

Wraps OpenAI client to automatically inject recalled memories into prompts.
Fully opt-in and backward compatible.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from memu.app.service import MemoryService


class MemuChatCompletions:
    """Wrapper for chat.completions that injects recalled memories."""

    def __init__(
        self,
        original_completions,
        service: MemoryService,
        user_data: dict[str, Any],
        ranking: str = "salience",
        top_k: int = 5,
    ):
        self._original = original_completions
        self._service = service
        self._user_data = user_data
        self._ranking = ranking
        self._top_k = top_k

    def _extract_user_query(self, messages: list[dict]) -> str:
        """Extract the most recent user message."""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, str):
                    return content
                # Handle content as list (vision models)
                if isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict) and part.get("type") == "text":
                            return part.get("text", "")
        return ""

    def _inject_memories(self, messages: list[dict], memories: list[dict]) -> list[dict]:
        """Inject recalled memories into the system prompt."""
        if not memories:
            return messages

        # Format memories as context
        memory_lines = [f"- {m.get('summary', '')}" for m in memories]
        recall_context = (
            "\n\n<memu_context>\n"
            "Relevant context about the user (use only if relevant to the query):\n"
            + "\n".join(memory_lines)
            + "\n</memu_context>"
        )

        # Clone messages to avoid mutation
        messages = [dict(m) for m in messages]

        # Inject into system message or create one
        if messages and messages[0].get("role") == "system":
            messages[0]["content"] = messages[0]["content"] + recall_context
        else:
            messages.insert(0, {"role": "system", "content": recall_context.lstrip("\n")})

        return messages

    async def _retrieve_memories(self, query: str) -> list[dict]:
        """Retrieve relevant memories for the query."""
        try:
            result = await self._service.retrieve(
                queries=[{"role": "user", "content": query}],
                where=self._user_data,
            )
            return result.get("items", [])
        except Exception:
            # Fail silently - don't break the LLM call
            return []

    def create(self, **kwargs) -> Any:
        """Wrapped create method with auto-recall injection."""
        messages = kwargs.get("messages", [])
        query = self._extract_user_query(messages)

        if query:
            # Run async retrieval in sync context
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Already in async context, create task
                    import concurrent.futures

                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        memories = pool.submit(asyncio.run, self._retrieve_memories(query)).result()
                else:
                    memories = loop.run_until_complete(self._retrieve_memories(query))
            except RuntimeError:
                memories = asyncio.run(self._retrieve_memories(query))

            if memories:
                kwargs["messages"] = self._inject_memories(messages, memories)

        return self._original.create(**kwargs)

    async def acreate(self, **kwargs) -> Any:
        """Async wrapped create method with auto-recall injection."""
        messages = kwargs.get("messages", [])
        query = self._extract_user_query(messages)

        if query:
            memories = await self._retrieve_memories(query)
            if memories:
                kwargs["messages"] = self._inject_memories(messages, memories)

        # Call original async method if available
        if hasattr(self._original, "acreate"):
            return await self._original.acreate(**kwargs)
        return self._original.create(**kwargs)

    def __getattr__(self, name: str) -> Any:
        """Proxy all other attributes to original."""
        return getattr(self._original, name)


class MemuChat:
    """Wrapper for chat namespace."""

    def __init__(
        self,
        original_chat,
        service: MemoryService,
        user_data: dict[str, Any],
        ranking: str = "salience",
        top_k: int = 5,
    ):
        self._original = original_chat
        self.completions = MemuChatCompletions(
            original_chat.completions,
            service,
            user_data,
            ranking,
            top_k,
        )

    def __getattr__(self, name: str) -> Any:
        """Proxy all other attributes to original."""
        return getattr(self._original, name)


class MemuOpenAIWrapper:
    """
    Wrapper around OpenAI client that auto-injects recalled memories.

    Usage:
        from openai import OpenAI
        from memu.client import MemuOpenAIWrapper

        client = OpenAI()
        service = MemoryService(...)

        wrapped = MemuOpenAIWrapper(
            client,
            service,
            user_data={"user_id": "user123"},
        )

        # Memories are automatically injected
        response = wrapped.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": "What's my favorite drink?"}]
        )
    """

    def __init__(
        self,
        client,
        service: MemoryService,
        user_data: dict[str, Any],
        ranking: str = "salience",
        top_k: int = 5,
    ):
        """
        Initialize the wrapper.

        Args:
            client: OpenAI client instance
            service: memU MemoryService instance
            user_data: User scope data (user_id, agent_id, session_id, etc.)
            ranking: Retrieval ranking strategy ("similarity" or "salience")
            top_k: Number of memories to retrieve
        """
        self._client = client
        self._service = service
        self._user_data = user_data
        self._ranking = ranking
        self._top_k = top_k

        # Wrap chat namespace
        self.chat = MemuChat(
            client.chat,
            service,
            user_data,
            ranking,
            top_k,
        )

    def __getattr__(self, name: str) -> Any:
        """Proxy all other attributes to original client."""
        return getattr(self._client, name)


def wrap_openai(
    client,
    service: MemoryService,
    user_data: dict[str, Any] | None = None,
    user_id: str | None = None,
    agent_id: str | None = None,
    session_id: str | None = None,
    ranking: str = "salience",
    top_k: int = 5,
) -> MemuOpenAIWrapper:
    """
    Wrap an OpenAI client for auto-recall memory injection.

    Args:
        client: OpenAI client instance
        service: memU MemoryService instance
        user_data: Full user scope dict (alternative to individual params)
        user_id: User identifier
        agent_id: Agent identifier (for multi-agent scoping)
        session_id: Session identifier
        ranking: Retrieval ranking ("similarity" or "salience")
        top_k: Number of memories to retrieve

    Returns:
        Wrapped client with auto-recall enabled

    Example:
        from openai import OpenAI
        from memu.client import wrap_openai

        client = wrap_openai(
            OpenAI(),
            service,
            user_id="user123",
            ranking="salience",
        )

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": "What do I like?"}]
        )
    """
    if user_data is None:
        user_data = {}
    if user_id:
        user_data["user_id"] = user_id
    if agent_id:
        user_data["agent_id"] = agent_id
    if session_id:
        user_data["session_id"] = session_id

    return MemuOpenAIWrapper(client, service, user_data, ranking, top_k)
