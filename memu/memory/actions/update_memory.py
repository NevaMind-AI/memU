"""
Update Memory Action

Updates existing memory content with new content and regenerates embeddings.
"""

import json
import hashlib
from typing import Dict, Any
from datetime import datetime

from .base_action import BaseAction
from ...utils import get_logger

logger = get_logger(__name__)


class UpdateMemoryAction(BaseAction):
    """Action to update existing memory content"""
    
    @property
    def action_name(self) -> str:
        return "update_memory"
    
    def get_schema(self) -> Dict[str, Any]:
        """Return OpenAI-compatible function schema"""
        return {
            "name": "update_memory",
            "description": "Update existing memory content with new content and regenerate embeddings",
            "parameters": {
                "type": "object",
                "properties": {
                    "character_name": {
                        "type": "string",
                        "description": "Name of the character"
                    },
                    "category": {
                        "type": "string",
                        "description": "Memory category to update"
                    },
                    "new_content": {
                        "type": "string",
                        "description": "New content to replace existing content"
                    },
                    "regenerate_embeddings": {
                        "type": "boolean",
                        "description": "Whether to regenerate embeddings for the new content",
                        "default": True
                    }
                },
                "required": ["character_name", "category", "new_content"]
            }
        }
    
    def execute(
        self,
        character_name: str,
        category: str,
        new_content: str,
        regenerate_embeddings: bool = True
    ) -> Dict[str, Any]:
        """
        Execute update memory operation
        
        Args:
            character_name: Name of the character
            category: Memory category to update
            new_content: New content to replace existing content
            regenerate_embeddings: Whether to regenerate embeddings
            
        Returns:
            Dict containing update result including embedding info
        """
        try:
            # Validate category
            if category not in self.memory_types:
                return self._add_metadata({
                    "success": False,
                    "error": f"Invalid category '{category}'. Available: {list(self.memory_types.keys())}"
                })
            
            # Get old content for comparison
            old_content = self._read_memory_content(character_name, category)
            old_length = len(old_content) if isinstance(old_content, str) else 0
            
            # Update with new content and embeddings
            embeddings_info = ""
            if regenerate_embeddings and self.embeddings_enabled:
                success = self._save_memory_with_embeddings(character_name, category, new_content)
                embeddings_info = "Regenerated embeddings for updated content"
            else:
                success = self._save_memory_content(character_name, category, new_content)
                embeddings_info = "No embedding regeneration"
            
            if success:
                return self._add_metadata({
                    "success": True,
                    "character_name": character_name,
                    "category": category,
                    "old_content_length": old_length,
                    "new_content_length": len(new_content),
                    "content_change": len(new_content) - old_length,
                    "embeddings_regenerated": regenerate_embeddings and self.embeddings_enabled,
                    "embeddings_info": embeddings_info,
                    "message": f"Successfully updated {category} for {character_name}"
                })
            else:
                return self._add_metadata({
                    "success": False,
                    "error": f"Failed to update {category}"
                })
                
        except Exception as e:
            return self._handle_error(e)
    
    def _save_memory_with_embeddings(self, character_name: str, memory_type: str, content: str) -> bool:
        """Save memory content and generate embeddings"""
        try:
            # Save the main content
            success = self._save_memory_content(character_name, memory_type, content)
            
            if success and self.embeddings_enabled and content.strip():
                # Generate embeddings for the content
                self._generate_memory_embeddings(character_name, memory_type, content)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to save memory with embeddings for {character_name}: {e}")
            return False
    
    def _generate_memory_embeddings(self, character_name: str, memory_type: str, content: str):
        """Generate and store embeddings for memory content - one embedding per line"""
        try:
            if not content.strip() or not self.embedding_client:
                return
            
            # Split content into lines (each line is a memory item)
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            
            embeddings = []
            for i, line in enumerate(lines):
                if not line.strip():
                    continue
                
                try:
                    # Generate embedding for this line
                    embedding_vector = self.embedding_client.generate_embedding(line)
                    
                    embedding_item = {
                        "item_id": f"{character_name}_{memory_type}_item_{i}",
                        "text": line,
                        "embedding": embedding_vector,
                        "line_number": i + 1,
                        "metadata": {
                            "character": character_name,
                            "memory_type": memory_type,
                            "length": len(line),
                            "timestamp": datetime.now().isoformat()
                        }
                    }
                    
                    embeddings.append(embedding_item)
                    
                except Exception as e:
                    logger.warning(f"Failed to generate embedding for line {i}: {e}")
                    continue
            
            if embeddings:
                # Store embeddings
                char_embeddings_dir = self.embeddings_dir / character_name
                char_embeddings_dir.mkdir(exist_ok=True)
                
                embeddings_file = char_embeddings_dir / f"{memory_type}_embeddings.json"
                embeddings_data = {
                    "memory_type": memory_type,
                    "timestamp": datetime.now().isoformat(),
                    "content_hash": hashlib.md5(content.encode()).hexdigest(),
                    "embeddings": embeddings,
                    "total_embeddings": len(embeddings)
                }
                
                with open(embeddings_file, 'w', encoding='utf-8') as f:
                    json.dump(embeddings_data, f, indent=2, ensure_ascii=False)
                
                logger.debug(f"Generated {len(embeddings)} embeddings for {memory_type} of {character_name}")
            
        except Exception as e:
            logger.error(f"Failed to generate memory embeddings for {character_name}:{memory_type}: {e}") 