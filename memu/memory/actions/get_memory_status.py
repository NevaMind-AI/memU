"""
Get Memory Status Action

Gets comprehensive status information about memory for a character.
"""

import json
from typing import Dict, Any
from datetime import datetime

from .base_action import BaseAction
from ...utils import get_logger

logger = get_logger(__name__)


class GetMemoryStatusAction(BaseAction):
    """Action to get comprehensive memory status for a character"""
    
    @property
    def action_name(self) -> str:
        return "get_memory_status"
    
    def get_schema(self) -> Dict[str, Any]:
        """Return OpenAI-compatible function schema"""
        return {
            "name": "get_memory_status",
            "description": "Get comprehensive status information about memory for a character",
            "parameters": {
                "type": "object",
                "properties": {
                    "character_name": {
                        "type": "string",
                        "description": "Name of the character"
                    },
                    "include_embedding_stats": {
                        "type": "boolean",
                        "description": "Whether to include embedding statistics",
                        "default": True
                    }
                },
                "required": ["character_name"]
            }
        }
    
    def execute(
        self,
        character_name: str,
        include_embedding_stats: bool = True
    ) -> Dict[str, Any]:
        """
        Execute get memory status operation
        
        Args:
            character_name: Name of the character
            include_embedding_stats: Whether to include embedding statistics
            
        Returns:
            Dict containing memory status information with embedding details
        """
        try:
            status = {
                "character_name": character_name,
                "available_categories": list(self.memory_types.keys()),
                "category_status": {},
                "total_content_length": 0,
                "embedding_stats": {},
                "last_updated": datetime.now().isoformat()
            }
            
            total_embeddings = 0
            for category in self.memory_types.keys():
                content = self._read_memory_content(character_name, category)
                content_str = content if isinstance(content, str) else ""
                
                category_embeddings = 0
                if include_embedding_stats and self.embeddings_enabled:
                    category_embeddings = self._count_embeddings(character_name, category)
                    total_embeddings += category_embeddings
                
                status["category_status"][category] = {
                    "exists": bool(content_str),
                    "content_length": len(content_str),
                    "filename": self.memory_types[category],
                    "description": self.config_manager.get_file_description(category),
                    "embeddings_count": category_embeddings
                }
                
                if content_str:
                    status["total_content_length"] += len(content_str)
            
            if include_embedding_stats:
                status["embedding_stats"] = {
                    "embeddings_enabled": self.embeddings_enabled,
                    "total_embeddings": total_embeddings,
                    "embedding_client": str(type(self.embedding_client)) if self.embedding_client else None,
                    "embeddings_directory": str(self.embeddings_dir)
                }
            
            return self._add_metadata({
                "success": True,
                "status": status,
                "message": f"Memory status for {character_name} - {status['total_content_length']} chars, {total_embeddings} embeddings"
            })
            
        except Exception as e:
            return self._handle_error(e)
    
    def _count_embeddings(self, character_name: str, memory_type: str) -> int:
        """Count embeddings for a specific memory type"""
        try:
            char_embeddings_dir = self.embeddings_dir / character_name
            embeddings_file = char_embeddings_dir / f"{memory_type}_embeddings.json"
            
            if embeddings_file.exists():
                with open(embeddings_file, 'r', encoding='utf-8') as f:
                    embeddings_data = json.load(f)
                return embeddings_data.get("total_embeddings", 0)
            
            return 0
        except Exception:
            return 0 