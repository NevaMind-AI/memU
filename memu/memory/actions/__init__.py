"""
Memory Actions Module

Individual action implementations for memory operations.
Each action is a standalone module that can be loaded dynamically.
"""

from .base_action import BaseAction

# Import all actions
from .add_activity_memory import AddActivityMemoryAction
# from .get_available_categories import GetAvailableCategoriesAction
from .link_related_memories import LinkRelatedMemoriesAction
from .generate_suggestions import GenerateMemorySuggestionsAction
from .update_memory_with_suggestions import UpdateMemoryWithSuggestionsAction
from .run_theory_of_mind import RunTheoryOfMindAction
from .cluster_memories import ClusterMemoriesAction

# Registry of all available actions
ACTION_REGISTRY = {
    "add_activity_memory": AddActivityMemoryAction,
    # "get_available_categories": GetAvailableCategoriesAction,
    "link_related_memories": LinkRelatedMemoriesAction,
    "generate_memory_suggestions": GenerateMemorySuggestionsAction,
    "update_memory_with_suggestions": UpdateMemoryWithSuggestionsAction,
    "run_theory_of_mind": RunTheoryOfMindAction,
    "cluster_memories": ClusterMemoriesAction
}

__all__ = [
    "BaseAction",
    "ACTION_REGISTRY",
    "AddActivityMemoryAction", 
    # "GetAvailableCategoriesAction",
    "LinkRelatedMemoriesAction",
    "GenerateMemorySuggestionsAction",
    "UpdateMemoryWithSuggestionsAction",
    "RunTheoryOfMindAction",
    "ClusterMemoriesAction"
] 