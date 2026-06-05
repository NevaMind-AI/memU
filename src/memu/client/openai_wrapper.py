"""
OpenAI Client Wrapper for Auto-Recall Memory Injection.

Wraps OpenAI client to automatically inject recalled memories into prompts.
Fully opt-in and backward compatible.
"""

from __future__ import annotations

import asyncio
import inspect
from typing import TYPE_CHECKING, Any

from memu.utils.retrieve import normalize_retrieve_ranking

if TYPE_CHECKING:
    from memu.app.service import MemoryService


def _normalize_top_k(top_k: int) -> int:
    if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k <= 0:
        msg = "top_k must be a positive integer"
        raise ValueError(msg)
    return top_k


def _copy_user_data(user_data: dict[str, Any]) -> dict[str, Any]:
    return dict(user_data)


def _extract_text_from_message_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        text = content.get("text")
        return text if isinstance(text, str) else ""
    if isinstance(content, list):
        chunks: list[str] = []
        for part in content:
            if not isinstance(part, dict):
                continue
            text = part.get("text")
            if isinstance(text, str) and text:
                chunks.append(text)
        return "\n".join(chunks)
    return ""


def _append_recall_context(content: Any, recall_context: str) -> str | list[Any]:
    if isinstance(content, str):
        return content + recall_context
    if isinstance(content, list):
        copied_parts = [dict(part) if isinstance(part, dict) else part for part in content]
        copied_parts.append({"type": "text", "text": recall_context.lstrip("\n")})
        return copied_parts
    if content is None:
        return recall_context.lstrip("\n")
    return f"{content}{recall_context}"


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
        self._user_data = _copy_user_data(user_data)
        self._ranking = normalize_retrieve_ranking(ranking, default="salience")
        self._top_k = _normalize_top_k(top_k)

    def _extract_user_query(self, messages: list[dict]) -> str:
        """Extract the most recent user message."""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                return _extract_text_from_message_content(msg.get("content", ""))
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
            messages[0]["content"] = _append_recall_context(messages[0].get("content"), recall_context)
        else:
            messages.insert(0, {"role": "system", "content": recall_context.lstrip("\n")})

        return messages

    async def _retrieve_memories(self, query: str) -> list[dict]:
        """Retrieve relevant memories for the query."""
        try:
            result = await self._service.retrieve(
                queries=[{"role": "user", "content": query}],
                where=_copy_user_data(self._user_data),
                ranking=self._ranking,
            )
            items = result.get("items", [])
            if not isinstance(items, list):
                return []
            return items[: self._top_k]
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
            result = self._original.acreate(**kwargs)
        else:
            result = self._original.create(**kwargs)
        if inspect.isawaitable(result):
            return await result
        return result

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
            top_k: Maximum number of recalled memory items to inject
        """
        self._client = client
        self._service = service
        self._user_data = _copy_user_data(user_data)
        self._ranking = normalize_retrieve_ranking(ranking, default="salience")
        self._top_k = _normalize_top_k(top_k)

        # Wrap chat namespace
        self.chat = MemuChat(
            client.chat,
            service,
            self._user_data,
            self._ranking,
            self._top_k,
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
        top_k: Maximum number of recalled memory items to inject

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
        scope: dict[str, Any] = {}
    else:
        scope = _copy_user_data(user_data)
    if user_id:
        scope["user_id"] = user_id
    if agent_id:
        scope["agent_id"] = agent_id
    if session_id:
        scope["session_id"] = session_id

    return MemuOpenAIWrapper(client, service, scope, ranking, top_k)
