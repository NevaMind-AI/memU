"""
Link Related Memories Action

Automatically finds and links related memories using embedding search.
"""

import json
import math
from typing import Dict, Any, List, Optional
from datetime import datetime
from .base_action import BaseAction
from ...utils import get_logger

logger = get_logger(__name__)


class LinkRelatedMemoriesAction(BaseAction):
    """
    Action to find and link related memories using embedding search
    
    This action takes a memory item and finds the most related existing memories,
    then creates links between them that can be written into documentation.
    """
    
    def __init__(self, memory_core):
        super().__init__(memory_core)
        self.description = "Find and link related memories using embedding search"

    @property
    def action_name(self) -> str:
        """Return the name of this action"""
        return "link_related_memories"

    def get_schema(self) -> Dict[str, Any]:
        """Get OpenAI function schema for linking related memories"""
        return {
            "name": "link_related_memories",
            "description": "Find related memories using embedding search and create links between them",
            "parameters": {
                "type": "object",
                "properties": {
                    "character_name": {
                        "type": "string",
                        "description": "Name of the character"
                    },
                    "memory_id": {
                        "type": "string",
                        "description": "ID of the memory item to find related memories for (optional if link_all_items is true)"
                    },
                    "category": {
                        "type": "string",
                        "description": "Category containing the target memory item"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of top related memories to find",
                        "default": 5
                    },
                    "min_similarity": {
                        "type": "number",
                        "description": "Minimum similarity threshold (0.0-1.0)",
                        "default": 0.3
                    },
                    "search_categories": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Categories to search in (default: all available categories)"
                    },

                    "link_all_items": {
                        "type": "boolean",
                        "description": "Whether to link all memory items in the category (if true, memory_id can be omitted)",
                        "default": False
                    },
                    "write_to_memory": {
                        "type": "boolean",
                        "description": "Whether to append links to the original memory content",
                        "default": False
                    }
                },
                "required": ["character_name", "category"]
            }
        }

    def execute(
        self,
        character_name: str,
        category: str,
        memory_id: Optional[str] = None,
        top_k: int = 5,
        min_similarity: float = 0.3,
        search_categories: Optional[List[str]] = None,
        link_all_items: bool = False,
        write_to_memory: bool = False
    ) -> Dict[str, Any]:
        """
        Execute link related memories operation
        
        Args:
            character_name: Name of the character
            memory_id: ID of the memory item to find related memories for
            category: Category containing the target memory item
            top_k: Number of top related memories to find
            min_similarity: Minimum similarity threshold
            search_categories: Categories to search in
            link_format: Format for generating links
            write_to_memory: Whether to append links to original memory
            
        Returns:
            Dict containing related memories and generated links
        """
        try:
            # Validate inputs
            if not self.embeddings_enabled:
                return self._add_metadata({
                    "success": False,
                    "error": "Embeddings are not enabled. Cannot perform similarity search."
                })
            
            if category not in self.memory_types:
                return self._add_metadata({
                    "success": False,
                    "error": f"Invalid category '{category}'. Available: {list(self.memory_types.keys())}"
                })
            
            # If link_all_items is True, process all memory items in the category
            if link_all_items:
                return self._link_all_items_in_category(
                    character_name, category, top_k, min_similarity, search_categories, write_to_memory
                )
            
            # Otherwise, process single memory item
            if not memory_id:
                return self._add_metadata({
                    "success": False,
                    "error": "memory_id is required when link_all_items is False"
                })
            
            # Find the target memory item
            target_memory = self._find_memory_item(character_name, category, memory_id)
            if not target_memory:
                return self._add_metadata({
                    "success": False,
                    "error": f"Memory ID '{memory_id}' not found in {category} for {character_name}"
                })
            
            # Generate embedding for target content
            target_embedding = self.embedding_client.embed(target_memory["content"])
            
            # Determine search categories - search in ALL categories by default
            if search_categories is None:
                search_categories = list(self.memory_types.keys())
            
            # Find related memories
            related_memories = self._find_related_memories(
                character_name, target_embedding, search_categories, top_k, min_similarity, memory_id
            )
            
            # Get memory IDs for links  
            memory_ids = [memory["memory_id"] for memory in related_memories]
            
            # Optionally write links to memory
            updated_content = None
            if write_to_memory and memory_ids:
                updated_content = self._append_links_to_memory(
                    character_name, category, memory_id, memory_ids
                )
            
            return self._add_metadata({
                "success": True,
                "character_name": character_name,
                "target_memory": {
                    "memory_id": memory_id,
                    "category": category,
                    "content": target_memory["content"]
                },
                "related_memories": related_memories,
                "memory_ids": memory_ids,
                "total_related": len(related_memories),
                "written_to_memory": write_to_memory,
                "updated_content": updated_content,
                "message": f"Found {len(related_memories)} related memories for {memory_id}"
            })
            
        except Exception as e:
            return self._handle_error(e)

    def _find_memory_item(self, character_name: str, category: str, memory_id: str) -> Optional[Dict[str, Any]]:
        """Find a specific memory item by ID"""
        try:
            content = self._read_memory_content(character_name, category)
            if not content:
                return None
            
            memory_items = self._parse_memory_items(content)
            for item in memory_items:
                if item["memory_id"] == memory_id:
                    return item
            return None
            
        except Exception as e:
            logger.error(f"Error finding memory item {memory_id}: {e}")
            return None

    def _find_related_memories(
        self,
        character_name: str,
        target_embedding: List[float],
        search_categories: List[str],
        top_k: int,
        min_similarity: float,
        exclude_memory_id: str
    ) -> List[Dict[str, Any]]:
        """Find related memories using embedding similarity across all categories"""
        all_candidates = []
        
        try:
            char_embeddings_dir = self.embeddings_dir / character_name
            if not char_embeddings_dir.exists():
                return []
            
            # Collect ALL embeddings from all categories first
            for category in search_categories:
                embeddings_file = char_embeddings_dir / f"{category}_embeddings.json"
                
                if embeddings_file.exists():
                    try:
                        with open(embeddings_file, 'r', encoding='utf-8') as f:
                            embeddings_data = json.load(f)
                        
                        for emb_data in embeddings_data.get("embeddings", []):
                            # Skip the target memory itself
                            if emb_data.get("memory_id") == exclude_memory_id:
                                continue
                                
                            similarity = self._cosine_similarity(target_embedding, emb_data["embedding"])
                            
                            # Add ALL candidates regardless of similarity threshold initially
                            all_candidates.append({
                                "memory_id": emb_data.get("memory_id", ""),
                                "content": emb_data["text"],
                                "full_line": emb_data.get("full_line", emb_data["text"]),
                                "category": category,
                                "similarity": similarity,
                                "item_id": emb_data.get("item_id", ""),
                                "line_number": emb_data.get("line_number", 0)
                            })
                    
                    except Exception as e:
                        logger.warning(f"Failed to load embeddings for {category}: {e}")
            
            # Sort ALL candidates by similarity globally
            all_candidates.sort(key=lambda x: x["similarity"], reverse=True)
            
            # Apply similarity threshold and take top K
            filtered_results = [
                candidate for candidate in all_candidates[:top_k * 2]  # Take more candidates first
                if candidate["similarity"] >= min_similarity
            ]
            
            # Return final top K after filtering
            return filtered_results[:top_k]
            
        except Exception as e:
            logger.error(f"Error finding related memories: {e}")
            return []

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            if len(vec1) != len(vec2):
                return 0.0
            
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            magnitude1 = math.sqrt(sum(a * a for a in vec1))
            magnitude2 = math.sqrt(sum(a * a for a in vec2))
            
            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0
            
            return dot_product / (magnitude1 * magnitude2)
            
        except Exception:
            return 0.0



    def _append_links_to_memory(
        self,
        character_name: str,
        category: str,
        memory_id: str,
        memory_ids: List[str]
    ) -> Optional[str]:
        """Append links to the original memory content"""
        try:
            # Read current content
            content = self._read_memory_content(character_name, category)
            if not content:
                return None
            
            memory_items = self._parse_memory_items(content)
            updated_lines = []
            
            for item in memory_items:
                if item["memory_id"] == memory_id:
                    # Format: [memory_id] content (related_id1,related_id2)
                    original_line = item["full_line"]
                    if memory_ids:
                        # Remove existing links if any (content between parentheses at the end)
                        import re
                        clean_line = re.sub(r'\s*\([^)]*\)\s*$', '', original_line)
                        updated_line = f"{clean_line} ({','.join(memory_ids)})"
                    else:
                        updated_line = original_line
                    
                    updated_lines.append(updated_line)
                else:
                    updated_lines.append(item["full_line"])
            
            # Save updated content
            updated_content = "\n".join(updated_lines)
            success = self._save_memory_content(character_name, category, updated_content)
            
            if success:
                return updated_content
            else:
                logger.error("Failed to save updated memory content")
                return None
                
        except Exception as e:
            logger.error(f"Error appending links to memory: {e}")
            return None

    def _link_all_items_in_category(
        self,
        character_name: str,
        category: str,
        top_k: int,
        min_similarity: float,
        search_categories: Optional[List[str]],
        write_to_memory: bool
    ) -> Dict[str, Any]:
        """Link all memory items in a category to related memories"""
        try:
            # Get all memory items in the category
            content = self._read_memory_content(character_name, category)
            if not content:
                return self._add_metadata({
                    "success": False,
                    "error": f"No content found in {category} for {character_name}"
                })
            
            memory_items = self._parse_memory_items(content)
            if not memory_items:
                return self._add_metadata({
                    "success": False,
                    "error": f"No memory items found in {category}"
                })
            
            # Determine search categories - search in ALL categories by default
            if search_categories is None:
                search_categories = list(self.memory_types.keys())
            
            total_linked = 0
            all_related_memories = []
            updated_content = None
            
            # Process each memory item
            for item in memory_items:
                memory_id = item["memory_id"]
                
                # Generate embedding for this item's content
                target_embedding = self.embedding_client.embed(item["content"])
                
                # Find related memories
                related_memories = self._find_related_memories(
                    character_name, target_embedding, search_categories, top_k, min_similarity, memory_id
                )
                
                if related_memories:
                    all_related_memories.extend(related_memories)
                    total_linked += 1
            
            # If write_to_memory is enabled, update all memory items with their links
            if write_to_memory and total_linked > 0:
                updated_content = self._append_links_to_all_items(
                    character_name, category, memory_items, search_categories, top_k, min_similarity
                )
            
            return self._add_metadata({
                "success": True,
                "character_name": character_name,
                "category": category,
                "total_items_processed": len(memory_items),
                "total_items_linked": total_linked,
                "all_related_memories": all_related_memories,
                "written_to_memory": write_to_memory,
                "updated_content": updated_content,
                "message": f"Linked {total_linked} out of {len(memory_items)} memory items in {category}"
            })
            
        except Exception as e:
            return self._handle_error(e)
    
    def _append_links_to_all_items(
        self,
        character_name: str,
        category: str,
        memory_items: List[Dict[str, Any]],
        search_categories: List[str],
        top_k: int,
        min_similarity: float
    ) -> Optional[str]:
        """Append links to all memory items in the category"""
        try:
            updated_lines = []
            
            for item in memory_items:
                memory_id = item["memory_id"]
                original_line = item["full_line"]
                
                # Generate embedding for this item
                target_embedding = self.embedding_client.embed(item["content"])
                
                # Find related memories for this specific item
                related_memories = self._find_related_memories(
                    character_name, target_embedding, search_categories, top_k, min_similarity, memory_id
                )
                
                if related_memories:
                    # Get memory IDs for links
                    memory_ids = [memory["memory_id"] for memory in related_memories]
                    
                    # Remove existing links if any
                    import re
                    clean_line = re.sub(r'\s*\([^)]*\)\s*$', '', original_line)
                    updated_line = f"{clean_line} ({','.join(memory_ids)})"
                    updated_lines.append(updated_line)
                else:
                    # No related memories found, keep original line
                    updated_lines.append(original_line)
            
            # Save updated content
            updated_content = "\n".join(updated_lines)
            success = self._save_memory_content(character_name, category, updated_content)
            
            if success:
                return updated_content
            else:
                logger.error("Failed to save updated memory content")
                return None
                
        except Exception as e:
            logger.error(f"Error appending links to all items: {e}")
            return None 