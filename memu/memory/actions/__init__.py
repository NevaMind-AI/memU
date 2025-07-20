"""
Memory Actions Module

Individual action implementations for memory operations.
Each action is a standalone module that can be loaded dynamically.
"""

from .base_action import BaseAction

# Import all actions
from .process_conversation import ProcessConversationAction
from .add_memory import AddMemoryAction
from .read_memory import ReadMemoryAction
from .search_memory import SearchMemoryAction
from .update_memory import UpdateMemoryAction
from .delete_memory import DeleteMemoryAction
from .get_memory_status import GetMemoryStatusAction
from .get_available_categories import GetAvailableCategoriesAction

# Registry of all available actions
ACTION_REGISTRY = {
    "process_conversation": ProcessConversationAction,
    "add_memory": AddMemoryAction,
    "read_memory": ReadMemoryAction,
    "search_memory": SearchMemoryAction,
    "update_memory": UpdateMemoryAction,
    "delete_memory": DeleteMemoryAction,
    "get_memory_status": GetMemoryStatusAction,
    "get_available_categories": GetAvailableCategoriesAction
}

__all__ = [
    "BaseAction",
    "ACTION_REGISTRY",
    "ProcessConversationAction",
    "AddMemoryAction", 
    "ReadMemoryAction",
    "SearchMemoryAction",
    "UpdateMemoryAction",
    "DeleteMemoryAction",
    "GetMemoryStatusAction",
    "GetAvailableCategoriesAction"
] 