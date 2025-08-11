import itertools
import os
import re
from typing import Any, Dict, List

from .base_action import BaseAction


class ClusterMemoriesAction(BaseAction):
    """
    Cluster memories into different categories.
    """

    @property
    def action_name(self) -> str:
        return "cluster_memories"

    def get_schema(self) -> Dict[str, Any]:
        """Return OpenAI-compatible function schema"""
        return {
            "name": self.action_name,
            "description": "Cluster memories into different categories",
            "parameters": {
                "type": "object",
                "properties": {
                    "character_name": {
                        "type": "string",
                        "description": "Name of the character",
                    },
                    "conversation_content": {
                        "type": "string",
                        "description": "The full conversation content to provide context for clustering",
                    },
                    "new_memory_items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "memory_id": {"type": "string"},
                                "content": {"type": "string"},
                                "mentioned_at": {"type": "string"},
                            },
                            "required": ["memory_id", "content", "mentioned_at"],
                        },
                        "description": "List of new memory items from the conversation",
                    },
                },
                "required": ["character_name", "conversation_content", "new_memory_items"],
            },
        }

    def execute(
        self,
        character_name: str,
        conversation_content: str,
        new_memory_items: List[Dict[str, str]],
        new_theory_of_mind_items: List[Dict[str, str]] = [],
        # available_categories: List[str]
        session_date: str = None,
    ) -> Dict[str, Any]:
        """
        Cluster memories into different categories
        """

        if session_date:
            for item in new_memory_items:
                if not item.get("mentioned_at", None):
                    item["mentioned_at"] = session_date

        existing_clusters = self.memory_types["cluster"].keys()
        # existing_clusters = [cluster.replace("_", " ") for cluster in existing_clusters]

        updated_clusters = {}
        if existing_clusters:
            updated_clusters = self._merge_existing_clusters(
                character_name,
                conversation_content,
                existing_clusters,
                new_memory_items,
                new_theory_of_mind_items,
            )

        new_clusters = self._detect_new_clusters(
            character_name,
            conversation_content,
            existing_clusters,
            new_memory_items,
            new_theory_of_mind_items,
        )

        return self._add_metadata(
            {
                "success": True,
                "character_name": character_name,
                "updated_clusters": sorted(updated_clusters.keys()),
                "new_clusters": sorted(new_clusters.keys()),
                "message": f"Analyzed {len(new_memory_items)} new memory items. Updated {len(updated_clusters)} existing clusters and detected {len(new_clusters)} new clusters",
            }
        )

    def _format_memory_item(self, memory_item: Dict[str, str]) -> str:
        """Format memory items into a string"""
        return f"[{memory_item['memory_id']}][mentioned at {memory_item['mentioned_at']}] {memory_item['content']} [{memory_item['memory_id']}]"

    def _merge_existing_clusters(
        self,
        character_name: str,
        conversation_content: str,
        existing_clusters: List[str],
        new_memory_items: List[Dict[str, str]],
        new_theory_of_mind_items: List[Dict[str, str]],
        count_threshold: int = 3,
    ) -> List[str]:
        """
        Merge existing clusters with new memory items and theory of mind items
        """

        all_items = {
            item["memory_id"]: item
            for item in itertools.chain(new_memory_items, new_theory_of_mind_items)
        }

        memory_items_text = "\n".join(
            [
                f"Memory ID: {item['memory_id']}\nContent: {item['content']}"
                for item in all_items.values()
            ]
        )

        # Create cluster list string outside f-string to avoid backslash issue
        clusters_list = "\n".join(f"- {cluster}" for cluster in existing_clusters)

        system_message = f"""You are an expert in analyzing and categorizing memories items.

You are given a list of existing clusters, a list of memory items, and the full conversation context that generated these memories.
Your task is to analyze if each of the memory items is related to any of the existing clusters.

**CONVERSATION CONTEXT:**
{conversation_content}

**EXISTING CLUSTERS:**
{clusters_list}

**MEMORY ITEMS:**
{memory_items_text}

**INSTRUCTIONS:**
1. Use the conversation context to better understand the background and relationships of the memory items.
2. It is possible that a memory item is related to multiple clusters.
Example: "We went to hiking in Blue Ridge Mountains this summer" is related to both "hiking" and "summer events" clusters, if both these two clusters are in the Existing Clusters.
3. If it possible that some memory items are not related to any of the existing clusters, you don't need to force them into any cluster.
4. DO NOT output memory items that are not related to any of the existing clusters.
5. Consider the conversation context when determining relationships - topics discussed together might belong to the same cluster.

**OUTPUT FORMAT:**
- [Memory ID]: [Cluster names that the memory item is related to, separated by comma]
- [Memory ID]: [Cluster names that the memory item is related to, separated by comma]
- ...
"""

        response = self.llm_client.simple_chat(system_message)

        if not response.strip():
            return self._add_metadata(
                {"success": False, "error": "LLM returned empty response"}
            )

        updated_clusters = {}

        for line in response.split("\n"):
            if not line.startswith("- "):
                continue

            memory_id, clusters = line[2:].split(": ", 1)
            memory_id = memory_id.strip()
            if memory_id not in all_items:
                continue

            for cluster in clusters.split(","):
                if cluster not in existing_clusters:
                    continue

                self.storage_manager.append_memory_file(cluster, self._format_memory_item(all_items[memory_id]))
                
                if cluster not in updated_clusters:
                    updated_clusters[cluster] = []
                updated_clusters[cluster].append(memory_id)

        return updated_clusters

    def _detect_new_clusters(
        self,
        character_name: str,
        conversation_content: str,
        existing_clusters: List[str],
        new_memory_items: List[Dict[str, str]],
        new_theory_of_mind_items: List[Dict[str, str]],
        count_threshold: int = 3,
    ) -> List[str]:
        """
        Detect new clusters from new memory items and theory of mind items
        """

        all_items = {
            item["memory_id"]: item
            for item in itertools.chain(new_memory_items, new_theory_of_mind_items)
        }

        memory_items_text = "\n".join(
            [
                f"Memory ID: {item['memory_id']}\nContent: {item['content']}"
                for item in all_items.values()
            ]
        )

        # Create cluster list string outside f-string to avoid backslash issue
        existing_clusters_list = "\n".join(
            f"- {cluster}" for cluster in existing_clusters
        )

        system_message = f"""You are an expert in discovering some important or repeating events in one's memory records.

You are given a conversation context, a list of memory items extracted from this conversation, and existing clusters.
Your task is to discover NEW events/themes that are either:
- Important (e.g., marriage, job promotion, etc.), or
- Repeating, periodical, or routine (e.g., going to gym, attending specific events, etc.).

**CONVERSATION CONTEXT:**
{conversation_content}

**EXISTING CLUSTERS (DO NOT recreate these):**
{existing_clusters_list}

**MEMORY ITEMS:**
{memory_items_text}

**INSTRUCTIONS:**
1. Use the conversation context to better understand the significance and relationships of events.
2. Only create NEW clusters - do not recreate existing clusters listed above.
3. You should create a Event Name for each NEW event you discover.
4. The Event Name should be short and clear. A single word is the best (e.g., "marriage", "hiking"). Never let the name be longer than 3 words.
5. The Event Name should contains only alphabets or space. DO NOT use any other characters including hyphen, underscore, etc.
6. An event can be considered repeating, periodical, or routine, if they are mentioned at least twice in the memory items OR if the conversation context suggests it's a recurring theme.
7. If an event is considered important enough (e.g., proposal), you should record it no matter how many times it is mentioned.
8. For event content that are close (e.g., hiking and backpacking), you can merge them into a single event, and accumulate the count.
9. Consider the conversation flow - events discussed together might indicate related themes or patterns.

**OUTPUT FORMAT:**
- [Event Name]: [Memory ID of ALL memory items related to this event, separated by comma]
- [Event Name]: [Memory ID of ALL memory items related to this event, separated by comma]
- ...
"""

        response = self.llm_client.simple_chat(system_message)

        if not response.strip():
            return self._add_metadata(
                {"success": False, "error": "LLM returned empty response"}
            )

        new_clusters = {}

        for line in response.split("\n"):
            if not line.startswith("- "):
                continue

            cluster, memory_ids = line[2:].split(": ", 1)
            cluster = cluster.strip().lower()

            if cluster not in self.memory_types["cluster"]:
                new_clusters[cluster] = []
                self.storage_manager.create_cluster_category(cluster)

            for memory_id in memory_ids.split(","):
                memory_id = memory_id.strip()
                if memory_id not in all_items:
                    continue
                self.storage_manager.append_memory_file(cluster, self._format_memory_item(all_items[memory_id]))

                new_clusters[cluster].append(memory_id)

        return new_clusters
