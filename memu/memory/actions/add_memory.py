"""
Add Memory Action

Adds new memory content to a specific category with automatic embedding generation.
"""

import json
import hashlib
from typing import Dict, Any
from datetime import datetime

from .base_action import BaseAction
from ...utils import get_logger

logger = get_logger(__name__)


class AddMemoryAction(BaseAction):
    """
    Action to add new memory content to a category
    
    Supports both append and replace modes, with optional embedding generation
    for semantic search functionality.
    """
    
    @property
    def action_name(self) -> str:
        return "add_memory"
    
    def get_schema(self) -> Dict[str, Any]:
        """Return OpenAI-compatible function schema"""
        return {
            "name": "add_memory",
            "description": "Add new memory content to a specific category with automatic embedding generation",
            "parameters": {
                "type": "object",
                "properties": {
                    "character_name": {
                        "type": "string",
                        "description": "Name of the character"
                    },
                    "category": {
                        "type": "string",
                        "description": "Memory category (activity, profile, event, etc.)"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to add to the memory"
                    },
                    "append": {
                        "type": "boolean",
                        "description": "Whether to append to existing content (true) or replace it (false)",
                        "default": True
                    },
                    "generate_embeddings": {
                        "type": "boolean",
                        "description": "Whether to generate embeddings for semantic search",
                        "default": True
                    }
                },
                "required": ["character_name", "category", "content"]
            }
        }
    
    def execute(
        self,
        character_name: str,
        category: str,
        content: str,
        append: bool = True,
        generate_embeddings: bool = True
    ) -> Dict[str, Any]:
        """
        Execute add memory operation
        
        Args:
            character_name: Name of the character
            category: Memory category to add to
            content: Content to add
            append: Whether to append to existing content or replace it
            generate_embeddings: Whether to generate embeddings for the content
            
        Returns:
            Dict containing operation result including embedding info
        """
        try:
            # Validate category
            if category not in self.memory_types:
                return self._add_metadata({
                    "success": False,
                    "error": f"Invalid category '{category}'. Available: {list(self.memory_types.keys())}"
                })
            
            # Load existing content if appending
            existing_content = ""
            if append:
                existing_content = self._read_memory_content(character_name, category)
            
            # Add memory IDs to new content
            content_with_ids = self._add_memory_ids_to_content(content)
            
            # Prepare new content
            if append and existing_content:
                new_content = existing_content + "\n\n" + content_with_ids
            else:
                new_content = content_with_ids
            
            # Save content with embeddings if enabled
            embeddings_info = ""
            if generate_embeddings and self.embeddings_enabled:
                if append and existing_content:
                    # For append mode, save first, then add embedding for just the new content
                    success = self._save_memory_content(character_name, category, new_content)
                    if success:
                        # Add embedding for just the new content
                        embedding_result = self._add_memory_item_embedding(character_name, category, content_with_ids)
                        embeddings_info = f"Generated embedding for new item: {embedding_result.get('message', 'Unknown')}"
                    else:
                        embeddings_info = "Failed to save memory"
                else:
                    # For replace mode, regenerate all embeddings
                    success = self._save_memory_with_embeddings(character_name, category, new_content)
                    embeddings_info = "Generated embeddings for all content"
            else:
                success = self._save_memory_content(character_name, category, new_content)
                embeddings_info = "No embeddings generated"
            
            if success:
                return self._add_metadata({
                    "success": True,
                    "character_name": character_name,
                    "category": category,
                    "operation": "append" if append else "replace",
                    "content_added": len(content),
                    "embeddings_generated": generate_embeddings and self.embeddings_enabled,
                    "embeddings_info": embeddings_info,
                    "message": f"Successfully {'appended to' if append else 'replaced'} {category} for {character_name}"
                })
            else:
                return self._add_metadata({
                    "success": False,
                    "error": f"Failed to save memory to {category}"
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
                    embedding_vector = self.embedding_client.generate_embedding(item["content"])
                    
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
    
    def _add_memory_item_embedding(self, character_name: str, category: str, new_content: str) -> Dict[str, Any]:
        """Add embedding for new memory items"""
        try:
            if not self.embeddings_enabled or not new_content.strip():
                return {
                    "success": False,
                    "error": "Embeddings disabled or empty item"
                }
            
            # Load existing embeddings
            char_embeddings_dir = self.embeddings_dir / character_name
            char_embeddings_dir.mkdir(exist_ok=True)
            embeddings_file = char_embeddings_dir / f"{category}_embeddings.json"
            
            existing_embeddings = []
            if embeddings_file.exists():
                with open(embeddings_file, 'r', encoding='utf-8') as f:
                    embeddings_data = json.load(f)
                    existing_embeddings = embeddings_data.get("embeddings", [])
            
            # Parse new memory items
            new_items = self._parse_memory_items(new_content)
            
            # Generate embeddings for new items
            for item in new_items:
                if not item["content"].strip():
                    continue
                    
                try:
                    embedding_vector = self.embedding_client.generate_embedding(item["content"])
                    new_item_id = f"{character_name}_{category}_item_{len(existing_embeddings)}"
                    
                    new_embedding = {
                        "item_id": new_item_id,
                        "memory_id": item["memory_id"],
                        "text": item["content"],
                        "full_line": item["full_line"],
                        "embedding": embedding_vector,
                        "line_number": len(existing_embeddings) + 1,
                        "metadata": {
                            "character": character_name,
                            "category": category,
                            "length": len(item["content"]),
                            "timestamp": datetime.now().isoformat()
                        }
                    }
                    
                    # Add to existing embeddings
                    existing_embeddings.append(new_embedding)
                    
                except Exception as e:
                    logger.warning(f"Failed to generate embedding for memory item {item.get('memory_id')}: {e}")
                    continue
            
            # Save updated embeddings
            embeddings_data = {
                "category": category,
                "timestamp": datetime.now().isoformat(),
                "content_hash": hashlib.md5(new_content.encode()).hexdigest(),
                "embeddings": existing_embeddings,
                "total_embeddings": len(existing_embeddings)
            }
            
            with open(embeddings_file, 'w', encoding='utf-8') as f:
                json.dump(embeddings_data, f, indent=2, ensure_ascii=False)
            
            return {
                "success": True,
                "embedding_count": len(existing_embeddings),
                "new_items_count": len(new_items),
                "message": f"Added embeddings for {len(new_items)} new memory items in {category}"
            }
                
        except Exception as e:
            logger.error(f"Failed to add memory item embedding: {e}")
            return {
                "success": False,
                "error": str(e)
            } 