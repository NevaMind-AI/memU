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


class MemoryClient:
    """
    Memory API client for remote operations.

    All memory operations are performed through remote API calls.
    No direct database access - maintains clean client-server architecture.
    """

    def __init__(
        self,
        api_url: str = "http://localhost:8000",
        timeout: int = 30,
    ):
        """
        Initialize MemoryClient.

        Args:
            api_url: Remote API URL for memory operations (e.g., "http://remote-server:8000")
            timeout: Request timeout in seconds
        """
        self.api_url = api_url.rstrip('/')
        self.timeout = timeout
        self._memory_cache = {}  # Cache for loaded memories
        
        print(f"🌐 MemoryClient initialized with API: {self.api_url}")

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

    def get_memory_by_agent(self, agent_id: str, user_id: str) -> "Memory":
        """Get memory instance by agent_id and user_id

        Args:
            agent_id: Agent ID
            user_id: User ID (required)

        Returns:
            Memory instance for the specified agent and user
        """
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

    def save_memory(self, memory: "Memory") -> bool:
        """Save memory via API

        Args:
            memory: Memory instance to save

        Returns:
            bool: Whether save was successful
        """
        # Import here to avoid circular imports
        from .base import Memory
        
        if not isinstance(memory, Memory):
            print("Warning: Can only save Memory instances")
            return False
            
        # TODO: Implement API endpoint for memory saving
        print("Info: Memory saving via API endpoint not yet implemented")
        return True

    def update_memory_with_conversation(
        self, agent_id: str, user_id: str, conversation: List[Dict[str, str]]
    ) -> int:
        """Update memory with a conversation via API

        Args:
            agent_id: Agent ID
            user_id: User ID (required)
            conversation: List of conversation messages

        Returns:
            Number of memories updated
        """
        try:
            # Send conversation to API for processing
            response = self._make_api_request("POST", "memories/update-conversation", data={
                "agent_id": agent_id,
                "user_id": user_id,
                "conversation": conversation
            })
            
            # Clear cache to force reload
            key = f"{agent_id}:{user_id}"
            if key in self._memory_cache:
                del self._memory_cache[key]
                
            return response.get("updated_count", 0)
            
        except Exception as e:
            print(f"Warning: Failed to update memory via API: {e}")
            return 0

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
        Update profile information via API.

        Args:
            agent_id: Agent ID
            user_id: User ID
            profile_info: Profile information

        Returns:
            bool: Whether update was successful
        """
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
            print(f"Error updating profile via API: {e}")
            return False

    def update_events(self, agent_id: str, user_id: str, events: List[str]) -> bool:
        """
        Add events via API.

        Args:
            agent_id: Agent ID
            user_id: User ID
            events: Event list

        Returns:
            bool: Whether addition was successful
        """
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
            print(f"Error adding events via API: {e}")
            return False

    def get_memory_stats(self, agent_id: str) -> Dict[str, Any]:
        """
        Get Memory statistics via API.

        Args:
            agent_id: Agent ID

        Returns:
            Dict: Statistics information
        """
        try:
            return self._make_api_request("GET", f"memories/stats/{agent_id}")
        except Exception as e:
            print(f"Error getting memory stats via API: {e}")
            return {}
