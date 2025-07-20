"""
Search Memory Action

Searches memory content using semantic embeddings and text matching.
"""

import json
import math
from typing import Dict, List, Any, Optional

from .base_action import BaseAction
from ...utils import get_logger

logger = get_logger(__name__)


class SearchMemoryAction(BaseAction):
    """Action to search memory content using embeddings and text matching"""
    
    @property
    def action_name(self) -> str:
        return "search_memory"
    
    def get_schema(self) -> Dict[str, Any]:
        """Return OpenAI-compatible function schema"""
        return {
            "name": "search_memory",
            "description": "Search memory content using semantic embeddings and text matching",
            "parameters": {
                "type": "object",
                "properties": {
                    "character_name": {
                        "type": "string",
                        "description": "Name of the character"
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "categories": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific categories to search (optional, searches all if not specified)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 5
                    },
                    "use_embeddings": {
                        "type": "boolean",
                        "description": "Whether to use semantic embedding search",
                        "default": True
                    }
                },
                "required": ["character_name", "query"]
            }
        }
    
    def execute(
        self,
        character_name: str,
        query: str,
        categories: Optional[List[str]] = None,
        limit: int = 5,
        use_embeddings: bool = True
    ) -> Dict[str, Any]:
        """
        Execute search memory operation
        
        Args:
            character_name: Name of the character
            query: Search query
            categories: Specific categories to search (None for all)
            limit: Maximum number of results
            use_embeddings: Whether to use embedding-based semantic search
            
        Returns:
            Dict containing search results with similarity scores
        """
        try:
            search_categories = categories or list(self.memory_types.keys())
            
            # Validate categories
            invalid_categories = [t for t in search_categories if t not in self.memory_types]
            if invalid_categories:
                return self._add_metadata({
                    "success": False,
                    "error": f"Invalid categories: {invalid_categories}. Available: {list(self.memory_types.keys())}"
                })
            
            results = []
            
            if use_embeddings and self.embeddings_enabled:
                # Use embedding-based semantic search
                results = self._semantic_memory_search(character_name, query, search_categories, limit)
            else:
                # Fallback to text-based search
                for category in search_categories:
                    content = self._read_memory_content(character_name, category)
                    if isinstance(content, str) and content and query.lower() in content.lower():
                        results.append({
                            "content": content,
                            "similarity": 1.0,
                            "type": category,
                            "character": character_name,
                            "search_method": "text_matching"
                        })
            
            return self._add_metadata({
                "success": True,
                "character_name": character_name,
                "query": query,
                "results": results[:limit],
                "total_results": len(results),
                "search_method": "semantic_embedding" if use_embeddings else "text_matching",
                "message": f"Found {len(results)} results for query: {query}"
            })
                
        except Exception as e:
            return self._handle_error(e)
    
    def _semantic_memory_search(self, character_name: str, query: str, categories: List[str], limit: int) -> List[Dict]:
        """Perform semantic search using stored embeddings - searches individual memory items (lines)"""
        try:
            if not self.embeddings_enabled or not self.embedding_client:
                return []
            
            # Generate query embedding
            query_embedding = self.embedding_client.embed(query)
            
            results = []
            char_embeddings_dir = self.embeddings_dir / character_name
            
            if not char_embeddings_dir.exists():
                return []
            
            for category in categories:
                embeddings_file = char_embeddings_dir / f"{category}_embeddings.json"
                
                if embeddings_file.exists():
                    try:
                        with open(embeddings_file, 'r', encoding='utf-8') as f:
                            embeddings_data = json.load(f)
                        
                        for emb_data in embeddings_data.get("embeddings", []):
                            similarity = self._cosine_similarity(query_embedding, emb_data["embedding"])
                            
                            if similarity > 0.3:  # Similarity threshold
                                results.append({
                                    "content": emb_data["text"],
                                    "similarity": similarity,
                                    "type": category,
                                    "character": character_name,
                                    "search_method": "semantic_embedding",
                                    "item_id": emb_data.get("item_id", ""),
                                    "line_number": emb_data.get("line_number", 0),
                                    "metadata": emb_data.get("metadata", {})
                                })
                    
                    except Exception as e:
                        logger.warning(f"Failed to load embeddings for {category}: {e}")
            
            # Sort by similarity and return top results
            results.sort(key=lambda x: x["similarity"], reverse=True)
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Semantic search failed for {character_name}: {e}")
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
            
        except Exception as e:
            logger.warning(f"Cosine similarity calculation failed: {e}")
            return 0.0 