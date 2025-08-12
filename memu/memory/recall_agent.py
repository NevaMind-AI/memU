"""
RecallAgent for MemU Memory System

A simple workflow for intelligent memory retrieval based on markdown configurations.
Handles context=all (full content) and context=rag (search with limitations) based on config.
"""

import json
import math
from pathlib import Path
from typing import Any, Dict, List

from ..config.markdown_config import get_config_manager
from ..utils import get_logger
from .embeddings import get_default_embedding_client
from .file_manager import MemoryFileManager

logger = get_logger(__name__)


class RecallAgent:
    """
    Enhanced workflow for intelligent memory retrieval with three distinct methods.
    Automatically scans {agent_id}/{user_id}/{category}.md files in memory directory.

    Three core retrieval methods:
    1. retrieve_default_category: Get content from ['profile', 'event'] categories
    2. retrieve_relevant_category: Get top-k similar category names (excluding profile/event/activity)
    3. retrieve_relevant_memories: Get top-k memories using embedding search
    """

    def __init__(self, memory_dir: str = "memu/server/memory", agent_id: str = None, user_id: str = None):
        """
        Initialize Recall Agent

        Args:
            memory_dir: Directory where memory files are stored
            agent_id: Agent identifier
            user_id: User identifier
        """
        self.memory_dir = Path(memory_dir)

        # Initialize config manager
        self.config_manager = get_config_manager()
        self.memory_types = self.config_manager.get_file_types_mapping()

        # Initialize file-based storage manager
        self.storage_manager = MemoryFileManager(memory_dir, agent_id=agent_id, user_id=user_id)

        # Initialize embedding client for semantic search
        try:
            self.embedding_client = get_default_embedding_client()
            self.semantic_search_enabled = True
            logger.info("Semantic search enabled")
        except Exception as e:
            logger.warning(
                f"Failed to initialize embedding client: {e}. Semantic search disabled."
            )
            self.embedding_client = None
            self.semantic_search_enabled = False

        # Default categories for core retrieval
        self.default_categories = ["profile", "event"]

        logger.info(
            f"Recall Agent initialized with memory directory: {self.memory_dir}"
        )

    def retrieve_default_category(self, agent_id: str = None, user_id: str = None) -> Dict[str, Any]:
        """
        Method 1: Retrieve Default Category
        Get complete content from ['profile', 'event'] categories

        Args:
            agent_id: Agent identifier
            user_id: User identifier

        Returns:
            Dict containing default category content
        """
        try:
            results = []

            all_categories = self.storage_manager.list_memory_files()
            existing_defaults = [
                cat for cat in self.default_categories if cat in all_categories
            ]

            for category in self.default_categories:
                content = self.storage_manager.read_memory_file(category)
                if content:
                    results.append(
                        {
                            "category": category,
                            "content": content,
                            "content_type": "default_category",
                            "length": len(content),
                            "lines": len(content.split("\n")),
                            "file_exists": category in all_categories,
                        }
                    )
                else:
                    logger.debug(f"No content found for {agent_id}:{user_id}:{category}")

            return {
                "success": True,
                "method": "retrieve_default_category",
                "requested_categories": self.default_categories,
                "existing_categories": existing_defaults,
                "all_categories_found": all_categories,
                "results": results,
                "total_items": len(results),
                "message": f"Retrieved {len(results)} default categories for {agent_id}:{user_id} (found {len(existing_defaults)}/{len(self.default_categories)} requested files)",
            }

        except Exception as e:
            logger.error(
                f"Error in retrieve_default_category for {agent_id}:{user_id}: {e}"
            )
            return {
                "success": False,
                "error": str(e),
                "method": "retrieve_default_category",
            }

    def retrieve_relevant_category(
        self, agent_id: str, user_id: str, query: str, top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Method 2: Retrieve Relevant Category
        Retrieve relevant contents from top-k similar category names (excluding profile, event, and activity)
        Scans actual {agent_id}/{user_id}/{category}.md files in memory directory

        Args:
            agent_id: Agent identifier 
            user_id: User identifier
            query: Search query for category relevance
            top_k: Number of top categories to return

        Returns:
            Dict containing relevant category content
        """
        try:
            all_categories = self.storage_manager.list_memory_files("all")
            excluded_categories = self.default_categories + ["activity"]
            relevant_categories = [
                cat for cat in all_categories if cat not in excluded_categories
            ]

            if not relevant_categories:
                return {
                    "success": True,
                    "method": "retrieve_relevant_category",
                    "query": query,
                    "results": [],
                    "total_items": 0,
                    "message": "No categories available (excluding profile/event/activity)",
                }

            # Calculate category relevance scores
            category_scores = []
            query_lower = query.lower()
            query_words = set(query_lower.split())

            for category in relevant_categories:
                # Check if category has content for this character
                content = self.storage_manager.read_memory_file(category)
                if not content:
                    continue

                # Semantic search for content relevance
                content_relevance = 0.0
                if self.semantic_search_enabled and self.embedding_client:
                    try:
                        # Generate embeddings for query and content
                        query_embedding = self.embedding_client.embed(query)
                        content_embedding = self.embedding_client.embed(
                            content[:1000]
                        )  # Limit content length for embedding

                        # Calculate semantic similarity
                        semantic_similarity = self._cosine_similarity(
                            query_embedding, content_embedding
                        )
                        content_relevance = semantic_similarity
                    except Exception as e:
                        logger.warning(f"Semantic search failed for {category}: {e}")
                        # Fallback to simple keyword matching
                        content_lower = content.lower()
                        content_relevance = (
                            sum(1 for word in query_words if word in content_lower)
                            / len(query_words)
                            if query_words
                            else 0
                        )
                else:
                    # Fallback to simple keyword matching when semantic search is not available
                    content_lower = content.lower()
                    content_relevance = (
                        sum(1 for word in query_words if word in content_lower)
                        / len(query_words)
                        if query_words
                        else 0
                    )

                # Use semantic score directly
                combined_score = content_relevance

                if combined_score > 0:
                    category_scores.append(
                        {
                            "category": category,
                            "content": content,
                            "score": combined_score,
                            "content_relevance": content_relevance,
                            "semantic_search_used": self.semantic_search_enabled
                            and self.embedding_client is not None,
                            "length": len(content),
                            "lines": len(content.split("\n")),
                        }
                    )

            # Sort by score and get top-k
            category_scores.sort(key=lambda x: x["score"], reverse=True)
            top_categories = category_scores[:top_k]

            # Format results
            results = []
            for item in top_categories:
                results.append(
                    {
                        "category": item["category"],
                        "content": item["content"],
                        "content_type": "relevant_category",
                        "relevance_score": item["score"],
                        "content_relevance": item["content_relevance"],
                        "semantic_search_used": item["semantic_search_used"],
                        "length": item["length"],
                        "lines": item["lines"],
                    }
                )

            return {
                "success": True,
                "method": "retrieve_relevant_category",
                "query": query,
                "top_k": top_k,
                "all_categories_found": all_categories,
                "excluded_categories": excluded_categories,
                "available_categories": relevant_categories,
                "semantic_search_enabled": self.semantic_search_enabled,
                "results": results,
                "total_items": len(results),
                "message": f"Retrieved top {len(results)} relevant categories for query '{query}' using semantic search from {len(all_categories)} total categories",
            }

        except Exception as e:
            logger.error(
                f"Error in retrieve_relevant_category for {agent_id}:{user_id}: {e}"
            )
            return {
                "success": False,
                "error": str(e),
                "method": "retrieve_relevant_category",
                "query": query,
            }

    def retrieve_relevant_memories(
        self, agent_id: str, user_id: str, query: str, top_k: int = 10
    ) -> Dict[str, Any]:
        """
        Method 3: Retrieve Relevant Memories
        Retrieve top-k memories using embedding search across all categories

        Args:
            agent_id: Agent identifier 
            user_id: User identifier
            query: Search query for memory retrieval
            top_k: Number of top memories to return

        Returns:
            Dict containing relevant memories
        """
        try:
            if not self.semantic_search_enabled:
                return {
                    "success": False,
                    "error": "Semantic search not available - embedding client not initialized",
                    "method": "retrieve_relevant_memories",
                    "query": query,
                }

            # Generate query embedding
            query_embedding = self.embedding_client.embed(query)

            results = []
            
            # Get embeddings directory from storage manager
            embeddings_dir = self.storage_manager.get_char_embeddings_dir()

            if not embeddings_dir.exists():
                return {
                    "success": True,
                    "method": "retrieve_relevant_memories",
                    "query": query,
                    "results": [],
                    "total_items": 0,
                    "message": f"No embeddings found for {agent_id}:{user_id} in {embeddings_dir}",
                }

            # Search through all embedding files for this character
            for embeddings_file in embeddings_dir.glob("*_embeddings.json"):
                category = embeddings_file.stem.replace("_embeddings", "")

                try:
                    with open(embeddings_file, "r", encoding="utf-8") as f:
                        embeddings_data = json.load(f)

                    # Search through stored embeddings
                    for emb_data in embeddings_data.get("embeddings", []):
                        similarity = self._cosine_similarity(
                            query_embedding, emb_data["embedding"]
                        )

                        if (
                            similarity > 0.1
                        ):  # Minimum threshold for semantic similarity
                            results.append(
                                {
                                    "content": emb_data["text"],
                                    "content_type": "relevant_memory",
                                    "semantic_score": similarity,
                                    "category": category,
                                    "item_id": emb_data.get("item_id", ""),
                                    "memory_id": emb_data.get("memory_id", ""),
                                    "line_number": emb_data.get("line_number", 0),
                                    "length": len(emb_data["text"]),
                                    "metadata": emb_data.get("metadata", {}),
                                }
                            )

                except Exception as e:
                    logger.warning(f"Failed to process embeddings for {category}: {e}")

            # Sort by semantic score and get top-k
            results.sort(key=lambda x: x["semantic_score"], reverse=True)
            top_memories = results[:top_k]

            return {
                "success": True,
                "method": "retrieve_relevant_memories",
                "query": query,
                "top_k": top_k,
                "semantic_search_enabled": self.semantic_search_enabled,
                "results": top_memories,
                "total_items": len(top_memories),
                "total_candidates": len(results),
                "message": f"Retrieved top {len(top_memories)} memories from {len(results)} candidates",
            }

        except Exception as e:
            logger.error(
                f"Error in retrieve_relevant_memories for {agent_id}:{user_id}: {e}"
            )
            return {
                "success": False,
                "error": str(e),
                "method": "retrieve_relevant_memories",
                "query": query,
            }

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

    def get_status(self) -> Dict[str, Any]:
        """Get status information about the recall agent"""
        return {
            "agent_name": "recall_agent",
            "agent_type": "enhanced_retrieval",
            "memory_types": list(self.memory_types.keys()),
            "memory_dir": str(self.memory_dir),
            "semantic_search_enabled": self.semantic_search_enabled,
            "default_categories": self.default_categories,
            "config_source": "markdown_config.py",
            "retrieval_methods": [
                "retrieve_default_category(agent_id, user_id)",
                "retrieve_relevant_category(agent_id, user_id, query, top_k) - excludes profile/event/activity",
                "retrieve_relevant_memories(agent_id, user_id, query, top_k)",
            ],
        }
