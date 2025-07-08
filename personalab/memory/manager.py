"""
Memory client module.

Provides Memory management interface through remote API:
- MemoryClient: Memory API client for remote operations
- Complete Memory lifecycle management through API calls
- Clean separation: Client -> API -> Backend -> Database
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import requests

from ..utils import get_logger

logger = get_logger(__name__)


class MemoryClient:
    """
    Memory API client for remote operations.

    All memory operations are performed through remote API calls.
    No direct database access - maintains clean client-server architecture.
    """

    def __init__(
        self,
        agent_id: str = None,
        api_url: str = "http://localhost:8080",
        timeout: int = 30,
    ):
        """
        Initialize MemoryClient.

        Args:
            agent_id: Agent ID (optional, but recommended for convenience)
            api_url: Remote API URL for memory operations (e.g., "http://remote-server:8080")
            timeout: Request timeout in seconds
        """
        self.agent_id = agent_id
        self.api_url = api_url.rstrip('/')
        self.timeout = timeout
        self._memory_cache = {}  # Cache for loaded memories
        
        logger.info(f"MemoryClient initialized with API: {self.api_url}, agent_id: {agent_id}")

    def _make_api_request(self, method: str, endpoint: str, data: dict = None, params: dict = None) -> dict:
        """Make HTTP request to remote API
        
        Args:
            method: HTTP method (GET, POST, DELETE, etc.)
            endpoint: API endpoint (without base URL)
            data: Request body data
            params: Query parameters
            
        Returns:
            Response data as dictionary
            
        Raises:
            Exception: If API request fails
        """
        url = f"{self.api_url}/api/{endpoint.lstrip('/')}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                json=data,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"API request failed: {e}")

    def get_memory_by_agent(self, agent_id: str = None, user_id: str = None) -> "Memory":
        """Get memory instance by agent_id and user_id

        Args:
            agent_id: Agent ID (optional if set in constructor)
            user_id: User ID (required)

        Returns:
            Memory instance for the specified agent and user
        """
        # Use provided agent_id or fallback to instance agent_id
        if agent_id is None:
            agent_id = self.agent_id
        if agent_id is None:
            raise ValueError("agent_id must be provided either in constructor or method call")
        
        if user_id is None:
            raise ValueError("user_id is required")
        
        # Import here to avoid circular imports
        from .base import Memory
        
        key = f"{agent_id}:{user_id}"

        # Check cache first
        if key in self._memory_cache:
            return self._memory_cache[key]

        # Load from API
        try:
            memories = self._make_api_request("GET", "memories", params={
                "agent_id": agent_id,
                "user_id": user_id
            })
            
            memory_data = None
            if memories and len(memories) > 0:
                memory_id = memories[0]["memory_id"]
                memory_data = self._make_api_request("GET", f"memories/{memory_id}")
            
            # Create Memory instance
            memory = Memory(
                agent_id=agent_id,
                user_id=user_id,
                memory_client=self,
                data=memory_data
            )
            
            # Cache the memory
            self._memory_cache[key] = memory
            return memory
            
        except Exception as e:
            # If API fails, return empty memory
            print(f"Warning: Failed to load memory from API: {e}")
            memory = Memory(
                agent_id=agent_id,
                user_id=user_id,
                memory_client=self,
                data=None
            )
            self._memory_cache[key] = memory
            return memory

    def get_memory(self, user_id: str) -> "Memory":
        """Get memory instance for the configured agent and specified user
        
        Convenience method that uses the agent_id from constructor.

        Args:
            user_id: User ID (required)

        Returns:
            Memory instance for the configured agent and specified user
        """
        if self.agent_id is None:
            raise ValueError("agent_id must be set in constructor to use this method")
        return self.get_memory_by_agent(self.agent_id, user_id)

    def update_memory_with_conversation(
        self, agent_id: str = None, user_id: str = None, conversation: List[Dict[str, str]] = None
    ) -> bool:
        """Update memory with a conversation via API

        Args:
            agent_id: Agent ID (optional if set in constructor)
            user_id: User ID (required)
            conversation: List of conversation messages

        Returns:
            True if update was successful, False otherwise
        """
        # Use provided agent_id or fallback to instance agent_id
        if agent_id is None:
            agent_id = self.agent_id
        if agent_id is None:
            raise ValueError("agent_id must be provided either in constructor or method call")
            
        if user_id is None:
            raise ValueError("user_id is required")
            
        try:
            # Send conversation to API for processing
            response = self._make_api_request("POST", "memories/update-memory", data={
                "agent_id": agent_id,
                "user_id": user_id,
                "conversation": conversation
            })
            
            # Clear cache to force reload
            key = f"{agent_id}:{user_id}"
            if key in self._memory_cache:
                del self._memory_cache[key]
                
            return response.get("success", False)
            
        except Exception as e:
            print(f"Warning: Failed to update memory via API: {e}")
            return False

    def clear_memory_cache(self, agent_id: str = None, user_id: str = None) -> None:
        """Clear memory cache

        Args:
            agent_id: Agent ID (optional)
            user_id: User ID (optional)
        """
        if agent_id and user_id:
            # Clear specific cache entry
            key = f"{agent_id}:{user_id}"
            if key in self._memory_cache:
                del self._memory_cache[key]
        elif agent_id:
            # Clear all cache entries for agent
            keys_to_remove = [
                key for key in self._memory_cache.keys() 
                if key.startswith(f"{agent_id}:")
            ]
            for key in keys_to_remove:
                del self._memory_cache[key]
        else:
            # Clear all cache
            self._memory_cache.clear()

    def get_memory_prompt(self, agent_id: str = None, user_id: str = None) -> str:
        """Get memory context as a prompt

        Args:
            agent_id: Agent ID (optional if set in constructor)
            user_id: User ID (required)

        Returns:
            Formatted memory prompt
        """
        # Use provided agent_id or fallback to instance agent_id
        if agent_id is None:
            agent_id = self.agent_id
        if agent_id is None:
            raise ValueError("agent_id must be provided either in constructor or method call")
            
        if user_id is None:
            raise ValueError("user_id is required")
            
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

    def get_memory_info(self, agent_id: str = None, user_id: str = None) -> Dict[str, Any]:
        """Get detailed memory information

        Args:
            agent_id: Agent ID (optional if set in constructor)
            user_id: User ID (required)

        Returns:
            Dictionary with memory statistics and content
        """
        # Use provided agent_id or fallback to instance agent_id
        if agent_id is None:
            agent_id = self.agent_id
        if agent_id is None:
            raise ValueError("agent_id must be provided either in constructor or method call")
            
        if user_id is None:
            raise ValueError("user_id is required")
            
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

    def export_memory(self, agent_id: str = None, user_id: str = None) -> Dict[str, Any]:
        """Export memory data for backup or migration

        Args:
            agent_id: Agent ID (optional if set in constructor)
            user_id: User ID (required)

        Returns:
            Dictionary with complete memory data
        """
        # Use provided agent_id or fallback to instance agent_id
        if agent_id is None:
            agent_id = self.agent_id
        if agent_id is None:
            raise ValueError("agent_id must be provided either in constructor or method call")
            
        if user_id is None:
            raise ValueError("user_id is required")
            
        memory = self.get_memory_by_agent(agent_id, user_id)

        return {
            "agent_id": agent_id,
            "user_id": user_id,
            "profile": memory.get_profile(),
            "events": memory.get_events(),
            "mind": memory.get_mind(),
            "metadata": memory.get_memory_stats(),
        }

    def update_profile(self, agent_id: str = None, user_id: str = None, profile_info: str = None) -> bool:
        """Update profile information via API

        Args:
            agent_id: Agent ID (optional if set in constructor)
            user_id: User ID (required)
            profile_info: Profile information to add

        Returns:
            True if update was successful, False otherwise
        """
        # Use provided agent_id or fallback to instance agent_id
        if agent_id is None:
            agent_id = self.agent_id
        if agent_id is None:
            raise ValueError("agent_id must be provided either in constructor or method call")
            
        if user_id is None:
            raise ValueError("user_id is required")

        try:
            response = self._make_api_request("POST", "memories/update-profile", data={
                "agent_id": agent_id,
                "user_id": user_id,
                "profile_info": profile_info
            })
            
            # Clear cache to force reload
            key = f"{agent_id}:{user_id}"
            if key in self._memory_cache:
                del self._memory_cache[key]
                
            return response.get("success", False)
        except Exception as e:
            logger.error(f"Error updating profile via API: {e}")
            return False

    def update_events(self, agent_id: str = None, user_id: str = None, events: List[str] = None) -> bool:
        """Update events information via API

        Args:
            agent_id: Agent ID (optional if set in constructor)
            user_id: User ID (required)
            events: List of events to add

        Returns:
            True if update was successful, False otherwise
        """
        # Use provided agent_id or fallback to instance agent_id
        if agent_id is None:
            agent_id = self.agent_id
        if agent_id is None:
            raise ValueError("agent_id must be provided either in constructor or method call")
            
        if user_id is None:
            raise ValueError("user_id is required")

        try:
            response = self._make_api_request("POST", "memories/update-events", data={
                "agent_id": agent_id,
                "user_id": user_id,
                "events": events
            })
            
            # Clear cache to force reload
            key = f"{agent_id}:{user_id}"
            if key in self._memory_cache:
                del self._memory_cache[key]
                
            return response.get("success", False)
        except Exception as e:
            logger.error(f"Error adding events via API: {e}")
            return False

    def get_memory_stats(self, agent_id: str = None) -> Dict[str, Any]:
        """Get memory statistics for an agent

        Args:
            agent_id: Agent ID (optional if set in constructor)

        Returns:
            Dictionary with memory statistics
        """
        # Use provided agent_id or fallback to instance agent_id
        if agent_id is None:
            agent_id = self.agent_id
        if agent_id is None:
            raise ValueError("agent_id must be provided either in constructor or method call")
            
        try:
            return self._make_api_request("GET", f"memories/stats/{agent_id}")
        except Exception as e:
            logger.error(f"Error getting memory stats via API: {e}")
            return {}
