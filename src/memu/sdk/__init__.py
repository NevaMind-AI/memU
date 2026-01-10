"""
MemU Python SDK - Cloud API Client

This module provides a Python SDK for interacting with the MemU Cloud API,
enabling developers to programmatically manage structured, long-term memory
for AI agents.

Example:
    from memu.sdk import MemUClient

    # Initialize the client
    client = MemUClient(api_key="your_api_key")

    # Memorize a conversation
    result = await client.memorize(
        resource_url="path/to/conversation.json",
        modality="conversation",
        user_id="user_123"
    )

    # Retrieve memories
    memories = await client.retrieve(
        query="What are the user's preferences?",
        user_id="user_123"
    )
"""

from memu.sdk.client import MemUClient
from memu.sdk.models import (
    MemorizeResult,
    MemoryCategory,
    MemoryItem,
    MemoryResource,
    RetrieveResult,
    TaskStatus,
)

__all__ = [
    "MemUClient",
    "MemorizeResult",
    "MemoryCategory",
    "MemoryItem",
    "MemoryResource",
    "RetrieveResult",
    "TaskStatus",
]
