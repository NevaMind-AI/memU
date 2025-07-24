"""
Memory Actions Module

Individual action implementations for memory operations.
Each action is a standalone module that can be loaded dynamically.
"""

from .base_action import BaseAction

# Import all actions
from .add_activity_memory import AddActivityMemoryAction
from .read_memory import ReadMemoryAction
from .delete_memory import DeleteMemoryAction
from .get_available_categories import GetAvailableCategoriesAction
from .link_related_memories import LinkRelatedMemoriesAction
from .generate_suggestions import GenerateMemorySuggestionsAction
from .update_memory_with_suggestions import UpdateMemoryWithSuggestionsAction
from .summarize_conversation import SummarizeConversationAction
from .run_theory_of_mind import RunTheoryOfMindAction
# Registry of all available actions
ACTION_REGISTRY = {
    "add_activity_memory": AddActivityMemoryAction,
    "read_memory": ReadMemoryAction,
    "delete_memory": DeleteMemoryAction,
    "get_available_categories": GetAvailableCategoriesAction,
    "link_related_memories": LinkRelatedMemoriesAction,
    "generate_memory_suggestions": GenerateMemorySuggestionsAction,
    "update_memory_with_suggestions": UpdateMemoryWithSuggestionsAction,
    "summarize_conversation": SummarizeConversationAction,
    "run_theory_of_mind": RunTheoryOfMindAction
}

__all__ = [
    "BaseAction",
    "ACTION_REGISTRY",
    "AddActivityMemoryAction", 
    "ReadMemoryAction",
    "DeleteMemoryAction",
    "GetAvailableCategoriesAction",
    "LinkRelatedMemoriesAction",
    "GenerateMemorySuggestionsAction",
    "UpdateMemoryWithSuggestionsAction",
    "SummarizeConversationAction",
    "RunTheoryOfMindAction"
] 