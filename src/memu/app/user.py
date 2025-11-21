from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from memu.app.service import MemoryService


class User:
    """User instance for performing memory operations with a specific user_id and agent_id.

    This class provides a clean API for user-specific memory operations.

    Example:
        service = MemoryService(llm_config=..., database_config=...)
        user = service.user(user_id="alice", agent_id="assistant_v1")

        # Memorize resources
        result = await user.memorize(
            resource_url="conversation.txt",
            modality="conversation"
        )

        # Retrieve memories
        queries = [{"role": "user", "content": {"text": "What did we discuss?"}}]
        retrieved = await user.retrieve(queries)
    """

    def __init__(self, service: MemoryService, user_id: str, agent_id: str):
        """Initialize User instance.

        Args:
            service: The MemoryService instance configured for this user
            user_id: User identifier
            agent_id: Agent identifier
        """
        self._service = service
        self.user_id = user_id
        self.agent_id = agent_id

    async def memorize(
        self,
        *,
        resource_url: str,
        modality: str,
        summary_prompt: str | None = None,
    ) -> dict[str, Any]:
        """Memorize a resource for this user.

        Args:
            resource_url: URL or path to the resource
            modality: Type of resource (conversation, document, image, video, audio)
            summary_prompt: Optional custom summary prompt

        Returns:
            Dictionary containing created resources, items, categories, and relationships
        """
        return await self._service.memorize(
            resource_url=resource_url,
            modality=modality,
            summary_prompt=summary_prompt,
        )

    async def retrieve(self, queries: list[dict[str, Any]]) -> dict[str, Any]:
        """Retrieve relevant memories for this user based on queries.

        Args:
            queries: List of query messages in format [{"role": "user", "content": {"text": "..."}}]

        Returns:
            Dictionary containing:
            - needs_retrieval: bool - Whether retrieval was performed
            - rewritten_query: str - Query after rewriting with context
            - next_step_query: str | None - Suggested query for next retrieval step
            - categories: list - Retrieved categories
            - items: list - Retrieved items
            - resources: list - Retrieved resources
        """
        return await self._service.retrieve(queries=queries)

    @property
    def store(self) -> Any:
        """Access to the underlying storage."""
        return self._service.store

    def __repr__(self) -> str:
        return f"User(user_id={self.user_id!r}, agent_id={self.agent_id!r})"
