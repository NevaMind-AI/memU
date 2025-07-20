"""
Delete Memory Action

Deletes memory content and associated embeddings for a character.
"""

from typing import Dict, Any, Optional, List

from .base_action import BaseAction
from ...utils import get_logger

logger = get_logger(__name__)


class DeleteMemoryAction(BaseAction):
    """Action to delete memory content and associated embeddings"""
    
    @property
    def action_name(self) -> str:
        return "delete_memory"
    
    def get_schema(self) -> Dict[str, Any]:
        """Return OpenAI-compatible function schema"""
        return {
            "name": "delete_memory",
            "description": "Delete memory content and associated embeddings for a character",
            "parameters": {
                "type": "object",
                "properties": {
                    "character_name": {
                        "type": "string",
                        "description": "Name of the character"
                    },
                    "category": {
                        "type": "string",
                        "description": "Specific category to delete (optional, deletes all if not specified)"
                    },
                    "delete_embeddings": {
                        "type": "boolean",
                        "description": "Whether to delete associated embeddings",
                        "default": True
                    }
                },
                "required": ["character_name"]
            }
        }
    
    def execute(
        self,
        character_name: str,
        category: Optional[str] = None,
        delete_embeddings: bool = True
    ) -> Dict[str, Any]:
        """
        Execute delete memory operation
        
        Args:
            character_name: Name of the character
            category: Specific category to delete (None to delete all)
            delete_embeddings: Whether to delete associated embeddings
            
        Returns:
            Dict containing deletion result including embedding cleanup info
        """
        try:
            deleted_categories = []
            failed_categories = []
            embeddings_deleted = 0
            
            categories_to_delete = [category] if category else list(self.memory_types.keys())
            
            for cat in categories_to_delete:
                if cat and cat not in self.memory_types:
                    failed_categories.append(f"Invalid category: {cat}")
                    continue
                
                try:
                    # Delete memory content (set to empty string)
                    success = self._save_memory_content(character_name, cat, "")
                    
                    # Delete associated embeddings
                    if delete_embeddings and self.embeddings_enabled:
                        deleted_count = self._delete_embeddings(character_name, cat)
                        embeddings_deleted += deleted_count
                    
                    if success:
                        deleted_categories.append(cat)
                    else:
                        failed_categories.append(cat)
                except Exception as e:
                    failed_categories.append(f"{cat}: {str(e)}")
            
            return self._add_metadata({
                "success": len(failed_categories) == 0,
                "character_name": character_name,
                "deleted_categories": deleted_categories,
                "failed_categories": failed_categories,
                "total_deleted": len(deleted_categories),
                "embeddings_deleted": embeddings_deleted,
                "message": f"Deleted {len(deleted_categories)} categories and {embeddings_deleted} embeddings for {character_name}"
            })
            
        except Exception as e:
            return self._handle_error(e)
    
    def _delete_embeddings(self, character_name: str, category: str) -> int:
        """Delete embeddings for a category"""
        try:
            char_embeddings_dir = self.embeddings_dir / character_name
            embeddings_file = char_embeddings_dir / f"{category}_embeddings.json"
            
            deleted_count = 0
            if embeddings_file.exists():
                # Get count before deletion
                deleted_count = self._count_embeddings(character_name, category)
                embeddings_file.unlink()
                logger.debug(f"Deleted {deleted_count} embeddings for {character_name}:{category}")
            
            return deleted_count
            
        except Exception as e:
            logger.warning(f"Failed to delete embeddings for {character_name}:{category}: {e}")
            return 0
    
    def _count_embeddings(self, character_name: str, category: str) -> int:
        """Count embeddings for a specific category"""
        try:
            import json
            
            char_embeddings_dir = self.embeddings_dir / character_name
            embeddings_file = char_embeddings_dir / f"{category}_embeddings.json"
            
            if embeddings_file.exists():
                with open(embeddings_file, 'r', encoding='utf-8') as f:
                    embeddings_data = json.load(f)
                return embeddings_data.get("total_embeddings", 0)
            
            return 0
        except Exception:
            return 0 