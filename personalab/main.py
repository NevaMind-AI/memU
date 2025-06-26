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

    def get_memory_info(self) -> Dict[str, Any]:
        """Get information about memory usage."""
        return {
            "agent_id": self.agent_id,
            "agent_profile_length": len(self.agent_memory.profile.get_profile()),
            "agent_events_count": len(self.agent_memory.events._memories),
            "user_count": len(self._user_memories),
            "users": {
                user_id: {
                    "profile_length": len(memory.profile.get_profile()),
                    "events_count": len(memory.events._memories)
                }
                for user_id, memory in self._user_memories.items()
            }
        }

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
        updated_profile = self._update_profile_with_llm(current_profile, conversation, f"user_{user_id}")
        
        # Update the user's profile
        user_memory.profile.set_profile(updated_profile)
        return updated_profile

    def _update_profile_with_llm(self, current_profile: str, conversation: str, profile_type: str) -> str:
        """
        Use LLM to intelligently update profile based on conversation.
        
        Args:
            current_profile: Current profile content
            conversation: Conversation to learn from
            profile_type: Type of profile ("agent" or "user_id")
            
        Returns:
            Updated profile content
        """
        if not self.enable_llm_search or not self.llm:
            # Fallback: simple append if LLM not available
            return self._simple_profile_update(current_profile, conversation)
        
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

Return only the updated profile text, nothing else.
"""
            
            response = self.llm.generate(update_prompt, max_tokens=500, temperature=0.3)
            
            if response and response.content:
                updated_profile = response.content.strip()
                
                # Validate the updated profile
                if len(updated_profile) > 50 and updated_profile != current_profile:
                    # Auto-update agent profile if this is agent profile update
                    if profile_type == "agent":
                        self.agent_memory.profile.set_profile(updated_profile)
                    
                    return updated_profile
                else:
                    # Return current profile if update seems invalid or unchanged
                    return current_profile
            
        except Exception as e:
            # Fallback on error
            pass
        
        # Fallback to simple update
        return self._simple_profile_update(current_profile, conversation)

    def _simple_profile_update(self, current_profile: str, conversation: str) -> str:
        """
        Simple fallback profile update when LLM is not available.
        
        Args:
            current_profile: Current profile content
            conversation: Conversation content
            
        Returns:
            Updated profile with basic information extraction
        """
        if not current_profile:
            # If no current profile, create a basic one
            return f"Profile updated based on conversation. Key topics discussed: {conversation[:200]}..."
        
        # Simple approach: check if conversation contains new meaningful information
        conversation_lower = conversation.lower()
        profile_lower = current_profile.lower()
        
        # Look for new information patterns
        new_info_patterns = [
            "i am", "i'm", "my name is", "i work", "i study", "i like", "i prefer",
            "my hobby", "my interest", "i specialize", "i focus on", "my background"
        ]
        
        new_info = []
        for pattern in new_info_patterns:
            if pattern in conversation_lower and pattern not in profile_lower:
                # Extract sentence containing the pattern
                sentences = conversation.split('.')
                for sentence in sentences:
                    if pattern in sentence.lower():
                        new_info.append(sentence.strip())
                        break
        
        if new_info:
            # Add new information to profile
            updated_profile = current_profile + "\n\nRecent updates:\n" + "\n".join(new_info[:3])
            return updated_profile
        else:
            # No significant new information found
            return current_profile

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
        
        # Fallback to basic search only if LLM unavailable
        return self.should_search_memory(conversation, system_prompt)

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
            # Fallback to basic rule-based search
            return self.should_search_memory(conversation, system_prompt)
        
        try:
            # Prepare LLM prompt for search decision
            decision_prompt = f"""
You are helping decide whether to search memory for relevant context. 

Conversation: "{conversation}"
System prompt: "{system_prompt}"
Context length: {context_length} characters

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
        
        # Fallback to rule-based approach
        return self.should_search_memory(conversation, system_prompt)

    def should_search_memory(self, conversation: str, system_prompt: str = "") -> bool:
        """
        Determine if memory search is needed based on conversation content.
        
        Args:
            conversation: Current conversation text
            system_prompt: System prompt being used
            
        Returns:
            True if memory search should be performed
        """
        # Search indicators
        search_indicators = [
            # Direct memory requests
            r'\b(remember|recall|what do you know|tell me about|history|previous|before|last time)\b',
            
            # Question words that might need context
            r'\b(who|what|when|where|why|how)\b.*\?',
            
            # Personal references
            r'\b(I|my|me|mine|myself)\b',
            
            # Temporal references
            r'\b(yesterday|today|last week|before|earlier|previously|last time)\b',
            
            # Context-dependent words
            r'\b(this|that|it|they|them|he|she|we|us)\b',
            
            # Commands that might benefit from context
            r'\b(continue|resume|update|change|modify|add to|build on)\b'
        ]
        
        # Combine conversation and system prompt
        full_text = (conversation + " " + system_prompt).lower()
        
        # Check for any indicators
        for pattern in search_indicators:
            if re.search(pattern, full_text, re.IGNORECASE):
                return True
        
        return False

    def search_memory_with_context(self, conversation: str, system_prompt: str = "", 
                                 user_id: Optional[str] = None, max_results: int = 10) -> Dict[str, Any]:
        """
        Search memory and return relevant context for the conversation.
        
        Args:
            conversation: Current conversation text
            system_prompt: System prompt being used
            user_id: Optional user ID to search user-specific memory
            max_results: Maximum number of results to return
            
        Returns:
            Dictionary containing relevant memory context
        """
        # Extract search terms
        search_terms = self._extract_search_terms(conversation, system_prompt)
        
        if not search_terms:
            return {
                "relevant_context": "",
                "search_terms": [],
                "results_found": 0,
                "agent_context": "",
                "user_context": ""
            }
        
        results = []
        
        # Search agent memory
        agent_context = self._search_agent_memory(search_terms)
        if agent_context:
            results.append({
                "source": "agent",
                "type": agent_context["type"],
                "content": agent_context["content"],
                "relevance": agent_context["relevance"]
            })
        
        # Search user memory if user_id provided
        user_context = ""
        if user_id and user_id in self._user_memories:
            user_memory_result = self._search_user_memory(user_id, search_terms)
            if user_memory_result:
                results.append({
                    "source": f"user_{user_id}",
                    "type": user_memory_result["type"],
                    "content": user_memory_result["content"],
                    "relevance": user_memory_result["relevance"]
                })
                user_context = user_memory_result["content"]
        
        # Sort by relevance and limit results
        results.sort(key=lambda x: x["relevance"], reverse=True)
        results = results[:max_results]
        
        # Create context string
        relevant_context = "\n".join([
            f"[{result['source']}] {result['content']}"
            for result in results
        ])
        
        return {
            "relevant_context": relevant_context,
            "search_terms": search_terms,
            "results_found": len(results),
            "agent_context": agent_context["content"] if agent_context else "",
            "user_context": user_context
        }

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
        return self.search_memory_with_context(conversation, system_prompt, user_id, max_results)

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
        if not self.enable_llm_search or not self.llm:
            # Fallback to regular deep search
            return self.deep_search(conversation, system_prompt, user_id, max_results, similarity_threshold)
        
        try:
            # Use LLM to analyze search intent and understand what user wants
            search_analysis = self._llm_analyze_search_intent(conversation, system_prompt)
            search_intent = search_analysis.get("intent", "")
            
            # Get all available memory content for LLM analysis
            all_memory_content = self._gather_all_memory_content(user_id)
            
            if not all_memory_content:
                return {
                    "relevant_context": "",
                    "search_terms": [],
                    "results_found": 0,
                    "agent_context": "",
                    "user_context": "",
                    "deep_search_metadata": {
                        "search_type": "llm_enhanced",
                        "llm_enhanced": True,
                        "similarity_threshold": similarity_threshold
                    }
                }
            
            # Use LLM to directly analyze and select relevant content
            llm_results = self._llm_analyze_memory_relevance(
                conversation, search_intent, all_memory_content, max_results, similarity_threshold
            )
            
            return llm_results
            
        except Exception as e:
            # Fallback to basic search on any error
            return self.search_memory_with_context(conversation, system_prompt, user_id, max_results)

    def _llm_analyze_search_intent(self, conversation: str, system_prompt: str) -> Dict[str, Any]:
        """Use LLM to analyze search intent and extract better search terms."""
        try:
            analysis_prompt = f"""
Analyze this conversation to understand what the user is looking for in memory search.

Conversation: "{conversation}"
System prompt: "{system_prompt}"

Please provide:
1. Search intent (what is the user trying to find/remember?)
2. Key search terms (important words and phrases to search for)
3. Context type (personal, technical, project-related, general, etc.)

Format your response as:
INTENT: [brief description of what user wants to find]
TERMS: [comma-separated list of 5-10 most important search terms]
CONTEXT: [type of context needed]
"""
            
            response = self.llm.generate(analysis_prompt, max_tokens=200, temperature=0.2)
            
            if response and response.content:
                content = response.content.strip()
                
                # Parse the response
                intent = ""
                terms = []
                context_type = ""
                
                for line in content.split('\n'):
                    line = line.strip()
                    if line.startswith("INTENT:"):
                        intent = line[7:].strip()
                    elif line.startswith("TERMS:"):
                        terms_str = line[6:].strip()
                        terms = [term.strip() for term in terms_str.split(',') if term.strip()]
                    elif line.startswith("CONTEXT:"):
                        context_type = line[8:].strip()
                
                return {
                    "intent": intent,
                    "search_terms": terms,
                    "context_type": context_type
                }
                
        except Exception:
            pass
        
        # Fallback to basic term extraction
        basic_terms = self._extract_enhanced_search_terms(conversation, system_prompt)
        return {
            "intent": "General information search",
            "search_terms": basic_terms,
            "context_type": "general"
        }

    def _llm_enhance_search_results(self, initial_results: Dict[str, Any], 
                                  conversation: str, search_intent: str, 
                                  max_results: int) -> Dict[str, Any]:
        """Use LLM to enhance and re-rank search results."""
        try:
            # Extract context from initial results
            context_parts = initial_results.get("relevant_context", "").split("\n\n")
            if len(context_parts) <= max_results:
                return initial_results
            
            # Prepare LLM prompt for result ranking
            ranking_prompt = f"""
User query: "{conversation}"
Search intent: {search_intent}

Here are potential memory search results. Please rank them by relevance to the user's query.
Rate each result from 1-10 (10 = highly relevant, 1 = not relevant).
Only include results with rating 6 or higher.

Results to rank:
{chr(10).join([f"{i+1}. {part[:200]}..." for i, part in enumerate(context_parts[:max_results*2])])}

Format: [Result number]: [Rating] - [Brief explanation]
Example: 1: 9 - Directly answers the user's question about machine learning
"""
            
            response = self.llm.generate(ranking_prompt, max_tokens=400, temperature=0.3)
            
            if response and response.content:
                # Parse LLM rankings
                ranked_indices = self._parse_llm_rankings(response.content)
                
                # Reorder results based on LLM ranking
                if ranked_indices:
                    reordered_context = []
                    for idx in ranked_indices[:max_results]:
                        if idx < len(context_parts):
                            reordered_context.append(context_parts[idx])
                    
                    # Update results with LLM-enhanced ranking
                    enhanced_results = initial_results.copy()
                    enhanced_results["relevant_context"] = "\n\n".join(reordered_context)
                    enhanced_results["results_found"] = len(reordered_context)
                    enhanced_results["deep_search_metadata"]["llm_enhanced"] = True
                    enhanced_results["deep_search_metadata"]["llm_ranking_applied"] = True
                    
                    return enhanced_results
                    
        except Exception:
            pass
        
        # Fallback: just limit results to max_results
        context_parts = initial_results.get("relevant_context", "").split("\n\n")
        limited_context = "\n\n".join(context_parts[:max_results])
        
        limited_results = initial_results.copy()
        limited_results["relevant_context"] = limited_context
        limited_results["results_found"] = min(initial_results["results_found"], max_results)
        
        return limited_results

    def _parse_llm_rankings(self, llm_response: str) -> List[int]:
        """Parse LLM ranking response to extract ordered result indices."""
        ranked_indices = []
        
        for line in llm_response.split('\n'):
            line = line.strip()
            if ':' in line:
                try:
                    # Extract result number and rating
                    parts = line.split(':')
                    result_num = int(parts[0].strip()) - 1  # Convert to 0-based index
                    
                    # Look for rating
                    rating_part = parts[1].strip()
                    rating = 0
                    
                    # Try to extract rating (should be first number after colon)
                    import re
                    rating_match = re.search(r'(\d+)', rating_part)
                    if rating_match:
                        rating = int(rating_match.group(1))
                    
                    # Only include results with rating 6 or higher
                    if rating >= 6 and result_num >= 0:
                        ranked_indices.append(result_num)
                        
                except (ValueError, IndexError):
                    continue
        
        return ranked_indices

    def _gather_all_memory_content(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Gather all memory content for LLM analysis."""
        all_content = []
        
        # Gather agent memory
        agent_profile = self.agent_memory.profile.get_profile()
        if agent_profile and agent_profile.strip():
            all_content.append({
                "type": "agent_profile",
                "source": "agent",
                "content": agent_profile,
                "id": "agent_profile"
            })
        
        for i, event in enumerate(self.agent_memory.events._memories):
            if event and event.strip():
                all_content.append({
                    "type": "agent_event",
                    "source": "agent",
                    "content": event,
                    "id": f"agent_event_{i}"
                })
        
        # Gather user memory if specified
        if user_id and user_id in self._user_memories:
            user_memory = self._user_memories[user_id]
            
            user_profile = user_memory.profile.get_profile()
            if user_profile and user_profile.strip():
                all_content.append({
                    "type": "user_profile",
                    "source": f"user_{user_id}",
                    "content": user_profile,
                    "id": f"user_{user_id}_profile"
                })
            
            for i, event in enumerate(user_memory.events._memories):
                if event and event.strip():
                    all_content.append({
                        "type": "user_event",
                        "source": f"user_{user_id}",
                        "content": event,
                        "id": f"user_{user_id}_event_{i}"
                    })
        
        return all_content

    def _llm_analyze_memory_relevance(self, conversation: str, search_intent: str, 
                                    all_content: List[Dict[str, Any]], max_results: int,
                                    similarity_threshold: float) -> Dict[str, Any]:
        """Use LLM to analyze memory content and determine relevance."""
        try:
            # Prepare content for LLM analysis
            content_items = []
            for i, item in enumerate(all_content):
                content_preview = item["content"][:200] + "..." if len(item["content"]) > 200 else item["content"]
                content_items.append(f"[{i+1}] ({item['type']}) {content_preview}")
            
            # Create LLM prompt for relevance analysis
            analysis_prompt = f"""
Analyze the following memory content to find items most relevant to the user's query.

User Query: "{conversation}"
Search Intent: {search_intent}

Memory Content:
{chr(10).join(content_items)}

Please analyze each memory item and:
1. Rate its relevance to the user's query (1-100, where 100 is extremely relevant)
2. Only include items with relevance >= {similarity_threshold}
3. Provide a brief explanation of why each item is relevant

Format your response as:
RELEVANT_ITEMS:
[Item number]: [Relevance score] - [Brief explanation]

Example:
RELEVANT_ITEMS:
1: 85 - Directly relates to the user's machine learning project
3: 72 - Contains background information about the discussed topic

If no items meet the threshold, respond with:
RELEVANT_ITEMS:
None - No memory content is sufficiently relevant to this query
"""
            
            response = self.llm.generate(analysis_prompt, max_tokens=500, temperature=0.2)
            
            if response and response.content:
                # Parse LLM response to get relevant items
                relevant_items = self._parse_llm_relevance_analysis(response.content, all_content)
                
                # Format results
                return self._format_llm_search_results(
                    relevant_items, conversation, search_intent, max_results, similarity_threshold
                )
                
        except Exception as e:
            # Return empty results on error
            pass
        
        return {
            "relevant_context": "",
            "search_terms": [],
            "results_found": 0,
            "agent_context": "",
            "user_context": "",
            "deep_search_metadata": {
                "search_type": "llm_enhanced",
                "llm_enhanced": True,
                "llm_error": True,
                "similarity_threshold": similarity_threshold
            }
        }

    def _parse_llm_relevance_analysis(self, llm_response: str, all_content: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parse LLM relevance analysis response."""
        relevant_items = []
        
        lines = llm_response.split('\n')
        parsing_items = False
        
        for line in lines:
            line = line.strip()
            
            if line.startswith("RELEVANT_ITEMS:"):
                parsing_items = True
                continue
            
            if parsing_items and ':' in line:
                try:
                    # Parse format: [Item number]: [Score] - [Explanation]
                    parts = line.split(':', 1)
                    item_num = int(parts[0].strip()) - 1  # Convert to 0-based index
                    
                    if 0 <= item_num < len(all_content):
                        rest = parts[1].strip()
                        
                        # Extract score
                        score_match = re.search(r'(\d+)', rest)
                        relevance_score = int(score_match.group(1)) if score_match else 0
                        
                        # Extract explanation
                        explanation = ""
                        if ' - ' in rest:
                            explanation = rest.split(' - ', 1)[1]
                        
                        # Add item with LLM analysis
                        item = all_content[item_num].copy()
                        item["relevance"] = relevance_score
                        item["llm_explanation"] = explanation
                        item["llm_analyzed"] = True
                        
                        relevant_items.append(item)
                        
                except (ValueError, IndexError):
                    continue
        
        # Sort by relevance score
        relevant_items.sort(key=lambda x: x["relevance"], reverse=True)
        
        return relevant_items

    def _format_llm_search_results(self, relevant_items: List[Dict[str, Any]], 
                                 conversation: str, search_intent: str, 
                                 max_results: int, similarity_threshold: float) -> Dict[str, Any]:
        """Format LLM search results into standard format."""
        
        # Limit to max results
        final_items = relevant_items[:max_results]
        
        # Create context string
        context_parts = []
        agent_context = ""
        user_context = ""
        
        for i, item in enumerate(final_items, 1):
            explanation = item.get("llm_explanation", "")
            relevance = item.get("relevance", 0)
            
            context_part = f"[{i}] ({item['source']}, LLM relevance: {relevance}) {item['content']}"
            if explanation:
                context_part += f"\n    → {explanation}"
            
            context_parts.append(context_part)
            
            # Extract specific contexts
            if item["source"] == "agent" and not agent_context:
                agent_context = item["content"]
            elif item["source"].startswith("user_") and not user_context:
                user_context = item["content"]
        
        relevant_context = "\n\n".join(context_parts)
        
        # Extract search terms from LLM intent analysis
        search_terms = []
        if search_intent:
            # Simple extraction of key terms from intent
            words = re.findall(r'\b[a-zA-Z]{3,}\b', search_intent.lower())
            search_terms = list(set(words))[:10]
        
        return {
            "relevant_context": relevant_context,
            "search_terms": search_terms,
            "results_found": len(final_items),
            "agent_context": agent_context,
            "user_context": user_context,
            "deep_search_metadata": {
                "search_type": "llm_enhanced",
                "llm_enhanced": True,
                "llm_analyzed": True,
                "similarity_threshold": similarity_threshold,
                "total_memory_items": len(relevant_items),
                "relevance_scores": [item["relevance"] for item in final_items],
                "search_intent": search_intent,
                "llm_explanations": [item.get("llm_explanation", "") for item in final_items]
            }
        }

    def _search_agent_memory(self, search_terms: List[str]) -> Optional[Dict[str, Any]]:
        """Search agent memory for relevant content."""
        # Search profile
        profile_result = self._search_text(self.agent_memory.profile.get_profile(), search_terms)
        if profile_result:
            profile_result["type"] = "agent_profile"
            profile_result["content"] = f"Agent Profile: {profile_result['content']}"
        
        # Search events
        events_result = self._search_events(self.agent_memory.events._memories, search_terms)
        if events_result:
            events_result["type"] = "agent_events"
            events_result["content"] = f"Agent Events: {events_result['content']}"
        
        # Return best result
        if profile_result and events_result:
            return profile_result if profile_result["relevance"] > events_result["relevance"] else events_result
        elif profile_result:
            return profile_result
        elif events_result:
            return events_result
        
        return None

    def _search_user_memory(self, user_id: str, search_terms: List[str]) -> Optional[Dict[str, Any]]:
        """Search user memory for relevant content."""
        user_memory = self._user_memories[user_id]
        
        # Search profile
        profile_result = self._search_text(user_memory.profile.get_profile(), search_terms)
        if profile_result:
            profile_result["type"] = "user_profile"
            profile_result["content"] = f"User {user_id} Profile: {profile_result['content']}"
        
        # Search events
        events_result = self._search_events(user_memory.events._memories, search_terms)
        if events_result:
            events_result["type"] = "user_events"
            events_result["content"] = f"User {user_id} Events: {events_result['content']}"
        
        # Return best result
        if profile_result and events_result:
            return profile_result if profile_result["relevance"] > events_result["relevance"] else events_result
        elif profile_result:
            return profile_result
        elif events_result:
            return events_result
        
        return None

    def _extract_search_terms(self, conversation: str, system_prompt: str) -> List[str]:
        """Extract relevant search terms from conversation and system prompt."""
        # Combine texts
        full_text = conversation + " " + system_prompt
        
        # Remove common words and extract meaningful terms
        stop_words = {
            'the', 'is', 'at', 'which', 'on', 'and', 'a', 'to', 'are', 'as', 'an', 'be', 'or', 'be',
            'have', 'it', 'of', 'not', 'you', 'that', 'but', 'for', 'can', 'had', 'has', 'was',
            'will', 'would', 'could', 'should', 'may', 'might', 'must', 'shall', 'do', 'does', 'did',
            'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'he', 'him', 'his', 'himself',
            'she', 'her', 'hers', 'herself', 'they', 'them', 'their', 'theirs', 'themselves'
        }
        
        # Extract words and filter
        words = re.findall(r'\b[a-zA-Z]{3,}\b', full_text.lower())
        search_terms = [word for word in words if word not in stop_words]
        
        # Remove duplicates while preserving order
        seen = set()
        unique_terms = []
        for term in search_terms:
            if term not in seen:
                seen.add(term)
                unique_terms.append(term)
        
        return unique_terms[:10]  # Limit to top 10 terms

    def _search_events(self, events: List[str], search_terms: List[str]) -> Optional[Dict[str, Any]]:
        """Search through events for relevant content."""
        best_match = None
        best_relevance = 0
        
        for event in events:
            result = self._search_text(event, search_terms)
            if result and result["relevance"] > best_relevance:
                best_match = result
                best_relevance = result["relevance"]
        
        return best_match

    def _search_text(self, text: str, search_terms: List[str]) -> Optional[Dict[str, Any]]:
        """
        Search for terms in text and return relevance score and matched content.
        
        Args:
            text: Text to search in
            search_terms: Terms to search for
            
        Returns:
            Dictionary with relevance score and content, or None if no matches
        """
        if not text or not search_terms:
            return None
        
        text_lower = text.lower()
        matches = 0
        matched_terms = []
        
        for term in search_terms:
            if term.lower() in text_lower:
                matches += 1
                matched_terms.append(term)
        
        if matches == 0:
            return None
        
        # Calculate relevance (percentage of terms matched + bonus for multiple matches)
        relevance = (matches / len(search_terms)) * 100
        if matches > 1:
            relevance += min(matches * 5, 25)  # Bonus for multiple matches, capped at 25
        
        return {
            "content": text[:500] + "..." if len(text) > 500 else text,
            "relevance": relevance,
            "matches": matches,
            "matched_terms": matched_terms
        }

    def _extract_enhanced_search_terms(self, conversation: str, system_prompt: str) -> List[str]:
        """
        Enhanced search term extraction for deep search with better semantic understanding.
        
        Args:
            conversation: Current conversation text
            system_prompt: System prompt being used
            
        Returns:
            List of enhanced search terms with better semantic relevance
        """
        # Combine texts
        full_text = conversation + " " + system_prompt
        
        # Enhanced stop words (more comprehensive)
        stop_words = {
            'the', 'is', 'at', 'which', 'on', 'and', 'a', 'to', 'are', 'as', 'an', 'be', 'or',
            'have', 'it', 'of', 'not', 'you', 'that', 'but', 'for', 'can', 'had', 'has', 'was',
            'will', 'would', 'could', 'should', 'may', 'might', 'must', 'shall', 'do', 'does', 'did',
            'am', 'this', 'these', 'those', 'then', 'than', 'how', 'now', 'here', 'there', 'where',
            'when', 'why', 'what', 'who', 'whom', 'whose', 'which', 'all', 'any', 'both', 'each',
            'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'only', 'own', 'same',
            'so', 'than', 'too', 'very', 'just', 'now'
        }
        
        # Extract different types of terms
        # 1. Regular words (3+ characters)
        words = re.findall(r'\b[a-zA-Z]{3,}\b', full_text.lower())
        
        # 2. Proper nouns (capitalized words)
        proper_nouns = re.findall(r'\b[A-Z][a-z]+\b', conversation + " " + system_prompt)
        
        # 3. Numbers and dates
        numbers = re.findall(r'\b\d+\b', full_text)
        
        # 4. Multi-word phrases (2-3 words)
        phrases = re.findall(r'\b[a-zA-Z]+\s+[a-zA-Z]+(?:\s+[a-zA-Z]+)?\b', full_text.lower())
        
        # Combine and filter terms
        all_terms = []
        
        # Add filtered words
        for word in words:
            if word not in stop_words and len(word) >= 3:
                all_terms.append(word)
        
        # Add proper nouns (likely important)
        for noun in proper_nouns:
            if noun.lower() not in stop_words:
                all_terms.append(noun.lower())
        
        # Add numbers
        all_terms.extend(numbers)
        
        # Add meaningful phrases (filter out common phrases)
        common_phrases = {'you know', 'i think', 'i mean', 'you see', 'i guess', 'you know what'}
        for phrase in phrases:
            if phrase not in common_phrases and all(word not in stop_words for word in phrase.split()):
                all_terms.append(phrase)
        
        # Remove duplicates while preserving order and prioritize by frequency
        term_counts = {}
        for term in all_terms:
            term_counts[term] = term_counts.get(term, 0) + 1
        
        # Sort by frequency and importance
        unique_terms = sorted(set(all_terms), 
                            key=lambda x: (term_counts[x], len(x)), 
                            reverse=True)
        
        return unique_terms[:15]  # Return top 15 terms for deep search

    def _deep_search_agent_memory(self, search_terms: List[str], 
                                similarity_threshold: float) -> List[Dict[str, Any]]:
        """Enhanced agent memory search with better relevance scoring."""
        results = []
        
        # Search profile with enhanced scoring
        profile_text = self.agent_memory.profile.get_profile()
        if profile_text:
            profile_result = self._enhanced_search_text(profile_text, search_terms, "agent_profile")
            if profile_result and profile_result["relevance"] >= similarity_threshold:
                profile_result["content"] = f"Agent Profile: {profile_result['content']}"
                results.append(profile_result)
        
        # Search all events with enhanced scoring
        for i, event in enumerate(self.agent_memory.events._memories):
            event_result = self._enhanced_search_text(event, search_terms, "agent_events")
            if event_result and event_result["relevance"] >= similarity_threshold:
                event_result["content"] = f"Agent Event {i+1}: {event_result['content']}"
                event_result["event_index"] = i
                results.append(event_result)
        
        return results

    def _deep_search_user_memory(self, user_id: str, search_terms: List[str], 
                               similarity_threshold: float) -> List[Dict[str, Any]]:
        """Enhanced user memory search with better relevance scoring."""
        user_memory = self._user_memories[user_id]
        results = []
        
        # Search profile
        profile_text = user_memory.profile.get_profile()
        if profile_text:
            profile_result = self._enhanced_search_text(profile_text, search_terms, "user_profile")
            if profile_result and profile_result["relevance"] >= similarity_threshold:
                profile_result["content"] = f"User {user_id} Profile: {profile_result['content']}"
                results.append(profile_result)
        
        # Search all events
        for i, event in enumerate(user_memory.events._memories):
            event_result = self._enhanced_search_text(event, search_terms, "user_events")
            if event_result and event_result["relevance"] >= similarity_threshold:
                event_result["content"] = f"User {user_id} Event {i+1}: {event_result['content']}"
                event_result["event_index"] = i
                results.append(event_result)
        
        return results

    def _enhanced_search_text(self, text: str, search_terms: List[str], 
                            search_type: str) -> Optional[Dict[str, Any]]:
        """
        Enhanced text search with better relevance scoring and semantic analysis.
        
        Args:
            text: Text to search in
            search_terms: Terms to search for
            search_type: Type of search (for weighting)
            
        Returns:
            Dictionary with enhanced relevance score and metadata
        """
        if not text or not search_terms:
            return None
        
        text_lower = text.lower()
        matches = 0
        matched_terms = []
        partial_matches = 0
        phrase_matches = 0
        
        # Exact matches
        for term in search_terms:
            term_lower = term.lower()
            if term_lower in text_lower:
                matches += 1
                matched_terms.append(term)
                # Count frequency of matches
                matches += text_lower.count(term_lower) - 1
        
        # Partial matches (fuzzy matching)
        for term in search_terms:
            if term not in matched_terms:
                term_lower = term.lower()
                # Check for partial matches (substring)
                for word in text_lower.split():
                    if len(term_lower) > 3 and (term_lower in word or word in term_lower):
                        partial_matches += 1
                        break
        
        # Phrase matches (multi-word terms)
        for term in search_terms:
            if ' ' in term and term.lower() in text_lower:
                phrase_matches += 1
        
        if matches == 0 and partial_matches == 0 and phrase_matches == 0:
            return None
        
        # Enhanced relevance calculation
        exact_match_score = (matches / len(search_terms)) * 100
        partial_match_score = (partial_matches / len(search_terms)) * 30
        phrase_match_score = phrase_matches * 20
        
        # Length penalty for very long texts (prefer concise relevant content)
        length_penalty = max(0, min(10, (len(text) - 200) / 100))
        
        # Type bonus (profiles might be more important than events)
        type_bonus = 10 if 'profile' in search_type else 0
        
        final_relevance = (exact_match_score + partial_match_score + 
                          phrase_match_score + type_bonus - length_penalty)
        
        return {
            "content": text[:800] + "..." if len(text) > 800 else text,
            "relevance": max(0, final_relevance),
            "type": search_type,
            "matches": matches,
            "partial_matches": partial_matches,
            "phrase_matches": phrase_matches,
            "matched_terms": matched_terms,
            "text_length": len(text)
        }

    def _analyze_cross_references(self, search_terms: List[str], 
                                user_id: str) -> List[Dict[str, Any]]:
        """
        Analyze cross-references between agent and user memories.
        
        Args:
            search_terms: Search terms to look for connections
            user_id: User ID to analyze
            
        Returns:
            List of cross-reference results
        """
        cross_refs = []
        
        if user_id not in self._user_memories:
            return cross_refs
        
        user_memory = self._user_memories[user_id]
        
        # Look for shared concepts between agent and user memories
        agent_content = (self.agent_memory.profile.get_profile() + " " + 
                        " ".join(self.agent_memory.events._memories))
        user_content = (user_memory.profile.get_profile() + " " + 
                       " ".join(user_memory.events._memories))
        
        # Find common important terms
        agent_words = set(re.findall(r'\b[a-zA-Z]{4,}\b', agent_content.lower()))
        user_words = set(re.findall(r'\b[a-zA-Z]{4,}\b', user_content.lower()))
        
        # Find intersections with search terms
        search_terms_set = set(term.lower() for term in search_terms)
        shared_terms = agent_words.intersection(user_words).intersection(search_terms_set)
        
        for term in shared_terms:
            cross_refs.append({
                "type": "cross_reference",
                "content": f"Shared concept '{term}' found in both agent and user {user_id} memories",
                "relevance": 80.0,  # High relevance for cross-references
                "shared_term": term,
                "reference_type": "shared_concept"
            })
        
        return cross_refs[:3]  # Limit to top 3 cross-references

    def _calculate_enhanced_relevance(self, result: Dict[str, Any], 
                                    search_terms: List[str], conversation: str, 
                                    system_prompt: str) -> float:
        """
        Calculate enhanced relevance score using multiple factors.
        
        Args:
            result: Search result to score
            search_terms: Original search terms
            conversation: Current conversation
            system_prompt: System prompt
            
        Returns:
            Enhanced relevance score
        """
        base_relevance = result["relevance"]
        
        # Conversation context bonus
        conv_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', conversation.lower()))
        result_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', result["content"].lower()))
        context_overlap = len(conv_words.intersection(result_words))
        context_bonus = min(context_overlap * 2, 20)
        
        # Recency bonus (newer content might be more relevant)
        # This is a placeholder - in a real implementation, you'd use timestamps
        recency_bonus = 5 if result.get("event_index", 0) >= 0 else 0
        
        # Source importance (profiles might be more important than individual events)
        source_bonus = 15 if "profile" in result["type"] else 0
        if result.get("source") == "cross_reference":
            source_bonus = 25  # Cross-references are very important
        
        # Match quality bonus
        match_quality = 0
        if result.get("phrase_matches", 0) > 0:
            match_quality += result["phrase_matches"] * 10
        if result.get("matches", 0) > result.get("partial_matches", 0):
            match_quality += 5
        
        enhanced_score = (base_relevance + context_bonus + recency_bonus + 
                         source_bonus + match_quality)
        
        return min(enhanced_score, 150.0)  # Cap at 150

    def _create_enhanced_context_string(self, results: List[Dict[str, Any]]) -> str:
        """
        Create an enhanced context string with better formatting and metadata.
        
        Args:
            results: Search results to format
            
        Returns:
            Formatted context string
        """
        if not results:
            return ""
        
        context_parts = []
        
        for i, result in enumerate(results, 1):
            relevance = result.get("enhanced_relevance", result["relevance"])
            source = result.get("source", "unknown")
            
            # Format with relevance score and source
            context_part = (f"[{i}] ({source}, relevance: {relevance:.1f}) "
                          f"{result['content']}")
            context_parts.append(context_part)
        
        return "\n\n".join(context_parts)

    def __str__(self) -> str:
        llm_status = f"llm={self.enable_llm_search and self.llm is not None}"
        search_mode = "LLM-search" if (self.enable_llm_search and self.llm is not None) else "keyword-fallback"
        return f"Memory(agent_id={self.agent_id}, users={len(self._user_memories)}, search_mode={search_mode}, {llm_status})" 