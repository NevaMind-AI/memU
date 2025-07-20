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
                        "description": "ID of the memory item to find related memories for"
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
                    "link_format": {
                        "type": "string",
                        "enum": ["markdown", "plain", "json"],
                        "description": "Format for generating links",
                        "default": "markdown"
                    },
                    "write_to_memory": {
                        "type": "boolean",
                        "description": "Whether to append links to the original memory content",
                        "default": False
                    }
                },
                "required": ["character_name", "memory_id", "category"]
            }
        }

    def execute(
        self,
        character_name: str,
        memory_id: str,
        category: str,
        top_k: int = 5,
        min_similarity: float = 0.3,
        search_categories: Optional[List[str]] = None,
        link_format: str = "markdown",
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
            
            # Find the target memory item
            target_memory = self._find_memory_item(character_name, category, memory_id)
            if not target_memory:
                return self._add_metadata({
                    "success": False,
                    "error": f"Memory ID '{memory_id}' not found in {category} for {character_name}"
                })
            
            # Generate embedding for target content
            target_embedding = self.embedding_client.generate_embedding(target_memory["content"])
            
            # Determine search categories - search in ALL categories by default
            if search_categories is None:
                search_categories = list(self.memory_types.keys())
            
            # Find related memories
            related_memories = self._find_related_memories(
                character_name, target_embedding, search_categories, top_k, min_similarity, memory_id
            )
            
            # Generate links
            links = self._generate_links(related_memories, link_format)
            
            # Optionally write links to memory
            updated_content = None
            if write_to_memory and links:
                updated_content = self._append_links_to_memory(
                    character_name, category, memory_id, links, link_format
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
                "links": links,
                "link_format": link_format,
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

    def _generate_links(self, related_memories: List[Dict[str, Any]], link_format: str) -> List[str]:
        """Generate links in the specified format"""
        links = []
        
        for memory in related_memories:
            memory_id = memory["memory_id"]
            content = memory["content"]
            category = memory["category"]
            similarity = memory["similarity"]
            
            if link_format == "markdown":
                # Markdown link format: [content](memory_id) (similarity: 0.85, category: profile)
                link = f"[{content[:50]}...]({memory_id}) (similarity: {similarity:.2f}, category: {category})"
            elif link_format == "plain":
                # Plain text format: memory_id: content (similarity: 0.85)
                link = f"{memory_id}: {content[:50]}... (similarity: {similarity:.2f})"
            elif link_format == "json":
                # JSON format
                link = json.dumps({
                    "memory_id": memory_id,
                    "content": content,
                    "category": category,
                    "similarity": similarity
                })
            else:
                # Default to plain format
                link = f"{memory_id}: {content[:50]}... (similarity: {similarity:.2f})"
            
            links.append(link)
        
        return links

    def _append_links_to_memory(
        self,
        character_name: str,
        category: str,
        memory_id: str,
        links: List[str],
        link_format: str
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
                    # Append links to this memory item
                    original_line = item["full_line"]
                    
                    if link_format == "markdown":
                        links_section = "\n\n**Related Memories:**\n" + "\n".join(f"- {link}" for link in links)
                    else:
                        links_section = "\n\nRelated: " + " | ".join(links)
                    
                    updated_line = f"{original_line}{links_section}"
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