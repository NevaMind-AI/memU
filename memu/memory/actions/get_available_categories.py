"""
Get Available Categories Action

Gets all available memory categories and their descriptions, excluding activity category.
"""

from typing import Any, Dict

from ...utils import get_logger
from .base_action import BaseAction

logger = get_logger(__name__)


class GetAvailableCategoriesAction(BaseAction):
    """Action to get all available memory categories from config, excluding activity"""

    @property
    def action_name(self) -> str:
        return "get_available_categories"

    def get_schema(self) -> Dict[str, Any]:
        """Return OpenAI-compatible function schema"""
        return {
            "name": "get_available_categories",
            "description": "Get all available memory categories and their descriptions (excluding activity category)",
            "parameters": {"type": "object", "properties": {}, "required": []},
        }

    def execute(self) -> Dict[str, Any]:
        """
        Execute get available categories operation

        Returns:
            Dict containing category information (excluding activity category)
        """
        try:
            categories = {}

            for category, filename in self.basic_memory_types.items():
                # Skip activity category as it's handled separately by add_activity_memory
                if category == "activity":
                    continue

                description = self.config_manager.get_file_description(category)

                categories[category] = {
                    "filename": filename,
                    "description": description,
                    "config_source": self.config_manager.get_folder_path(category),
                }

            return self._add_metadata(
                {
                    "success": True,
                    "categories": categories,
                    "total_categories": len(categories),
                    "processing_order": [
                        cat for cat in self.processing_order if cat != "activity"
                    ],
                    "embeddings_enabled": self.embeddings_enabled,
                    "excluded_categories": ["activity"],
                    "message": f"Found {len(categories)} memory categories from config (excluding activity)",
                }
            )

        except Exception as e:
            return self._handle_error(e)
