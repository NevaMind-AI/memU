"""
Update Memory with Suggestions Action

Updates memory categories based on new memory items and suggestions, supporting different operation types:
- ADD: Add new content
- UPDATE: Modify existing content
- DELETE: Delete specific content
- TOUCH: Use current content but don't update (mark as accessed)
"""

import json
from datetime import datetime
from typing import Any, Dict, List

from ...utils import get_logger
from .base_action import BaseAction

logger = get_logger(__name__)


class UpdateMemoryWithSuggestionsAction(BaseAction):
    """
    Update memory categories based on new memory items and suggestions,
    supporting different operation types (ADD, UPDATE, DELETE, TOUCH).
    """

    @property
    def action_name(self) -> str:
        return "update_memory_with_suggestions"

    def get_schema(self) -> Dict[str, Any]:
        """Return OpenAI-compatible function schema"""
        return {
            "name": self.action_name,
            "description": "Update memory categories with different operation types (ADD, UPDATE, DELETE, TOUCH)",
            "parameters": {
                "type": "object",
                "properties": {
                    "character_name": {
                        "type": "string",
                        "description": "Name of the character",
                    },
                    "category": {
                        "type": "string",
                        "description": "Memory category to update",
                    },
                    "suggestion": {
                        "type": "string",
                        "description": "Suggestion for what content should be processed in this category",
                    },
                    "session_date": {
                        "type": "string",
                        "description": "Session date for the memory items (format: YYYY-MM-DD)",
                        "default": None,
                    },
                    "generate_embeddings": {
                        "type": "boolean",
                        "default": True,
                        "description": "Whether to generate embeddings for the new content",
                    },
                },
                "required": ["character_name", "category", "suggestion"],
            },
        }

    def execute(
        self,
        character_name: str,
        category: str,
        suggestion: str,
        session_date: str = None,
        generate_embeddings: bool = True,
    ) -> Dict[str, Any]:
        """
        Update memory category with different operation types based on suggestions

        Args:
            character_name: Name of the character
            category: Memory category to update
            suggestion: Suggestion for what content should be processed
            session_date: Session date for the memory items (format: YYYY-MM-DD)
            generate_embeddings: Whether to generate embeddings

        Returns:
            Dict containing the operations performed in structured format
        """
        try:
            # Validate category
            if category not in self.basic_memory_types:
                return self._add_metadata(
                    {
                        "success": False,
                        "error": f"Invalid category '{category}'. Available: {list(self.basic_memory_types.keys())}",
                    }
                )

            if not session_date:
                session_date = datetime.now().strftime("%Y-%m-%d")

            # Load existing content
            existing_content = self._read_memory_content(character_name, category)
            existing_memory_items = self._extract_memory_items_from_content(
                existing_content
            )
            formatted_existing_content = self._format_existing_content(
                existing_memory_items
            )

            operation_response = self._analyze_memory_operation_from_suggestion(
                category, character_name, formatted_existing_content, suggestion
            )

            if not operation_response.strip():
                return {
                    "success": False,
                    "error": f"LLM returned empty operation analysis for {category}",
                }

            # Parse operation response
            operation_list = self._parse_operation_response(operation_response)
            operation_executed, new_items = self._execute_operations(
                character_name,
                category,
                operation_list,
                session_date,
                existing_memory_items,
                generate_embeddings,
            )

            return self._add_metadata(
                {
                    "success": True,
                    "character_name": character_name,
                    "category": category,
                    "operation_executed": operation_executed,
                    "new_memory_items": new_items,
                    "message": f"Successfully performed {len(operation_executed)} memory operations for {category}",
                }
            )

        except Exception as e:
            return self._handle_error(e)

    def _format_existing_content(
        self, existing_memory_items: List[Dict[str, str]]
    ) -> str:
        """Format existing content into a list of memory items"""
        return "\n".join(
            [
                f"[Memory ID: {item['memory_id']}] {item['content']}"
                for item in existing_memory_items
            ]
        )

    def _analyze_memory_operation_from_suggestion(
        self,
        category: str,
        character_name: str,
        existing_content: str,
        suggestion: str,
    ) -> str:
        """Analyze memory update scenario and determine the operations that should be performed"""

        operation_prompt = f"""You are an expert in analyzing the following memory update scenario and determining the memory operations that should be performed.

Character: {character_name}
Memory Category: {category}

Existing Memory Items in {category}:
{existing_content if existing_content else "No existing content"}

Memory Update Suggestion:
{suggestion}

**CRITICAL REQUIREMENT: The object of memory operations must be SELF-CONTAINED MEMORY ITEMS**

**SELF-CONTAINED MEMORY REQUIREMENTS:**
- EVERY activity item must be complete and standalone
- ALWAYS include the full subject (do not use "she/he/they/it")
- NEVER use pronouns that depend on context (no "she", "he", "they", "it")
- Include specific names, places, dates, and full context in each item
- Each activity should be understandable without reading other items
- Include all relevant details, emotions, and outcomes in the activity description

**OPERATION TYPES:**
1. **ADD**: Add completely new memory items that doesn't exist in Existing Memory Items
2. **UPDATE**: Modify or enhance existing memory items with new details
3. **DELETE**: Remove outdated, incorrect, or irrelevant memory items
4. **TOUCH**: Touch memory items that already exists in current content (only for updating last-mentioned timestamp)

**ANALYSIS GUIDELINES:**
- Read the Memory Update Suggestion carefully to determine what new memory items are offered
- Read the Existing Memory Items to view all memory items that are already present
- Determine the most appropriate operation type FOR EACH NEW MEMORY ITEM based on the new information and existing content
- **Use ADD for:** New memory items that are not covered in existing content
- **Use UPDATE for:** New memory items that provide updated details for existing memory items
- **Use DELETE for:** Existing memory items that are outdated/incorrect based on new memory items
- **Use TOUCH for:** Existing memory items that already covers the new memory items adequately

**OUTPUT INSTRUCTIONS:**
- **IMPORTANT** Output ALL necessary memory operations. It is common that you should perform different operations for different specific memory items
- For ADD and UPDATE operations, provide the content of the new memory items following the self-contained memory requirements
- For UPDATE, DELETE, and TOUCH operations, provide the target memory IDs associated with the memory items
- If there are multiple actions for an operation type (e.g, multiple ADDs), output them separately, do not put them in a single **OPERATION:** block
- **IMPORTANT** If a memory item in suggestion uses modal adverbs (perhaps, probably, likely, etc.) to indicate an uncertain inference, keep the modal adverbs as-is in your output

**OUTPUT FORMAT:**

**OPERATION:** [ADD/UPDATE/DELETE/TOUCH]
- Target Memory ID: [Only if operation is UPDATE, DELETE, or TOUCH][Memory ID of the memory item that is the target of the operation]
- Memory Item Content: [Only if operation is ADD or UPDATE][Content of the new memory item]

**OPERATION:** [ADD/UPDATE/DELETE/TOUCH]
- Target Memory ID: [Only if operation is UPDATE, DELETE, or TOUCH][Memory ID of the memory item that is the target of the operation]
- Memory Item Content: [Only if operation is ADD or UPDATE][Content of the new memory item]

... other operations ...
"""

        # Call LLM to determine operation type and content
        operation_response = self.llm_client.simple_chat(operation_prompt)
        return operation_response

    def _parse_operation_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response to extract operation info"""
        lines = response.strip().split("\n")

        operation_list = []
        current_operation = None

        for line in lines:
            line = line.strip()

            if line.startswith("**OPERATION:**"):
                operation = line.replace("**OPERATION:**", "").strip()
                if operation in ["ADD", "UPDATE", "DELETE", "TOUCH"]:
                    if current_operation:
                        """cleanup and completeness checks are not conducted here, they will be done in the execute function"""
                        operation_list.append(current_operation)
                    current_operation = {
                        "operation": operation,
                        "target_id": None,
                        "memory_content": None,
                    }

            if line.startswith("- Target Memory ID:"):
                target_id = line.replace("- Target Memory ID:", "").strip()
                current_operation["target_id"] = target_id

            if line.startswith("- Memory Item Content:"):
                memory_content = line.replace("- Memory Item Content:", "").strip()
                current_operation["memory_content"] = memory_content

        if current_operation:
            operation_list.append(current_operation)

        return operation_list

    def _execute_operations(
        self,
        character_name: str,
        category: str,
        operation_list: List[Dict[str, Any]],
        session_date: str,
        existing_items: List[Dict[str, str]],
        generate_embeddings: bool,
    ) -> List[Dict[str, Any]]:
        """Execute all operations in the list"""

        all_items = existing_items
        new_items = []
        updated_items = []
        operation_executed = []

        for operation in operation_list:
            if operation["operation"] == "ADD":
                if not operation["memory_content"]:
                    continue

                memory_id = self._generate_memory_id()
                memory_item = {
                    "memory_id": memory_id,
                    "mentioned_at": session_date,
                    "content": operation["memory_content"],
                    "links": "",
                }

                all_items.append(memory_item)
                new_items.append(memory_item)
                updated_items.append(memory_item)
                operation_executed.append(operation)

            if operation["operation"] == "UPDATE":
                if not operation["target_id"] or not operation["memory_content"]:
                    continue

                for item in all_items:
                    if item["memory_id"] == operation["target_id"]:
                        item["content"] = operation["memory_content"]
                        updated_items.append(item)
                        break

                operation_executed.append(operation)

            if operation["operation"] == "DELETE":
                if not operation["target_id"]:
                    continue

                for item in all_items:
                    if item["memory_id"] == operation["target_id"]:
                        all_items.remove(item)

                operation_executed.append(operation)

            if operation["operation"] == "TOUCH":
                if not operation["target_id"]:
                    continue

                for item in all_items:
                    if item["memory_id"] == operation["target_id"]:
                        """should update "updated_at" """
                        pass

                operation_executed.append(operation)

        new_content = self._format_memory_items(all_items)
        self._save_memory_content(character_name, category, new_content)

        if generate_embeddings and self.embeddings_enabled and updated_items:
            self._add_memory_item_embedding(character_name, category, updated_items)

        return operation_executed, new_items

    def _extract_memory_items_from_content(self, content: str) -> List[Dict[str, str]]:
        """Extract memory items with IDs from content, supporting both old and new timestamp formats"""
        import re

        items = []
        lines = content.split("\n")

        for line in lines:
            line = line.strip()

            pattern = r"^\[([^\]]+)\]\[mentioned at ([^\]]+)\]\s*(.*?)(?:\s*\[([^\]]*)\])?$"
            match = re.match(pattern, line)
            if match:
                memory_id = match.group(1)
                mentioned_at = match.group(2)
                clean_content = match.group(3).strip()
                links = match.group(4) if match.group(4) else ""

                if memory_id and clean_content:
                    items.append(
                        {
                            "memory_id": memory_id,
                            "mentioned_at": mentioned_at,
                            "content": clean_content,
                            "links": links,
                        }
                    )

        return items

    def _add_memory_item_embedding(
        self, character_name: str, category: str, new_items: list[dict]
    ) -> Dict[str, Any]:
        """Add embedding for new memory items"""
        try:
            if not self.embeddings_enabled or not new_items:
                return {"success": False, "error": "Embeddings disabled or empty item"}

            # Get character embeddings directory from storage manager
            char_embeddings_dir = self.storage_manager.get_char_embeddings_dir()
            embeddings_file = char_embeddings_dir / f"{category}_embeddings.json"

            existing_embeddings = []
            if embeddings_file.exists():
                with open(embeddings_file, "r", encoding="utf-8") as f:
                    embeddings_data = json.load(f)
                    existing_embeddings = embeddings_data.get("embeddings", [])

            # Generate embeddings for new items
            for item in new_items:
                if not item["content"].strip():
                    continue

                try:
                    embedding_vector = self.embedding_client.embed(item["content"])
                    
                    new_item_id = (
                        f"{character_name}_{category}_item_{len(existing_embeddings)}"
                    )

                    new_embedding = {
                        "item_id": new_item_id,
                        "memory_id": item["memory_id"],
                        "text": item["content"],
                        "full_line": f"[{item['memory_id']}][mentioned at {item['mentioned_at']}] {item['content']} [{item['links']}]",
                        "embedding": embedding_vector,
                        "line_number": len(existing_embeddings) + 1,
                        "metadata": {
                            "character": character_name,
                            "category": category,
                            "length": len(item["content"]),
                            "mentioned_at": item["mentioned_at"],
                            "timestamp": datetime.now().isoformat(),
                        },
                    }

                    # Add to existing embeddings
                    existing_embeddings.append(new_embedding)

                except Exception as e:
                    logger.warning(
                        f"Failed to generate embedding for memory item {item.get('memory_id')}: {repr(e)}"
                    )
                    continue

            # Save updated embeddings
            embeddings_data = {
                "category": category,
                "timestamp": datetime.now().isoformat(),
                # "content_hash": hashlib.md5(new_content.encode()).hexdigest(),
                "embeddings": existing_embeddings,
                "total_embeddings": len(existing_embeddings),
            }

            with open(embeddings_file, "w", encoding="utf-8") as f:
                json.dump(embeddings_data, f, indent=2, ensure_ascii=False)

            return {
                "success": True,
                "embedding_count": len(existing_embeddings),
                "new_items_count": len(new_items),
                "message": f"Added embeddings for {len(new_items)} new memory items in {category}",
            }

        except Exception as e:
            logger.error(f"Failed to add memory item embedding: {e}")
            return {"success": False, "error": str(e)}

    def _format_memory_items(self, items: List[Dict[str, str]]) -> str:
        """Format memory items into a string"""
        return "\n".join(
            [
                f"[{item['memory_id']}][mentioned at {item['mentioned_at']}] {item['content']} [{item['links']}]"
                for item in items
            ]
        )

    def _load_category_extract_prompt(
        self,
        category: str,
        character_name: str,
        existing_content: str,
        memory_items_text: str,
        suggestion: str,
    ) -> str:
        """
        Load category-specific prompt template to extract NEW content only

        Args:
            category: Memory category (profile, event, activity, etc.)
            character_name: Name of the character
            existing_content: Existing content in the category
            memory_items_text: Source activity content to extract from
            suggestion: Suggestion for what to extract

        Returns:
            Formatted prompt for extracting new content only
        """
        from pathlib import Path

        # Load category-specific prompt
        config_dir = Path(__file__).parent.parent.parent / "config" / category
        prompt_file = config_dir / "prompt.txt"

        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

        # Load and format the prompt template
        with open(prompt_file, "r", encoding="utf-8") as f:
            prompt_template = f.read()

        # Format the prompt with variables for extracting NEW content only
        extract_prompt = f"""Based on the following category-specific requirements, extract ONLY NEW information for the {category} memory:

{prompt_template}

=== EXTRACTION CONTEXT ===

EXISTING {category} content (DO NOT DUPLICATE):
{existing_content if existing_content else "No existing content"}

Source activity content to extract from:
{memory_items_text}

Suggestion for this category: {suggestion}

=== CRITICAL EXTRACTION REQUIREMENTS ===

**ONLY EXTRACT NEW INFORMATION**
- CAREFULLY review the existing {category} content above
- ONLY extract information that is NOT already present in existing content
- If information is already covered in existing content, DO NOT extract it again
- Focus on completely NEW facts, details, or updates

**NO PRONOUNS - COMPLETE SENTENCES ONLY**
- EVERY memory item must be a complete, standalone sentence
- ALWAYS include the full subject "{character_name}"
- NEVER use pronouns that depend on context (no "she", "he", "they", "it")
- Each memory item should be understandable without reading other items

**CRITICAL: NO "NOT SPECIFIED" OR "NOT MENTIONED" CONTENT**
- NEVER create memory items saying information is "not specified", "not mentioned", "not available", or "unknown"
- ONLY extract and record information that is ACTUALLY present in the source content
- If information is missing, simply DON'T create a memory item for that topic
- Empty/missing information should result in NO memory item, not a "not specified" item

**OUTPUT FORMAT:**
1. Each line should be one complete, self-contained statement
2. NO markdown headers, bullets, or structure
3. Write in plain text only
4. Each line will automatically get a memory ID [xxx] prefix
5. ONLY include lines with actual, factual NEW information
6. If no new information is found, return empty content

Extract ONLY NEW relevant information according to the category requirements above and write each piece as a complete, self-contained sentence:

NEW {category} content to append:"""

        return extract_prompt
