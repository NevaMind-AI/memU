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
                        "description": "Memory category containing the item to update"
                    },
                    "memory_id": {
                        "type": "string",
                        "description": "ID of the specific memory item to update"
                    },
                    "new_content": {
                        "type": "string",
                        "description": "New content to replace the existing memory item"
                    },
                    "regenerate_embeddings": {
                        "type": "boolean",
                        "description": "Whether to regenerate embeddings for the updated content",
                        "default": True
                    }
                },
                "required": ["character_name", "category", "memory_id", "new_content"]
            }
        }
    
    def execute(
        self,
        character_name: str,
        category: str,
        memory_id: str,
        new_content: str,
        regenerate_embeddings: bool = True
    ) -> Dict[str, Any]:
        """
        Execute update memory operation
        
        Args:
            character_name: Name of the character
            category: Memory category containing the item to update
            memory_id: ID of the specific memory item to update
            new_content: New content to replace the existing memory item
            regenerate_embeddings: Whether to regenerate embeddings
            
        Returns:
            Dict containing update result
        """
        try:
            # Validate category
            if category not in self.memory_types:
                return self._add_metadata({
                    "success": False,
                    "error": f"Invalid category '{category}'. Available: {list(self.memory_types.keys())}"
                })
            
            # Read existing content
            existing_content = self._read_memory_content(character_name, category)
            
            if not existing_content.strip():
                return self._add_metadata({
                    "success": False,
                    "error": f"No existing content found in {category} for {character_name}"
                })
            
            # Parse existing memory items
            memory_items = self._parse_memory_items(existing_content)
            
            # Find the item with the specified memory_id
            target_item = None
            remaining_items = []
            
            for item in memory_items:
                if item["memory_id"] == memory_id:
                    target_item = item
                else:
                    remaining_items.append(item)
            
            if not target_item:
                return self._add_metadata({
                    "success": False,
                    "error": f"Memory ID '{memory_id}' not found in {category} for {character_name}",
                    "available_ids": [item["memory_id"] for item in memory_items]
                })
            
            # Generate new memory ID for the updated content
            new_memory_id = self._generate_memory_id()
            new_line_with_id = f"[{new_memory_id}] {new_content.strip()}"
            
            # Rebuild content: remaining items + new item at the end
            updated_lines = []
            for item in remaining_items:
                updated_lines.append(item["full_line"])
            
            # Add new content at the end
            updated_lines.append(new_line_with_id)
            
            updated_content = "\n".join(updated_lines)
            
            # Save the updated content
            if regenerate_embeddings:
                success = self._save_memory_with_embeddings(character_name, category, updated_content)
            else:
                success = self._save_memory_content(character_name, category, updated_content)
            
            if success:
                return self._add_metadata({
                    "success": True,
                    "character_name": character_name,
                    "category": category,
                    "old_memory_id": memory_id,
                    "new_memory_id": new_memory_id,
                    "old_content": target_item["content"],
                    "new_content": new_content.strip(),
                    "total_items": len(updated_lines),
                    "embeddings_regenerated": regenerate_embeddings,
                    "message": f"Successfully updated memory item {memory_id} in {category} for {character_name}"
                })
            else:
                return self._add_metadata({
                    "success": False,
                    "error": "Failed to save updated memory content"
                })
                
        except Exception as e:
            return self._handle_error(e)
    
    def _save_memory_with_embeddings(self, character_name: str, category: str, content: str) -> bool:
        """Save memory content and generate embeddings"""
        try:
            # Save the main content (content already has memory IDs)
            success = self._save_memory_content(character_name, category, content)
            
            if success and self.embeddings_enabled and content.strip():
                # Generate embeddings for the content
                self._generate_memory_embeddings(character_name, category, content)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to save memory with embeddings for {character_name}: {e}")
            return False
    
    def _generate_memory_embeddings(self, character_name: str, category: str, content: str):
        """Generate and store embeddings for memory content - one embedding per line"""
        try:
            if not content.strip() or not self.embedding_client:
                return
            
            # Parse memory items with IDs
            memory_items = self._parse_memory_items(content)
            
            embeddings = []
            for i, item in enumerate(memory_items):
                if not item["content"].strip():
                    continue
                
                try:
                    # Generate embedding for the clean content (without memory ID)
                    embedding_vector = self.embedding_client.embed(item["content"])
                    
                    embedding_item = {
                        "item_id": f"{character_name}_{category}_item_{i}",
                        "memory_id": item["memory_id"],  # Store the original memory ID
                        "text": item["content"],  # Store clean content
                        "full_line": item["full_line"],  # Store full line with memory ID
                        "embedding": embedding_vector,
                        "line_number": item["line_number"],
                        "metadata": {
                            "character": character_name,
                            "category": category,
                            "length": len(item["content"]),
                            "timestamp": datetime.now().isoformat()
                        }
                    }
                    
                    embeddings.append(embedding_item)
                    
                except Exception as e:
                    logger.warning(f"Failed to generate embedding for memory item {item.get('memory_id', i)}: {e}")
                    continue
            
            if embeddings:
                # Store embeddings
                char_embeddings_dir = self.embeddings_dir / character_name
                char_embeddings_dir.mkdir(exist_ok=True)
                
                embeddings_file = char_embeddings_dir / f"{category}_embeddings.json"
                embeddings_data = {
                    "category": category,
                    "timestamp": datetime.now().isoformat(),
                    "content_hash": hashlib.md5(content.encode()).hexdigest(),
                    "embeddings": embeddings,
                    "total_embeddings": len(embeddings)
                }
                
                with open(embeddings_file, 'w', encoding='utf-8') as f:
                    json.dump(embeddings_data, f, indent=2, ensure_ascii=False)
                
                logger.debug(f"Generated {len(embeddings)} embeddings for {category} of {character_name}")
            
        except Exception as e:
            logger.error(f"Failed to generate memory embeddings for {character_name}:{category}: {e}") 