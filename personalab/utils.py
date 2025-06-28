"""
PersonaLab Utilities

Convenient utility functions for integrating PersonaLab memory with LLM services.
"""

from typing import List, Dict, Optional, Union
from .memory import Memory, MemoryClient


def enhance_system_prompt_with_memory(
    base_system_prompt: str,
    memory: Union[Memory, str], 
    memory_client: Optional[MemoryClient] = None,
    include_profile: bool = True,
    include_events: bool = True,
    include_insights: bool = True,
    max_events: int = 10,
    max_insights: int = 5,
    memory_section_title: str = "## Memory Context"
) -> str:
    """
    Enhance a system prompt with PersonaLab memory content.
    
    This is the main utility function to integrate memory into OpenAI system prompts.
    
    Args:
        base_system_prompt: The base system prompt to enhance
        memory: Either a Memory object or an agent_id string
        memory_client: MemoryClient instance (required if memory is an agent_id)
        include_profile: Whether to include profile memory
        include_events: Whether to include event memory
        include_insights: Whether to include ToM insights
        max_events: Maximum number of recent events to include
        max_insights: Maximum number of recent insights to include
        memory_section_title: Title for the memory section
        
    Returns:
        Enhanced system prompt with memory context
        
    Example:
        >>> from personalab.utils import enhance_system_prompt_with_memory
        >>> from personalab.memory import MemoryClient
        >>> 
        >>> client = MemoryClient("agent_memory.db")
        >>> enhanced_prompt = enhance_system_prompt_with_memory(
        ...     "You are a helpful AI assistant.",
        ...     agent_id="my_agent",
        ...     memory_client=client
        ... )
    """
    # Get Memory object if agent_id is provided
    if isinstance(memory, str):
        if memory_client is None:
            raise ValueError("memory_client is required when memory is an agent_id string")
        memory_obj = memory_client.get_or_create_memory(memory)
    else:
        memory_obj = memory
    
    # Build memory sections
    memory_sections = []
    
    # Add profile information
    if include_profile:
        profile = memory_obj.get_profile_content()
        if profile:
            memory_sections.append(f"**User Profile:**\n{profile}")
    
    # Add recent events
    if include_events:
        events = memory_obj.get_event_content()
        if events:
            recent_events = events[-max_events:] if len(events) > max_events else events
            events_text = "\n".join(f"- {event}" for event in recent_events)
            memory_sections.append(f"**Recent Events:**\n{events_text}")
    
    # Add psychological insights
    if include_insights:
        insights = memory_obj.get_tom_content()
        if insights:
            recent_insights = insights[-max_insights:] if len(insights) > max_insights else insights
            insights_text = "\n".join(f"- {insight}" for insight in recent_insights)
            memory_sections.append(f"**Behavioral Insights:**\n{insights_text}")
    
    # Combine with base prompt
    if memory_sections:
        memory_context = "\n\n".join(memory_sections)
        enhanced_prompt = f"""{base_system_prompt}

{memory_section_title}
{memory_context}

Use this context naturally in your responses without explicitly mentioning the memory system."""
    else:
        enhanced_prompt = base_system_prompt
    
    return enhanced_prompt



__all__ = [
    'enhance_system_prompt_with_memory'
]
