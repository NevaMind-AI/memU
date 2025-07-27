
import os
import re
from typing import Dict, Any, List
from datetime import datetime
import itertools

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
                        "description": "Name of the character"
                    },
                    "conversation_content": {
                        "type": "string",
                        "description": "The full conversation content to provide context for clustering"
                    },
                    "new_memory_items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "memory_id": {"type": "string"},
                                "content": {"type": "string"}
                            },
                            "required": ["memory_id", "content"]
                        },
                        "description": "List of new memory items from the conversation"
                    },
                    # "new_theory_of_mind_items": {
                    #     "type": "array",
                    #     "items": {
                    #         "type": "object",
                    #         "properties": {
                    #             "memory_id": {"type": "string"},
                    #             "content": {"type": "string"}
                    #         },
                    #         "required": ["memory_id", "content"]
                    #     },
                    #     "description": "List of new theory of mind items from the conversation"
                    # },
                    # "available_categories": {
                    #     "type": "array",
                    #     "items": {"type": "string"},
                    #     "description": "List of available memory categories"
                    # }
                },
                "required": ["character_name", "conversation_content", "new_memory_items"]
                # "required": ["character_name", "new_memory_items", "new_theory_of_mind_items", "available_categories"]
            }
        }
    
    def execute(
        self,
        character_name: str,
        conversation_content: str,
        new_memory_items: List[Dict[str, str]],
        new_theory_of_mind_items: List[Dict[str, str]] = [],
        # available_categories: List[str]
    ) -> Dict[str, Any]:
        """
        Cluster memories into different categories
        """ 
        existing_clusters = self._get_existing_cluster_items(character_name)
        existing_clusters = [cluster.replace('_', ' ') for cluster in existing_clusters]

        if existing_clusters:
             self._merge_existing_clusters(character_name, conversation_content, existing_clusters, new_memory_items, new_theory_of_mind_items)

        new_clusters = self._detect_new_clusters(character_name, conversation_content, existing_clusters, new_memory_items, new_theory_of_mind_items)

        return self._add_metadata({
            "success": True,
            "character_name": character_name,
            # "existing_clusters": existing_clusters
        })

    def _get_existing_cluster_items(self, character_name: str) -> List[str]:
        """
        Get existing cluster items by listing files that match pattern {character_name}_($1).md
        and return the list of captured values ($1)
        """
        try:
            # List all files in the memory directory
            files = os.listdir("memory")
            
            # Create regex pattern to match {character_name}_($1).md
            # This will capture the text in parentheses as group 1
            pattern = rf"{re.escape(character_name)}_([^.]+)\.md$"
            
            existing_clusters = []
            for file in files:
                match = re.match(pattern, file)
                if match:
                    # Extract the captured group (the text in parentheses)
                    cluster_name = match.group(1)
                    if cluster_name not in self.memory_types:
                        existing_clusters.append(cluster_name)

            return existing_clusters
        except FileNotFoundError:
            # Return empty list if directory doesn't exist
            return []

    def _merge_existing_clusters(self, 
        character_name: str,
        conversation_content: str,
        existing_clusters: List[str], 
        new_memory_items: List[Dict[str, str]], 
        new_theory_of_mind_items: List[Dict[str, str]],
        count_threshold: int = 3
    ) -> List[str]:
        """
        Merge existing clusters with new memory items and theory of mind items
        """

        all_items = {item['memory_id']: item for item in itertools.chain(new_memory_items, new_theory_of_mind_items)}

        memory_items_text = "\n".join([
            f"Memory ID: {item['memory_id']}\nContent: {item['content']}"
            for item in all_items.values()
        ])
        
        system_message = f"""You are an expert in analyzing and categorizing memories items.

You are given a list of existing clusters, a list of memory items, and the full conversation context that generated these memories.
Your task is to analyze if each of the memory items is related to any of the existing clusters.

**CONVERSATION CONTEXT:**
{conversation_content}

**EXISTING CLUSTERS:**
{'\n'.join(f"- {cluster}" for cluster in existing_clusters)}

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

        dump_debug(f"[merge] {repr(response)}")

        if not response.strip():
            return self._add_metadata({
                "success": False,
                "error": "LLM returned empty response"
            })

        updated_clusters = {}

        for line in response.split('\n'):
            if not line.startswith('- '):
                continue

            memory_id, clusters = line[2:].split(': ', 1)
            memory_id = memory_id.strip()
            if not memory_id in all_items:
                continue

            for cluster in clusters.split(','):
                if not cluster in existing_clusters:
                    continue
                cluster_fn = cluster.replace(' ', '_')
                with open(f"memory/{character_name}_{cluster_fn}.md", "a") as f:
                    memory_item = all_items[memory_id]
                    # f.write(f"[{memory_id}][mentioned at {memory_item['session_date']}] {memory_item['content']} []\n")
                    f.write(f"[{memory_id}][mentioned at {memory_item.get('session_date', 'Unknown')}] {memory_item['content']} []\n")
                if not cluster in updated_clusters:
                    updated_clusters[cluster] = []
                updated_clusters[cluster].append(memory_id)

        return self._add_metadata({
            "success": True,
            "character_name": character_name,
            "updated_clusters": updated_clusters
        })

    def _detect_new_clusters(self, 
        character_name: str, 
        conversation_content: str,
        existing_clusters: List[str], 
        new_memory_items: List[Dict[str, str]], 
        new_theory_of_mind_items: List[Dict[str, str]],
        count_threshold: int = 3
    ) -> List[str]:
        """
        Detect new clusters from new memory items and theory of mind items
        """

        all_items = {item['memory_id']: item for item in itertools.chain(new_memory_items, new_theory_of_mind_items)}
        
        memory_items_text = "\n".join([
            f"Memory ID: {item['memory_id']}\nContent: {item['content']}"
            for item in all_items.values()
        ])

        system_message = f"""You are an expert in discovering some important or repeating events in one's memory records.

You are given a conversation context, a list of memory items extracted from this conversation, and existing clusters.
Your task is to discover NEW events/themes that are either:
- Important (e.g., marriage, job promotion, etc.), or 
- Repeating, periodical, or routine (e.g., going to gym, attending specific events, etc.).

**CONVERSATION CONTEXT:**
{conversation_content}

**EXISTING CLUSTERS (DO NOT recreate these):**
{'\n'.join(f"- {cluster}" for cluster in existing_clusters)}

**MEMORY ITEMS:**
{memory_items_text}

**INSTRUCTIONS:**
1. Use the conversation context to better understand the significance and relationships of events.
2. Only create NEW clusters - do not recreate existing clusters listed above.
3. You should create a Event Name for each NEW event you discover.
4. The Event Name should be short and clear. A single word is the best (e.g., "marriage", "hiking"). Never let the name be longer than 3 words.
5. An event can be considered repeating, periodical, or routine, if they are mentioned at least twice in the memory items OR if the conversation context suggests it's a recurring theme.
6. If an event is considered important enough (e.g., proposal), you should record it no matter how many times it is mentioned.
7. For event content that are close (e.g., hiking and backpacking), you can merge them into a single event, and accumulate the count.
8. Consider the conversation flow - events discussed together might indicate related themes or patterns.

**OUTPUT FORMAT:**
- [Event Name]: [Memory ID of ALL memory items related to this event, separated by comma]
- [Event Name]: [Memory ID of ALL memory items related to this event, separated by comma]
- ...
"""

        response = self.llm_client.simple_chat(system_message)

        if not response.strip():
            return self._add_metadata({
                "success": False,
                "error": "LLM returned empty response"
            })


        dump_debug(f"{repr(all_items)}")
        dump_debug(f"[detect] {repr(response)}")

        new_clusters = {}

        for line in response.split('\n'):
            if not line.startswith('- '):
                continue

            cluster, memory_ids = line[2:].split(': ', 1)
            cluster_fn = cluster.replace(' ', '_')
            with open(f"memory/{character_name}_{cluster_fn}.md", "a") as f:
                if cluster not in existing_clusters:
                    new_clusters[cluster] = []

                for memory_id in memory_ids.split(','):
                    memory_id = memory_id.strip()
                    if not memory_id in all_items:
                        continue
                    memory_item = all_items[memory_id]

                    dump_debug(f"[add] {cluster} {repr(memory_item)}")

                    # f.write(f"[{memory_id}][mentioned at {memory_item['session_date']}] {memory_item['content']} []\n")
                    f.write(f"[{memory_id}][mentioned at {memory_item.get('session_date', 'Unknown')}] {memory_item['content']} []\n")
                    
                    new_clusters[cluster].append(memory_id)
            
        return self._add_metadata({
            "success": True,
            "character_name": character_name,
            "new_clusters": new_clusters
        })

def dump_debug(string: str):
    with open("debug/cluster_debug.txt", "a") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] {string}\n")