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
                    "memory_type": {
                        "type": "string",
                        "description": "Specific memory type to read (optional, returns all if not specified)"
                    },
                    "include_embeddings": {
                        "type": "boolean",
                        "description": "Whether to include embedding information",
                        "default": False
                    }
                },
                "required": ["character_name"]
            }
        }
    
    def execute(
        self,
        character_name: str,
        memory_type: Optional[str] = None,
        include_embeddings: bool = False
    ) -> Dict[str, Any]:
        """
        Execute read memory operation
        
        Args:
            character_name: Name of the character
            memory_type: Specific memory type to read (None for all)
            include_embeddings: Whether to include embedding information
            
        Returns:
            Dict containing read result with content
        """
        try:
            if memory_type and memory_type not in self.memory_types:
                return self._add_metadata({
                    "success": False,
                    "error": f"Invalid memory type '{memory_type}'. Available: {list(self.memory_types.keys())}"
                })
            
            if memory_type:
                # Read specific memory type
                content = self._read_memory_content(character_name, memory_type)
                
                if include_embeddings and self.embeddings_enabled:
                    # Include embedding metadata
                    embedding_info = self._get_embedding_info(character_name, memory_type)
                    return self._add_metadata({
                        "success": True,
                        "character_name": character_name,
                        "memory_type": memory_type,
                        "content": {
                            "content": content,
                            "embedding_info": embedding_info
                        },
                        "message": f"Successfully read {memory_type} for {character_name}"
                    })
                else:
                    return self._add_metadata({
                        "success": True,
                        "character_name": character_name,
                        "memory_type": memory_type,
                        "content": content,
                        "message": f"Successfully read {memory_type} for {character_name}"
                    })
            else:
                # Read all memory types
                all_memory = self._load_existing_memory(character_name)
                return self._add_metadata({
                    "success": True,
                    "character_name": character_name,
                    "memory_type": None,
                    "content": all_memory,
                    "message": f"Successfully read all memory types for {character_name}"
                })
                
        except Exception as e:
            return self._handle_error(e)
    
    def _get_embedding_info(self, character_name: str, memory_type: str) -> Dict[str, Any]:
        """Get embedding information for a memory type"""
        try:
            import json
            
            char_embeddings_dir = self.embeddings_dir / character_name
            embeddings_file = char_embeddings_dir / f"{memory_type}_embeddings.json"
            
            if embeddings_file.exists():
                with open(embeddings_file, 'r', encoding='utf-8') as f:
                    embeddings_data = json.load(f)
                
                return {
                    "has_embeddings": True,
                    "embedding_count": embeddings_data.get("total_embeddings", 0),
                    "last_updated": embeddings_data.get("timestamp", ""),
                    "content_hash": embeddings_data.get("content_hash", "")
                }
            else:
                return {
                    "has_embeddings": False,
                    "embedding_count": 0,
                    "last_updated": "",
                    "content_hash": ""
                }
                
        except Exception as e:
            logger.warning(f"Failed to get embedding info for {character_name}:{memory_type}: {e}")
            return {"has_embeddings": False, "embedding_count": 0, "error": str(e)} 