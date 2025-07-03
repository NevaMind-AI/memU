#!/usr/bin/env python3
"""
PersonaLab Utilities Module

Contains reusable common functions and tools for PersonaLab project, providing:
1. Conversation processing and analysis tools
2. Memory management tools
3. AI response simulation and learning functions

Author: PersonaLab Team
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from personalab.memo import ConversationManager
from personalab.memory import Memory, MemoryClient

from .config.database import get_database_manager


def validate_conversation_data(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Validate conversation data integrity and format

    Args:
        messages: List of conversation messages

    Returns:
        Dict[str, Any]: Validation result containing is_valid and errors
    """
    result = {"is_valid": True, "errors": [], "warnings": []}

    if not messages:
        result["is_valid"] = False
        result["errors"].append("Conversation message list is empty")
        return result

    for i, msg in enumerate(messages):
        # Check required fields
        if not isinstance(msg, dict):
            result["is_valid"] = False
            result["errors"].append(f"Message {i}: Not in dictionary format")
            continue

        if "role" not in msg:
            result["is_valid"] = False
            result["errors"].append(f"Message {i}: Missing role field")

        if "content" not in msg:
            result["is_valid"] = False
            result["errors"].append(f"Message {i}: Missing content field")

        # Check role value
        if msg.get("role") not in ["user", "assistant", "system"]:
            result["warnings"].append(
                f"Message {i}: Non-standard role value: {msg.get('role')}"
            )

        # Check content length
        content = msg.get("content", "")
        if len(content) > 10000:
            result["warnings"].append(
                f"Message {i}: Content too long ({len(content)} characters)"
            )
        elif len(content.strip()) == 0:
            result["warnings"].append(f"Message {i}: Content is empty")

    return result


# ===== Memory Management Utility Functions =====


def create_memory_manager():
    """Create Memory manager (PostgreSQL-only)"""

    db_manager = get_database_manager()
    return MemoryClient(db_manager=db_manager)


def create_conversation_manager(enable_embeddings: bool = True):
    """Create conversation manager (PostgreSQL-only)

    Args:
        enable_embeddings: Whether to enable vector embeddings
    """

    db_manager = get_database_manager()
    return ConversationManager(
        db_manager=db_manager, enable_embeddings=enable_embeddings
    )


def setup_agent_memory(memory_manager, agent_id: str, initial_profile: str = ""):
    """Set up agent's initial memory"""
    memory = memory_manager.get_memory_by_agent(agent_id)
    if initial_profile:
        memory.update_profile(initial_profile)
        memory_manager.database.save_memory(memory)
    return memory


def get_memory_context(memory_manager, agent_id: str) -> str:
    """Get memory context for AI prompts"""
    memory = memory_manager.get_memory_by_agent(agent_id)
    context_parts = []

    # Add user profile
    profile = memory.get_profile_content()
    if profile:
        context_parts.append(f"user background: {profile}")

    # Add important events
    events = memory.get_event_content()
    if events:
        recent_events = events[-3:]  # Latest 3 events
        context_parts.append("important events: " + ";".join(recent_events))

    # Add user insights
    insights = memory.get_mind_content()
    if insights:
        recent_insights = insights[-2:]  # Latest 2 insights
        context_parts.append("user characteristics: " + ";".join(recent_insights))

    return "\n\n".join(context_parts)


def get_conversation_context(
    conversation_manager, agent_id: str, query: str, limit: int = 2
) -> str:
    """Get relevant historical conversation context"""
    try:
        # Search for relevant conversations
        results = conversation_manager.search_similar_conversations(
            agent_id=agent_id, query=query, limit=limit, similarity_threshold=0.6
        )

        if not results:
            return ""

        # Build context
        context = "## Related historical conversation\n"
        for i, result in enumerate(results, 1):
            context += f"{i}. {result['summary']}\n"

        context += "\nPlease refer to the above historical conversation to answer the current question."
        return context

    except Exception as e:
        print(f"⚠️ Failed to retrieve history: {e}")
        return ""


def build_system_prompt(
    memory_manager, conversation_manager, agent_id: str, user_message: str
) -> str:
    """Build system prompt with memory"""
    base_prompt = "You are a smart assistant, able to remember user preferences and historical conversations."

    # Add memory context
    memory_context = get_memory_context(memory_manager, agent_id)
    if memory_context:
        base_prompt += f"\n\n{memory_context}"

    # Add conversation history context
    conversation_context = get_conversation_context(
        conversation_manager, agent_id, user_message
    )
    if conversation_context:
        base_prompt += f"\n\n{conversation_context}"

    return base_prompt


def get_memory_summary(memory_manager, agent_id: str) -> Dict[str, Any]:
    """Get memory summary"""
    memory = memory_manager.get_memory_by_agent(agent_id)

    return {
        "agent_id": agent_id,
        "profile": memory.get_profile_content(),
        "events": memory.get_event_content(),
        "insights": memory.get_mind_content(),
    }


def cleanup_memory_resources(memory_manager, conversation_manager):
    """Clean up resources"""
    try:
        if hasattr(memory_manager, "close"):
            memory_manager.close()
        if hasattr(conversation_manager, "close"):
            conversation_manager.close()
    except Exception:
        pass


def chat_with_memory(
    llm_client, memory: Memory, message: str, agent_id: str, user_id: str
) -> str:
    """Integrated memory chat function

    Args:
        llm_client: LLM client instance
        memory: Memory object
        message: User message
        agent_id: Agent ID (required)
        user_id: User ID (required)

    Returns:
        AI response
    """
    # Get memory context
    # Get memory context (temporarily not using stats)

    # Build system prompt
    memory_context = []
    if memory.get_profile():
        memory_context.append(f"user profile: {', '.join(memory.get_profile())}")
    if memory.get_events():
        memory_context.append(f"important events: {', '.join(memory.get_events())}")
    if memory.get_mind():
        memory_context.append(f"psychological insights: {', '.join(memory.get_mind())}")

    system_prompt = """You are smart assistant {agent_id}, talking with user {user_id}.

Memory context:
{chr(10).join(memory_context) if memory_context else 'No memory information'}

Please reply to the user based on the above memory information in a natural and helpful way."""

    # Send request
    response = llm_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message},
        ],
    )

    return response.choices[0].message.content
