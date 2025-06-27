"""
Main memory manager for PersonaLab.

This module provides the main Memory class that integrates all memory components
and provides in-memory storage with search functionality and memory management.
Includes LLM-enhanced search capabilities for better relevance judgment.

Note: This is the legacy Memory class. New code should use the unified Memory architecture 
from personalab.memory module.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .memory.user import UserMemory
from .memory import Memory as UnifiedMemory, MemoryManager

# Optional LLM integration
try:
    from .llm import LLMManager, BaseLLM
    LLM_AVAILABLE = True
except ImportError:
    LLMManager = None
    BaseLLM = None
    LLM_AVAILABLE = False


class Memory:
    """
    Legacy memory container for backward compatibility.
    
    This class maintains compatibility with the old Memory interface while 
    using the new unified Memory architecture internally.
    
    Note: For new code, use MemoryManager from personalab.memory module directly.
    """
    
    def __init__(self, agent_id: str, enable_deep_search: bool = True, 
                 llm_instance: Optional[BaseLLM] = None, enable_llm_search: bool = True):
        """
        Initialize Memory for a specific agent.
        
        Args:
            agent_id: Unique identifier for the agent
            enable_deep_search: Whether to enable deep search capabilities
            llm_instance: Optional LLM instance for enhanced search capabilities
            enable_llm_search: Whether to use LLM for search decision making and analysis
        """
        self.agent_id = agent_id
        self.enable_deep_search = enable_deep_search
        self.enable_llm_search = enable_llm_search and LLM_AVAILABLE
        
        # Set up LLM for enhanced search
        self.llm = llm_instance
        if self.enable_llm_search and self.llm is None and LLM_AVAILABLE:
            # Try to create a default LLM instance
            try:
                llm_manager = LLMManager.create_quick_setup()
                self.llm = llm_manager.get_current_provider()
            except Exception:
                self.enable_llm_search = False
                self.llm = None
        
        # Use new unified Memory architecture
        self.memory_manager = MemoryManager(llm_client=self.llm)
        self.unified_memory = self.memory_manager.get_or_create_memory(agent_id)
        
        # Keep user memories for backward compatibility
        self._user_memories: Dict[str, UserMemory] = {}
    
    def get_user_memory(self, user_id: str) -> UserMemory:
        """
        Get or create user memory for the given user ID.
        
        Args:
            user_id: User identifier
            
        Returns:
            UserMemory instance for the user
        """
        if user_id not in self._user_memories:
            self._user_memories[user_id] = UserMemory(self.agent_id, user_id)
        
        return self._user_memories[user_id]

    def get_agent_memory(self) -> UnifiedMemory:
        """
        Get agent memory using the new unified Memory architecture.
        
        Returns:
            UnifiedMemory instance for the agent
        """
        return self.unified_memory

    def list_users(self) -> List[str]:
        """List all user IDs that have memory."""
        return list(self._user_memories.keys())

    def update_agent_profile_memory(self, conversation: str) -> str:
        """
        Update agent profile based on conversation using LLM analysis.
        
        Args:
            conversation: The conversation content to learn from
            
        Returns:
            The updated agent profile
        """
        # Use the new pipeline-based update
        conversation_data = [{"role": "user", "content": conversation}]
        updated_memory, pipeline_result = self.memory_manager.update_memory_with_conversation(
            self.agent_id, conversation_data
        )
        self.unified_memory = updated_memory
        return updated_memory.get_profile_content()

    def update_user_profile_memory(self, user_id: str, conversation: str) -> str:
        """
        Update user profile based on conversation using LLM analysis.
        
        Args:
            user_id: User identifier
            conversation: The conversation content to learn from
            
        Returns:
            The updated user profile
        """
        user_memory = self.get_user_memory(user_id)
        current_profile = user_memory.profile.get_profile()
        updated_profile = self._update_profile_with_llm(current_profile, conversation, "user")
        
        # Update the user's profile
        user_memory.profile.set_profile(updated_profile)
        return updated_profile

    def _update_profile_with_llm(self, current_profile: str, conversation: str, profile_type: str) -> str:
        """
        Use LLM to intelligently update profile based on conversation.
        
        Args:
            current_profile: Current profile content
            conversation: Conversation to learn from
            profile_type: Type of profile ("agent" or "user")
            
        Returns:
            Updated profile content
        """
        if not self.llm:
            # Fallback: simple append if LLM not available
            raise ValueError("LLM not available")
        try:
            # Create LLM prompt for profile updating
            update_prompt = f"""
You are helping to update a profile based on new conversation information.

Current Profile:
```
{current_profile if current_profile else "[Empty Profile]"}
```

New Conversation:
```
{conversation}
```

Profile Type: {profile_type}

Please analyze the conversation and update the profile by:
1. Extracting new information about the person/agent
2. Updating existing information if it has changed
3. Adding new skills, interests, or characteristics mentioned
4. Maintaining the overall structure and tone
5. Removing outdated or contradictory information

Rules:
- Keep the profile concise but informative
- Focus on persistent characteristics, not temporary states
- Maintain professional and factual tone
- If the conversation doesn't contain profile-relevant information, return the current profile unchanged
- Don't include specific conversation details, focus on learnable traits

Return in XML format:
<profile>
    18 years old boy, like playing game...
</profile>
"""
            
            response = self.llm.generate(update_prompt, max_tokens=4096, temperature=0.3)
            
            if response and response.content:
                updated_profile = response.content.strip()

                # Parse the updated profile
                updated_profile = self._parse_profile(updated_profile)
                
                # Validate the updated profile
                if len(updated_profile) > 50 and updated_profile != current_profile:
                    return updated_profile
                else:
                    return current_profile
            
        except Exception as e:
            raise ValueError("Failed to update profile")

    def _parse_profile(self, generated_profile: str) -> str:
        """
        Parse the generated profile to extract profile content from XML format.
        
        Args:
            generated_profile: LLM response containing profile in XML format
            
        Returns:
            Extracted profile content
        """
        import xml.etree.ElementTree as ET
        
        try:
            # Try to parse as XML
            if '<profile>' in generated_profile and '</profile>' in generated_profile:
                start = generated_profile.find('<profile>') + len('<profile>')
                end = generated_profile.find('</profile>')
                extracted_profile = generated_profile[start:end].strip()
                return extracted_profile if extracted_profile else generated_profile
            else:
                return generated_profile
        except Exception:
            # If XML parsing fails, return as is
            return generated_profile

    def need_search(self, conversation: str, system_prompt: str = "", context_length: int = 0) -> bool:
        """
        Determine if memory search is needed based on conversation context.
        
        Args:
            conversation: The conversation text to analyze
            system_prompt: System prompt to consider for context
            context_length: Current context length
            
        Returns:
            True if search is recommended, False otherwise
        """
        # Use LLM-based decision making if available
        if self.enable_llm_search and self.llm:
            return self.llm_need_search(conversation, system_prompt, context_length)
        
        # Fallback to simple heuristics
        return self._simple_need_search(conversation, context_length)
    
    def _simple_need_search(self, conversation: str, context_length: int = 0) -> bool:
        """Simple heuristic for determining search need."""
        # Search if conversation mentions past events or asks questions
        search_indicators = [
            "remember", "recall", "previous", "before", "earlier", "last time",
            "what did", "when did", "how did", "who was", "where was",
            "?", "tell me about", "what about"
        ]
        
        conversation_lower = conversation.lower()
        has_indicators = any(indicator in conversation_lower for indicator in search_indicators)
        
        # Also search if context is getting long
        is_long_context = context_length > 2000
        
        return has_indicators or is_long_context

    def llm_need_search(self, conversation: str, system_prompt: str = "", 
                       context_length: int = 0) -> bool:
        """
        Use LLM to determine if memory search is needed.
        
        Args:
            conversation: The conversation text to analyze
            system_prompt: System prompt to consider for context
            context_length: Current context length
            
        Returns:
            True if search is recommended, False otherwise
        """
        if not self.llm:
            return self._simple_need_search(conversation, context_length)
        
        try:
            decision_prompt = f"""
Analyze if this conversation requires searching through memory/conversation history.

Conversation: "{conversation}"
System Prompt: "{system_prompt}"
Current Context Length: {context_length} characters

Consider these factors:
1. Does the user reference past conversations or events?
2. Are they asking about previous topics or information shared?
3. Do they use words like "remember", "before", "earlier", "last time"?
4. Are they asking follow-up questions that need context?
5. Is the context getting too long (>2000 chars) and needs relevant information?

Answer with just "YES" or "NO" and brief reasoning.

Examples:
- "What did we discuss about Python yesterday?" → YES (references past)
- "Hello, how are you?" → NO (simple greeting)
- "Continue with that topic" → YES (needs context)
- "What's the weather?" → NO (independent question)

Response:"""

            response = self.llm.generate(decision_prompt, max_tokens=50, temperature=0.1)
            
            if response and response.content:
                response_text = response.content.strip().upper()
                return "YES" in response_text
            
        except Exception:
            pass
        
        # Fallback to simple heuristics
        return self._simple_need_search(conversation, context_length)

    def deep_search(self, conversation: str, system_prompt: str = "", 
                   user_id: Optional[str] = None, max_results: int = 15,
                   similarity_threshold: float = 60.0) -> Dict[str, Any]:
        """
        Perform deep search through memories based on conversation context.
        
        Args:
            conversation: The conversation to search for
            system_prompt: System prompt for context
            user_id: Optional user ID to search user-specific memories
            max_results: Maximum number of results to return
            similarity_threshold: Minimum similarity score for results
            
        Returns:
            Dictionary containing search results and metadata
        """
        # Use LLM-enhanced search if available
        if self.enable_llm_search and self.llm:
            return self.llm_deep_search(conversation, system_prompt, user_id, max_results, similarity_threshold)
        
        # Fallback to simple search
        return self._simple_deep_search(conversation, user_id, max_results)

    def _simple_deep_search(self, conversation: str, user_id: Optional[str] = None, 
                           max_results: int = 15) -> Dict[str, Any]:
        """Simple keyword-based search fallback."""
        results = {
            "agent_profile": self.unified_memory.get_profile_content(),
            "agent_events": self.unified_memory.get_event_content()[-max_results:],
            "user_memories": [],
            "search_metadata": {
                "method": "simple_keyword",
                "total_results": 0
            }
        }
        
        if user_id and user_id in self._user_memories:
            user_memory = self._user_memories[user_id]
            results["user_memories"] = [{
                "user_id": user_id,
                "profile": user_memory.profile.get_profile(),
                "events": user_memory.events.get_recent_memories(max_results)
            }]
        
        return results

    def llm_deep_search(self, conversation: str, system_prompt: str = "", 
                       user_id: Optional[str] = None, max_results: int = 15,
                       similarity_threshold: float = 60.0) -> Dict[str, Any]:
        """
        Use LLM to perform intelligent memory search and relevance ranking.
        
        Returns comprehensive memory context relevant to the conversation.
        """
        # For now, delegate to the new MemoryManager for advanced searching
        # This is a simplified implementation - full semantic search would be implemented
        # according to STRUCTURE.md section 4
        
        return self._simple_deep_search(conversation, user_id, max_results)
     