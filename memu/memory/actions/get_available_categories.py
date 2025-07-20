"""
Get Available Categories Action

Gets all available memory categories and their descriptions.
"""

from typing import Dict, Any

from .base_action import BaseAction
from ...utils import get_logger

logger = get_logger(__name__)


class GetAvailableCategoriesAction(BaseAction):
    """Action to get all available memory categories from config"""
    
    @property
    def action_name(self) -> str:
        return "get_available_categories"
    
    def get_schema(self) -> Dict[str, Any]:
        """Return OpenAI-compatible function schema"""
        return {
            "name": "get_available_categories",
            "description": "Get all available memory categories and their descriptions",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    
    def execute(self) -> Dict[str, Any]:
        """
        Execute get available categories operation
        
        Returns:
            Dict containing category information
        """
        try:
            categories = {}
            
            for category, filename in self.memory_types.items():
                description = self.config_manager.get_file_description(category)
                
                categories[category] = {
                    "filename": filename,
                    "description": description,
                    "config_source": self.config_manager.get_folder_path(category)
                }
            
            return self._add_metadata({
                "success": True,
                "categories": categories,
                "total_categories": len(categories),
                "processing_order": self.processing_order,
                "embeddings_enabled": self.embeddings_enabled,
                "message": f"Found {len(categories)} memory categories from config"
            })
            
        except Exception as e:
            return self._handle_error(e) 