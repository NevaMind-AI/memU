"""
Memory Actions Module

Individual action implementations for memory operations.
Each action is a standalone module that can be loaded dynamically.
"""

# Import all actions
from .add_activity_memory import AddActivityMemoryAction
from .base_action import BaseAction
from .cluster_memories import ClusterMemoriesAction
from .generate_suggestions import GenerateMemorySuggestionsAction

# from .get_available_categories import GetAvailableCategoriesAction
from .link_related_memories import LinkRelatedMemoriesAction
from .run_theory_of_mind import RunTheoryOfMindAction
from .update_memory_with_suggestions import UpdateMemoryWithSuggestionsAction

# Registry of all available actions
ACTION_REGISTRY = {
    "add_activity_memory": AddActivityMemoryAction,
    # "get_available_categories": GetAvailableCategoriesAction,
    "link_related_memories": LinkRelatedMemoriesAction,
    "generate_memory_suggestions": GenerateMemorySuggestionsAction,
    "update_memory_with_suggestions": UpdateMemoryWithSuggestionsAction,
    "run_theory_of_mind": RunTheoryOfMindAction,
    "cluster_memories": ClusterMemoriesAction,
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
    "ClusterMemoriesAction",
]
