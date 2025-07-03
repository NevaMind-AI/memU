"""
Memory client module.

Provides unified Memory management interface, integrating Memory, Pipeline and Storage layers:
- MemoryClient: Main Memory client class
- Complete Memory lifecycle management implementation
- LLM integration support
- PostgreSQL backend with pgvector
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..config.database import DatabaseManager, get_database_manager
from .base import Memory
from .pipeline import MemoryUpdatePipeline, PipelineResult


class MemoryClient:
    """
    Memory client with database backend abstraction.

    Provides complete Memory lifecycle management, including:
    - Memory creation, loading, updating, saving
    - Pipeline execution and management
    - Database interaction (PostgreSQL)
    """

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        **llm_config,
    ):
        """
        Initialize MemoryClient.

        Args:
            db_manager: Optional database manager instance. If not provided, the global PostgreSQL manager will be used.
            **llm_config: LLM configuration parameters
        """
        # Use provided database manager or fallback to global one (PostgreSQL-only)
        self.db_manager = db_manager or get_database_manager()

        self.database = self.db_manager.get_memory_db()
        self.pipeline = MemoryUpdatePipeline(**llm_config)
        self._memory_cache = {}  # Cache for loaded memories

    def get_memory_by_agent(self, agent_id: str, user_id: str) -> Memory:
        """Get memory instance by agent_id and user_id

        Args:
            agent_id: Agent ID
            user_id: User ID (required)

        Returns:
            Memory instance for the specified agent and user
        """
        key = f"{agent_id}:{user_id}"

        # Check cache first
        if key in self._memory_cache:
            return self._memory_cache[key]

        # Try to load from database
        memory = self.database.get_memory_by_agent_and_user(agent_id, user_id)

        # If not found, create new memory
        if memory is None:
            memory = Memory(agent_id=agent_id, user_id=user_id)

        # Cache the memory
        self._memory_cache[key] = memory
        return memory

    def save_memory(self, memory: Memory) -> bool:
        """Save memory to database

        Args:
            memory: Memory instance to save

        Returns:
            bool: Whether save was successful
        """
        return self.database.save_memory(memory)

    def clear_memory(self, agent_id: str = None, user_id: str = None) -> None:
        """Clear memory data for specified agents/users

        Args:
            agent_id: Agent ID to clear (if None, clear all agents)
            user_id: User ID to clear (if None, clear all users)
        """
        if agent_id is None and user_id is None:
            # Clear all cached memories
            for memory in self._memory_cache.values():
                memory.clear_all()
            self._memory_cache.clear()
        elif agent_id is not None and user_id is not None:
            # Clear specific agent-user combination
            key = f"{agent_id}:{user_id}"
            if key in self._memory_cache:
                self._memory_cache[key].clear_all()
                del self._memory_cache[key]
        elif agent_id is not None:
            # Clear all memories for a specific agent
            to_remove = []
            for key, memory in self._memory_cache.items():
                if key.startswith(f"{agent_id}:"):
                    memory.clear_all()
                    to_remove.append(key)
            for key in to_remove:
                del self._memory_cache[key]
        elif user_id is not None:
            # Clear all memories for a specific user
            to_remove = []
            for key, memory in self._memory_cache.items():
                if key.endswith(f":{user_id}"):
                    memory.clear_all()
                    to_remove.append(key)
            for key in to_remove:
                del self._memory_cache[key]

    def update_memory_with_conversation(
        self, agent_id: str, user_id: str, conversation: List[Dict[str, str]]
    ) -> int:
        """Update memory with a conversation

        Args:
            agent_id: Agent ID
            user_id: User ID (required)
            conversation: List of conversation messages with 'user' and 'assistant' keys

        Returns:
            Number of memories updated
        """
        memory = self.get_memory_by_agent(agent_id, user_id)
        if not conversation:
            return 0

        # Convert conversation to memory format
        conversation_str = ""
        for turn in conversation:
            if "user" in turn and "assistant" in turn:
                conversation_str += (
                    f"User: {turn['user']}\nAssistant: {turn['assistant']}\n"
                )

        if conversation_str.strip():
            memory.add_events([conversation_str.strip()])
            return 1
        return 0

    def get_memory_prompt(self, agent_id: str, user_id: str) -> str:
        """Get memory context as a prompt

        Args:
            agent_id: Agent ID
            user_id: User ID (required)

        Returns:
            Formatted memory prompt
        """
        memory = self.get_memory_by_agent(agent_id, user_id)

        prompt_parts = []

        # Add profile information
        profile = memory.get_profile()
        if profile:
            prompt_parts.append(
                f"User Profile:\n{chr(10).join(f'- {p}' for p in profile)}"
            )

        # Add event history
        events = memory.get_events()
        if events:
            prompt_parts.append(
                f"Recent Events:\n{chr(10).join(f'- {e}' for e in events)}"
            )

        # Add psychological insights
        mind = memory.get_mind()
        if mind:
            prompt_parts.append(
                f"Psychological Insights:\n{chr(10).join(f'- {m}' for m in mind)}"
            )

        return "\n\n".join(prompt_parts) if prompt_parts else ""

    def get_memory_info(self, agent_id: str, user_id: str) -> Dict[str, Any]:
        """Get memory information and statistics

        Args:
            agent_id: Agent ID
            user_id: User ID (required)

        Returns:
            Dictionary containing memory statistics and information
        """
        memory = self.get_memory_by_agent(agent_id, user_id)

        profile = memory.get_profile()
        events = memory.get_events()
        mind = memory.get_mind()

        return {
            "agent_id": agent_id,
            "user_id": user_id,
            "profile_count": len(profile),
            "events_count": len(events),
            "mind_count": len(mind),
            "total_memories": len(profile) + len(events) + len(mind),
            "memory_stats": memory.get_memory_stats(),
        }

    def export_memory(self, agent_id: str, user_id: str) -> Dict[str, Any]:
        """Export all memory data for an agent-user combination

        Args:
            agent_id: Agent ID
            user_id: User ID (required)

        Returns:
            Dictionary containing all memory data
        """
        memory = self.get_memory_by_agent(agent_id, user_id)

        return {
            "agent_id": agent_id,
            "user_id": user_id,
            "profile": memory.get_profile(),
            "events": memory.get_events(),
            "mind": memory.get_mind(),
            "metadata": memory.get_memory_stats(),
        }

    def update_profile(self, agent_id: str, user_id: str, profile_info: str) -> bool:
        """
        Directly update profile information.

        Args:
            agent_id: Agent ID
            user_id: User ID
            profile_info: Profile information

        Returns:
            bool: Whether update was successful
        """
        try:
            memory = self.get_memory_by_agent(agent_id, user_id)
            memory.update_profile(profile_info)
            return self.database.save_memory(memory)
        except Exception as e:
            print(f"Error updating profile: {e}")
            return False

    def update_events(self, agent_id: str, user_id: str, events: List[str]) -> bool:
        """
        Directly add events.

        Args:
            agent_id: Agent ID
            user_id: User ID
            events: Event list

        Returns:
            bool: Whether addition was successful
        """
        try:
            memory = self.get_memory_by_agent(agent_id, user_id)
            memory.update_events(events)
            return self.database.save_memory(memory)
        except Exception as e:
            print(f"Error adding events: {e}")
            return False

    def import_memory(self, memory_data: Dict[str, Any]) -> bool:
        """
        Import Memory data.

        Args:
            memory_data: Memory data dictionary

        Returns:
            bool: Whether import was successful
        """
        try:
            # Create Memory object
            memory = Memory(
                agent_id=memory_data["agent_id"],
                user_id=memory_data.get("user_id"),
                memory_id=memory_data.get("memory_id"),
            )

            # Set timestamps
            if "created_at" in memory_data:
                memory.created_at = datetime.fromisoformat(memory_data["created_at"])
            if "updated_at" in memory_data:
                memory.updated_at = datetime.fromisoformat(memory_data["updated_at"])

            # Set Profile Memory
            if "profile_memory" in memory_data:
                profile_data = memory_data["profile_memory"]
                memory.update_profile(profile_data.get("content", ""))

            # Set Event Memory
            if "event_memory" in memory_data:
                event_data = memory_data["event_memory"]
                memory.update_events(event_data.get("content", []))

            # Set mind metadata
            if "mind_metadata" in memory_data:
                memory.mind_metadata = memory_data["mind_metadata"]
            elif "tom_metadata" in memory_data:  # Backward compatibility
                memory.mind_metadata = memory_data["tom_metadata"]

            # Save to database
            return self.database.save_memory(memory)

        except Exception as e:
            print(f"Error importing memory: {e}")
            return False

    def get_memory_stats(self, agent_id: str) -> Dict[str, Any]:
        """
        Get Memory statistics.

        Args:
            agent_id: Agent ID

        Returns:
            Dict: Statistics information
        """
        return self.database.get_memory_stats(agent_id)
