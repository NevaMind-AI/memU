"""
Main memory manager for PersonaLab.

This module provides the main Memory class that integrates all memory components
and provides in-memory storage with search functionality and memory management.
Includes LLM-enhanced search capabilities for better relevance judgment.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .memory.agent import AgentMemory
from .memory.user import UserMemory

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
    Main memory container that manages both user and agent memories in-memory.
    Provides search functionality and memory management without persistence.
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
        
        # Create new memory
        self.agent_memory = AgentMemory(agent_id)
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

    def get_agent_memory(self) -> AgentMemory:
        """Get agent memory."""
        return self.agent_memory

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
        current_profile = self.agent_memory.profile.get_profile()
        return self._update_profile_with_llm(current_profile, conversation, "agent")

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
                    # Auto-update agent profile if this is agent profile update
                    if profile_type == "agent":
                        self.agent_memory.profile.set_profile(updated_profile)
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
        import re
        
        # Try to extract content from <profile> tags
        profile_match = re.search(r'<profile>\s*(.*?)\s*</profile>', generated_profile, re.DOTALL | re.IGNORECASE)
        
        if profile_match:
            # Found profile tags, extract the content
            profile_content = profile_match.group(1).strip()
            return profile_content
        else:
            # No XML tags found, try to clean up the response
            # Remove common XML-like patterns that might be incomplete
            profile = re.sub(r'</?profile[^>]*>', '', generated_profile, flags=re.IGNORECASE)
            profile = profile.strip()
            
            # If the cleaned response is reasonable, return it
            if len(profile) > 10:
                return profile
            else:
                # Fall back to original response if cleaning didn't work
                return generated_profile.strip()

   

    def need_search(self, conversation: str, system_prompt: str = "", context_length: int = 0) -> bool:
        """
        Determine if memory search is needed using LLM-based analysis.
        
        This function now uses LLM by default for intelligent search decisions,
        falling back to basic patterns only if LLM is unavailable.
        
        Args:
            conversation: Current conversation text
            system_prompt: System prompt being used
            context_length: Length of existing context (tokens or characters)
            
        Returns:
            True if memory search should be performed
        """
        # Always try LLM first if available
        if self.enable_llm_search and self.llm:
            return self.llm_need_search(conversation, system_prompt, context_length)
        
        # Fallback to basic search only if LLM unavailable (conservative approach)
        return False

    def llm_need_search(self, conversation: str, system_prompt: str = "", 
                       context_length: int = 0) -> bool:
        """
        Use LLM to determine if memory search is needed.
        
        This function leverages LLM's natural language understanding to make 
        more intelligent decisions about when memory search is beneficial.
        
        Args:
            conversation: Current conversation text
            system_prompt: System prompt being used
            context_length: Length of existing context
            
        Returns:
            True if LLM determines memory search should be performed
        """
        if not self.enable_llm_search or not self.llm:
            # Fallback to basic search (conservative approach)
            return False
        
        try:
            # Prepare LLM prompt for search decision
            decision_prompt = f"""
You are helping decide whether to search memory for relevant context. 


System prompt: "{system_prompt}"
Conversation: "{conversation}"

Consider these factors:
1. Does the query reference past conversations, memories, or personal information?
2. Are there pronouns or references that need context to understand?
3. Does the query ask about ongoing projects, relationships, or personal details?
4. Would knowing previous interactions help provide a better response?
5. Is this a continuation of a previous topic?

Respond with only "YES" if memory search would be helpful, or "NO" if not needed.
Be conservative - only suggest search when it would meaningfully improve the response.
"""
            
            # Get LLM response
            response = self.llm.generate(decision_prompt, max_tokens=10, temperature=0.1)
            
            if response and response.content:
                decision = response.content.strip().upper()
                return decision.startswith("YES")
                
        except Exception as e:
            # Fallback on error
            pass

        return False

    
    def deep_search(self, conversation: str, system_prompt: str = "", 
                   user_id: Optional[str] = None, max_results: int = 15,
                   similarity_threshold: float = 60.0) -> Dict[str, Any]:
        """
        Perform advanced deep search using LLM-enhanced analysis by default.
        
        This function now uses LLM for intelligent search and ranking,
        falling back to keyword-based search only when LLM is unavailable.
        
        Args:
            conversation: Current conversation text
            system_prompt: System prompt being used
            user_id: Optional user ID to search user-specific memory
            max_results: Maximum number of results to return
            similarity_threshold: Minimum similarity score to include results
            
        Returns:
            Dictionary containing LLM-enhanced search results with metadata
        """
        # Always try LLM-enhanced search first if available
        if self.enable_llm_search and self.llm:
            return self.llm_deep_search(conversation, system_prompt, user_id, max_results, similarity_threshold)
        
        # Fallback to basic search if LLM unavailable
        raise ValueError("LLM not available")

    def llm_deep_search(self, conversation: str, system_prompt: str = "", 
                       user_id: Optional[str] = None, max_results: int = 15,
                       similarity_threshold: float = 60.0) -> Dict[str, Any]:
        """
        Perform LLM-enhanced deep search with intelligent relevance judgment.
        
        This function uses LLM to:
        - Better understand search intent
        - Judge relevance of search results
        - Provide more contextual search term extraction
        - Enhance result ranking based on semantic understanding
        
        Args:
            conversation: Current conversation text
            system_prompt: System prompt being used
            user_id: Optional user ID to search user-specific memory
            max_results: Maximum number of results to return
            similarity_threshold: Minimum similarity score to include results
            
        Returns:
            Dictionary containing LLM-enhanced search results
        """
     