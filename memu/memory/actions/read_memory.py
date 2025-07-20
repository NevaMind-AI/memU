"""
Read Memory Action

Reads memory content for a character from specific category or all categories.
"""

from typing import Dict, Any, Optional

from .base_action import BaseAction
from ...utils import get_logger

logger = get_logger(__name__)


class ReadMemoryAction(BaseAction):
    """Action to read memory content for a character"""
    
    @property
    def action_name(self) -> str:
        return "read_memory"
    
    def get_schema(self) -> Dict[str, Any]:
        """Return OpenAI-compatible function schema"""
        return {
            "name": "read_memory",
            "description": "Read memory content for a character from specific category or all categories",
            "parameters": {
                "type": "object",
                "properties": {
                    "character_name": {
                        "type": "string",
                        "description": "Name of the character"
                    },
                    "category": {
                        "type": "string",
                        "description": "Specific category to read (optional, returns all if not specified)"
                    }
                },
                "required": ["character_name"]
            }
        }
    
    def execute(
        self,
        character_name: str,
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute read memory operation
        
        Args:
            character_name: Name of the character
            category: Specific category to read (None for all)
            
        Returns:
            Dict containing read result with content
        """
        try:
            if category and category not in self.memory_types:
                return self._add_metadata({
                    "success": False,
                    "error": f"Invalid category '{category}'. Available: {list(self.memory_types.keys())}"
                })
            
            if category:
                # Read specific category
                content = self._read_memory_content(character_name, category)
                
                return self._add_metadata({
                    "success": True,
                    "character_name": character_name,
                    "category": category,
                    "content": content,
                    "message": f"Successfully read {category} for {character_name}"
                })
            else:
                # Read all memory types
                all_memory = self._load_existing_memory(character_name)
                
                return self._add_metadata({
                    "success": True,
                    "character_name": character_name,
                    "category": None,
                    "content": all_memory,
                    "message": f"Successfully read all memory types for {character_name}"
                })
                
        except Exception as e:
            return self._handle_error(e) 