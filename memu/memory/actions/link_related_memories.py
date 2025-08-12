"""
Link Related Memories Action

Automatically finds and links related memories using embedding search.
"""

import json
import math
from typing import Any, Dict, List, Optional

from ...utils import get_logger
from .base_action import BaseAction

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
        self.filter_with_llm = False

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
                        "description": "Name of the character",
                    },
                    "memory_id": {
                        "type": "string",
                        "description": "ID of the memory item to find related memories for (optional if link_all_items is true)",
                    },
                    "category": {
                        "type": "string",
                        "description": "Category containing the target memory item",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of top related memories to find",
                        "default": 5,
                    },
                    "min_similarity": {
                        "type": "number",
                        "description": "Minimum similarity threshold (0.0-1.0)",
                        "default": 0.3,
                    },
                    "search_categories": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Categories to search in (default: all available categories)",
                    },
                    "link_all_items": {
                        "type": "boolean",
                        "description": "Whether to link all memory items in the category (if true, memory_id can be omitted)",
                        "default": False,
                    },
                },
                "required": ["character_name", "category"],
            },
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
        write_to_memory: bool = True,
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
                return self._add_metadata(
                    {
                        "success": False,
                        "error": "Embeddings are not enabled. Cannot perform similarity search.",
                    }
                )

            if category not in self.basic_memory_types:
                return self._add_metadata(
                    {
                        "success": False,
                        "error": f"Skipping category '{category}' not in available categories. Available: {list(self.basic_memory_types.keys())}",
                    }
                )

            # If link_all_items is True, process all memory items in the category
            if link_all_items:
                return self._link_all_items_in_category(
                    character_name,
                    category,
                    top_k,
                    min_similarity,
                    search_categories,
                    write_to_memory,
                )

            # Otherwise, process single memory item
            if not memory_id:
                return self._add_metadata(
                    {
                        "success": False,
                        "error": "memory_id is required when link_all_items is False",
                    }
                )

            # Find the target memory item
            target_memory = self._find_memory_item(character_name, category, memory_id)
            if not target_memory:
                return self._add_metadata(
                    {
                        "success": False,
                        "error": f"Memory ID '{memory_id}' not found in {category} for {character_name}",
                    }
                )

            # Generate embedding for target content
            target_embedding = self.embedding_client.embed(target_memory["content"])

            # Determine search categories - search in ALL categories by default
            if search_categories is None:
                search_categories = list(self.basic_memory_types.keys())

            # Find related memories
            related_memories = self._find_related_memories(
                character_name,
                target_embedding,
                target_memory["content"],
                search_categories,
                top_k,
                min_similarity,
                memory_id,
            )

            # Get memory IDs for links
            link_ids = [memory["memory_id"] for memory in related_memories]

            # Optionally write links to memory
            if write_to_memory and link_ids:
                self._append_links_to_memory(
                    character_name, category, memory_id, link_ids
                )

            return self._add_metadata(
                {
                    "success": True,
                    "character_name": character_name,
                    "linked_memory_ids": link_ids,
                    "total_related": len(related_memories),
                    "message": f"Found {len(related_memories)} related memories for {memory_id}",
                }
            )

        except Exception as e:
            return self._handle_error(e)

    def _find_memory_item(
        self, character_name: str, category: str, memory_id: str
    ) -> Optional[Dict[str, Any]]:
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
        target_content: str,
        search_categories: List[str],
        top_k: int,
        min_similarity: float,
        exclude_memory_id: str,
    ) -> List[Dict[str, Any]]:
        """Find related memories using embedding similarity across all categories"""
        all_candidates = []

        try:
            # Get character embeddings directory from storage manager
            char_embeddings_dir = self.storage_manager.get_char_embeddings_dir()
            if not char_embeddings_dir.exists():
                return []

            # Collect ALL embeddings from all categories first
            for category in search_categories:
                embeddings_file = char_embeddings_dir / f"{category}_embeddings.json"

                if embeddings_file.exists():
                    try:
                        with open(embeddings_file, "r", encoding="utf-8") as f:
                            embeddings_data = json.load(f)

                        for emb_data in embeddings_data.get("embeddings", []):
                            # Skip the target memory itself
                            if emb_data.get("memory_id") == exclude_memory_id:
                                continue

                            similarity = self._cosine_similarity(
                                target_embedding, emb_data["embedding"]
                            )

                            # Add ALL candidates regardless of similarity threshold initially
                            all_candidates.append(
                                {
                                    "memory_id": emb_data.get("memory_id", ""),
                                    "content": emb_data["text"],
                                    "full_line": emb_data.get(
                                        "full_line", emb_data["text"]
                                    ),
                                    "category": category,
                                    "similarity": similarity,
                                    "item_id": emb_data.get("item_id", ""),
                                    "line_number": emb_data.get("line_number", 0),
                                }
                            )

                    except Exception as e:
                        logger.warning(
                            f"Failed to load embeddings for {category}: {repr(e)}"
                        )

            # Sort ALL candidates by similarity globally
            all_candidates.sort(key=lambda x: x["similarity"], reverse=True)

            # Apply similarity threshold and take top K candidates for LLM filtering
            filtered_results = [
                candidate
                for candidate in all_candidates[
                    : top_k * 2
                ]  # Take more candidates first
                if candidate["similarity"] >= min_similarity
            ]

            # Use LLM to filter for truly relevant memories
            if filtered_results:
                if self.filter_with_llm:
                    relevant_memories = self._filter_relevant_memories_with_llm(
                        character_name, filtered_results, target_content, top_k
                    )
                else:
                    relevant_memories = sorted(
                        filtered_results, key=lambda x: x["similarity"], reverse=True
                    )[:top_k]
                return relevant_memories
            else:
                return []

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
        self, character_name: str, category: str, memory_id: str, related_memories: List[str]
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
                    updated_line = f"[{item['memory_id']}][mentioned at {item['mentioned_at']}] {item['content']} [{','.join(related_memories)}]"
                    updated_lines.append(updated_line)
                else:
                    updated_lines.append(item["full_line"])

            # Save updated content
            updated_content = "\n".join(updated_lines)
            success = self._save_memory_content(
                character_name, category, updated_content
            )

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
        write_to_memory: bool,
    ) -> Dict[str, Any]:
        """Link all memory items in a category to related memories"""
        try:
            # Get all memory items in the category
            content = self._read_memory_content(character_name, category)
            if not content:
                return self._add_metadata(
                    {
                        "success": False,
                        "error": f"No content found in {category} for {character_name}",
                    }
                )

            memory_items = self._parse_memory_items(content)
            if not memory_items:
                return self._add_metadata(
                    {"success": False, "error": f"No memory items found in {category}"}
                )

            # Determine search categories - search in ALL categories by default
            if search_categories is None:
                search_categories = list(self.basic_memory_types.keys())

            total_linked = 0

            # Process each memory item
            for item in memory_items:
                memory_id = item["memory_id"]

                # Generate embedding for this item's content
                target_embedding = self.embedding_client.embed(item["content"])

                # Find related memories
                related_memories = self._find_related_memories(
                    character_name,
                    target_embedding,
                    item["content"],
                    search_categories,
                    top_k,
                    min_similarity,
                    memory_id,
                )

                # Get memory IDs for links
                link_ids = [memory["memory_id"] for memory in related_memories]

                # Optionally write links to memory
                if write_to_memory and link_ids:
                    self._append_links_to_memory(
                        character_name, category, memory_id, link_ids
                    )
                    total_linked += 1

            return self._add_metadata(
                {
                    "success": True,
                    "character_name": character_name,
                    "category": category,
                    "total_items_processed": len(memory_items),
                    "total_items_linked": total_linked,
                    "message": f"Linked {total_linked} out of {len(memory_items)} memory items in {category}",
                }
            )

        except Exception as e:
            return self._handle_error(e)

    def _filter_relevant_memories_with_llm(
        self,
        character_name: str,
        candidate_memories: List[Dict[str, Any]],
        target_content: str,
        max_links: int,
    ) -> List[Dict[str, Any]]:
        """
        Use LLM to filter candidate memories and keep only truly relevant ones

        Args:
            character_name: Name of the character
            candidate_memories: List of candidate memories from embedding search
            target_content: The target memory content to compare against
            max_links: Maximum number of links to return

        Returns:
            List of filtered relevant memories
        """
        try:
            if not candidate_memories:
                return []

            # Prepare candidate memories for LLM evaluation
            candidates_text = ""
            for i, memory in enumerate(candidate_memories, 1):
                candidates_text += f"{i}. [ID: {memory['memory_id']}] [{memory['category']}] {memory['content']} (similarity: {memory['similarity']:.3f})\n"

            # Create LLM prompt for relevance filtering
            relevance_prompt = f"""You are evaluating whether candidate memories are truly related to a target memory for {character_name}.

TARGET MEMORY:
{target_content}

CANDIDATE MEMORIES:
{candidates_text}

**TASK**: Determine which candidate memories are genuinely related to the target memory.

**CRITERIA FOR RELEVANCE**:
- Memories should share meaningful connections (people, places, events, topics, themes)
- Avoid superficial similarities (just sharing common words like "the", "and", "is")
- Consider contextual relationships (cause-effect, temporal sequences, thematic connections)
- Focus on memories that would provide useful context or background for understanding the target memory

**EVALUATION GUIDELINES**:
- ✅ RELEVANT: Memories about the same people, events, locations, or directly related topics
- ✅ RELEVANT: Memories that provide context, background, or related information
- ❌ NOT RELEVANT: Memories that only share common words but different contexts
- ❌ NOT RELEVANT: Memories about completely different topics/people/events

**OUTPUT FORMAT**:
Return ONLY the numbers (1, 2, 3, etc.) of the truly relevant memories, separated by commas. If no memories are relevant, return "NONE".

Examples:
- If memories 1, 3, and 5 are relevant: "1, 3, 5"
- If no memories are relevant: "NONE"
- If only memory 2 is relevant: "2"

RELEVANT MEMORY NUMBERS:"""

            # Call LLM to evaluate relevance
            llm_response = self.llm_client.simple_chat(relevance_prompt)

            # Parse LLM response
            relevant_indices = self._parse_relevance_response(llm_response.strip())

            # Filter memories based on LLM evaluation
            relevant_memories = []
            for idx in relevant_indices:
                if 1 <= idx <= len(candidate_memories):
                    relevant_memories.append(
                        candidate_memories[idx - 1]
                    )  # Convert to 0-based index

            # Limit to max_links
            return relevant_memories[:max_links]

        except Exception as e:
            logger.error(f"Error filtering memories with LLM: {e}")
            # Fallback to original top candidates if LLM filtering fails
            return candidate_memories[:max_links]

    def _parse_relevance_response(self, response: str) -> List[int]:
        """
        Parse LLM response to extract relevant memory indices

        Args:
            response: LLM response containing memory numbers

        Returns:
            List of memory indices (1-based)
        """
        import re

        try:
            response = response.strip().upper()

            if response == "NONE" or not response:
                return []

            # Extract numbers from response
            numbers = re.findall(r"\b(\d+)\b", response)
            return [int(num) for num in numbers if num.isdigit()]

        except Exception as e:
            logger.warning(
                f"Failed to parse relevance response '{response}': {repr(e)}"
            )
            return []
