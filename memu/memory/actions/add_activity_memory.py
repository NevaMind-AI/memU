"""
Add Activity Memory Action

Adds new activity memory content with strict no-pronouns formatting, following the same
high-quality standards as update_memory_with_suggestions for self-contained memory items.
"""

import json
import re
from datetime import datetime
from typing import Any, Dict

from ...utils import get_logger
from .base_action import BaseAction

logger = get_logger(__name__)


class AddActivityMemoryAction(BaseAction):
    """
    Action to add new activity memory content with strict formatting requirements

    Ensures all memory items are complete, self-contained sentences with no pronouns,
    following the same standards as update_memory_with_suggestions.
    """

    @property
    def action_name(self) -> str:
        return "add_activity_memory"

    def get_schema(self) -> Dict[str, Any]:
        """Return OpenAI-compatible function schema"""
        return {
            "name": "add_activity_memory",
            "description": "Add new activity memory content with strict no-pronouns formatting for complete, self-contained memory items",
            "parameters": {
                "type": "object",
                "properties": {
                    "character_name": {
                        "type": "string",
                        "description": "Name of the character",
                    },
                    "content": {
                        "type": "string",
                        "description": "Complete original conversation text exactly as provided - do NOT modify, extract, or summarize",
                    },
                    "session_date": {
                        "type": "string",
                        "description": "Date of the session (e.g., '2024-01-15')",
                        "default": None,
                    },
                    "generate_embeddings": {
                        "type": "boolean",
                        "description": "Whether to generate embeddings for semantic search",
                        "default": True,
                    },
                },
                "required": ["character_name", "content"],
            },
        }

    def execute(
        self,
        character_name: str,
        content: str,
        session_date: str = None,
        generate_embeddings: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute add activity memory operation with strict formatting

        Args:
            character_name: Name of the character
            content: Raw content to process and format
            session_date: Date of the session
            generate_embeddings: Whether to generate embeddings for the content

        Returns:
            Dict containing operation result including formatted content and embedding info
        """
        try:
            # Use current date if not provided
            if not session_date:
                session_date = datetime.now().strftime("%Y-%m-%d")

            # Process raw content through LLM to ensure strict formatting
            formatted_content = self._format_content_with_llm(
                character_name, content, session_date
            )

            if not formatted_content.strip():
                return self._add_metadata(
                    {"success": False, "error": "LLM returned empty formatted content"}
                )

            # Add memory IDs with timestamp to the formatted content
            memory_items, content_with_ids = self._add_memory_ids_with_timestamp(
                formatted_content, session_date
            )

            # Save first, then add embedding for just the new content
            success = self._append_memory_content(
                character_name, "activity", content_with_ids
            )

            # Save content with embeddings if enabled
            if success and generate_embeddings and self.embeddings_enabled:
                self._add_memory_item_embedding(
                    character_name, "activity", memory_items
                )

            if success:
                return self._add_metadata(
                    {
                        "success": True,
                        "character_name": character_name,
                        "category": "activity",
                        "session_date": session_date,
                        "memory_items_added": len(memory_items),
                        "memory_items": memory_items,
                        "message": f"Successfully generated {len(memory_items)} self-contained activity memory items for {character_name}",
                    }
                )
            else:
                return self._add_metadata(
                    {"success": False, "error": "Failed to save activity memory"}
                )

        except Exception as e:
            return self._handle_error(e)

    def _format_content_with_llm(
        self, character_name: str, content: str, session_date: str
    ) -> str:
        """Use LLM to format content with meaningful activity grouping"""

        user_name = character_name
            
        # Create enhanced prompt for meaningful activity grouping
        format_prompt = f"""You are formatting activity memory content for {user_name} on {session_date}.

Raw content to format:
{content}

**CRITICAL REQUIREMENT: GROUP RELATED CONTENT INTO MEANINGFUL ACTIVITIES**

Transform this raw content into properly formatted activity memory items following these rules:

**MEANINGFUL ACTIVITY GROUPING REQUIREMENTS:**
- Group related sentences/statements into single, comprehensive activity descriptions
- Each activity should be a complete, self-contained description of what happened
- Combine related dialogue, actions, and context into cohesive activity blocks
- Only create separate items for genuinely different activities or topics
- Each activity item should tell a complete "story" or "event"

**SELF-CONTAINED MEMORY REQUIREMENTS:**
- EVERY activity item must be complete and standalone
- ALWAYS include the full subject (do not use "she/he/they/it")
- NEVER use pronouns that depend on context (no "she", "he", "they", "it")
- Include specific names, places, dates, and full context in each item
- Each activity should be understandable without reading other items
- Include all relevant details, emotions, and outcomes in the activity description

**FORMAT REQUIREMENTS:**
1. Each line = one complete, meaningful activity (may include multiple related sentences)
2. NO markdown headers, bullets, numbers, or structure
3. Write in plain text only
4. Focus on comprehensive, meaningful activity descriptions
5. Use specific names, titles, places, and dates
6. Each line ends with a period

**GOOD EXAMPLES (meaningful activities, one per line):**
{character_name} attended a LGBTQ support group where {character_name} heard inspiring transgender stories and felt happy, thankful, accepted, and gained courage to embrace {character_name}'s true self.
{character_name} discussed future career plans with Melanie, expressing keen interest in counseling and mental health work to support people with similar issues, and Melanie encouraged {character_name} saying {character_name} would be a great counselor due to {character_name}'s empathy and understanding.
{character_name} admired Melanie's lake sunrise painting from last year, complimented the color blending, and discussed how painting serves as a great outlet for expressing feelings and relaxing after long days.

**BAD EXAMPLES (too fragmented):**
{character_name} went to a LGBTQ support group.
{character_name} heard transgender stories.
{character_name} felt happy and thankful.
{character_name} gained courage to embrace {character_name}'s true self.

**ACTIVITY GROUPING GUIDELINES:**
- Conversations about the same topic → Single activity
- Related actions and their outcomes → Single activity
- Emotional reactions to specific events → Include in the main activity
- Sequential related events → Single comprehensive activity
- Different topics or unrelated events → Separate activities

**QUALITY STANDARDS:**
- Never use "he", "she", "they", "it" - always use the person's actual name
- Never use "the book", "the place", "the friend" - always include full titles and names
- Each activity must be complete and tell the full story
- Include emotional context, outcomes, and significance
- Merge related content intelligently to create meaningful activity summaries

Transform the raw content into properly formatted activity memory items (ONE MEANINGFUL ACTIVITY PER LINE):

"""

        # Call LLM to format content
        cleaned_content = self.llm_client.simple_chat(format_prompt)

        return cleaned_content

    def _add_memory_ids_with_timestamp(
        self, content: str, session_date: str
    ) -> tuple[list[dict], str]:
        """
        Add memory IDs with timestamp to content lines
        Format: [memory_id][mentioned at {session_date}] {content}

        Args:
            content: Raw content
            session_date: Date of the session

        Returns:
            Content with memory IDs and timestamps added to each line
        """
        if not content.strip():
            return content

        lines = content.split("\n")
        processed_items = []
        plain_memory_lines = []

        for line in lines:
            line = line.strip()
            if line:  # Only process non-empty lines
                # Generate new unique memory ID for this line
                memory_id = self._generate_memory_id()
                # Format: [memory_id][mentioned at {session_date}] {content} [links]
                processed_items.append(
                    {
                        "memory_id": memory_id,
                        "mentioned_at": session_date,
                        "content": line,
                        "links": "",
                    }
                )
                plain_memory_lines.append(
                    f"[{memory_id}][mentioned at {session_date}] {line} []"
                )

        plain_memory_text = "\n".join(plain_memory_lines)

        return processed_items, plain_memory_text

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
