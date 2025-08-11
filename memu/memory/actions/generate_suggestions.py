"""
Generate Memory Suggestions Action

Analyzes new memory items and suggests what should be added to different memory categories.
"""

from typing import Any, Dict, Optional

from .base_action import BaseAction


class GenerateMemorySuggestionsAction(BaseAction):
    """
    Generate suggestions for what memory content should be added to different categories
    based on new memory items from conversations.
    """

    @property
    def action_name(self) -> str:
        return "generate_memory_suggestions"

    def get_schema(self) -> Dict[str, Any]:
        """Return OpenAI-compatible function schema"""
        return {
            "name": self.action_name,
            "description": "Analyze new memory items and generate suggestions for what should be added to different memory categories",
            "parameters": {
                "type": "object",
                "properties": {
                    "character_name": {
                        "type": "string",
                        "description": "Name of the character",
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
                            "required": ["memory_id", "content"],
                        },
                        "description": "List of new memory items from the conversation",
                    },
                },
                "required": ["character_name", "new_memory_items"],
            },
        }

    def execute(
        self,
        character_name: str,
        new_memory_items: list[dict[str, str]],
        available_categories: Optional[list[str]] = None,
    ) -> Dict[str, Any]:
        """
        Generate memory suggestions for different categories

        Args:
            character_name: Name of the character
            new_memory_items: List of new memory items with memory_id and content
            available_categories: List of available memory categories

        Returns:
            Dict containing suggestions for each category
        """
        try:
            if not new_memory_items:
                return self._add_metadata(
                    {"success": False, "error": "No memory items provided"}
                )

            if available_categories is None:
                available_categories = self._get_available_categories(character_name)
            if not available_categories:
                return self._add_metadata(
                    {"success": False, "error": "No available categories found"}
                )

            # Convert memory items to text for analysis
            memory_items_text = "\n".join(
                [
                    # f"Memory ID: {item['memory_id']}\nContent: {item['content']}"
                    f"- {item['content']}"
                    for item in new_memory_items
                ]
            )

            # Create enhanced prompt for LLM to analyze and generate suggestions
            suggestions_prompt = f"""You are an expert in analyzing the provided memory items for {character_name} and suggesting the memory items that should be added to each memory category.

New Memory Items:
{memory_items_text}

Available Categories: {', '.join(available_categories)}

**CRITICAL REQUIREMENT: Suggestions must be SELF-CONTAINED MEMORY ITEMS**

**SELF-CONTAINED MEMORY REQUIREMENTS:**
- EVERY activity item must be complete and standalone
- ALWAYS include the full subject (do not use "she/he/they/it")
- NEVER use pronouns that depend on context (no "she", "he", "they", "it")
- Include specific names, places, dates, and full context in each item
- Each activity should be understandable without reading other items
- Include all relevant details, emotions, and outcomes in the activity description

**CATEGORY-SPECIFIC REQUIREMENTS:**

For each category, analyze the new memory items and suggest what specific information should be extracted and added to that category:

- **activity**: Detailed description of the conversation, including the time, place, and people involved
- **profile**: ONLY basic personal information (age, location, occupation, education, family status, demographics) - EXCLUDE events, activities, things they did
- **event**: Specific events, dates, milestones, appointments, meetings, activities with time references
- **Other categories**: Relevant information for each specific category

**CRITICAL DISTINCTION - Profile vs Activity/Event:**
- Profile (GOOD): "Alice lives in San Francisco", "Alice is 28 years old", "Alice works at TechFlow Solutions"
- Profile (BAD): "Alice went hiking" (this is activity), "Alice attended workshop" (this is event)
- Activity/Event (GOOD): "Alice went hiking in Blue Ridge Mountains", "Alice attended photography workshop"

**SUGGESTION REQUIREMENTS:**
- Specify that memory items should include "{character_name}" as the subject
- Mention specific names, places, titles, and dates that should be included
- Ensure suggestions lead to complete, self-contained memory items
- Avoid suggesting content that would result in pronouns or incomplete sentences
- For profile: Focus ONLY on stable, factual, demographic information
- If one input memory item involves information belongs to multiple categories, you should reasonable seperete the information and provide suggestions to all involved categories
- **IMPORTANT** If the input memory item use modal adverbs (perhaps, probably, likely, etc.) to indicate an uncertain inference, keep the modal adverbs as-is in your suggestions

**OUTPUT INSTRUCTIONS:**
- **IMPORTANT** NEVER suggest categories that are not in the Available Categories
- Only output categories where there are suggestions for new memory items

**OUTPUT FORMAT:**

**Category: [category_name]**
- Suggestion: [What specific self-contained content should be added to this category, ensuring full subjects and complete context]
- Suggestion: [What specific self-contained content should be added to this category, ensuring full subjects and complete context]

**Category: [category_name]**
- Suggestion: [What specific self-contained content should be added to this category, ensuring full subjects and complete context]

... other categories ...
"""

            # Call LLM to generate suggestions
            response = self.llm_client.simple_chat(suggestions_prompt)

            if not response.strip():
                return self._add_metadata(
                    {"success": False, "error": "LLM returned empty suggestions"}
                )

            # Parse text response
            suggestions = self._parse_suggestions_from_text(
                response.strip(), available_categories, new_memory_items
            )

            return self._add_metadata(
                {
                    "success": True,
                    "character_name": character_name,
                    "suggestions": suggestions,
                    "categories_analyzed": available_categories,
                    "message": f"Generated self-contained suggestions for {len(suggestions)} categories based on {len(new_memory_items)} memory items",
                }
            )

        except Exception as e:
            return self._handle_error(e)

    def _get_available_categories(self, character_name: str) -> list[str]:
        """Get available categories for a character"""
        return [category for category in self.basic_memory_types.keys() if category != "activity"]

    def _parse_suggestions_from_text(
        self,
        response_text: str,
        available_categories: list[str],
        new_memory_items: list[dict[str, str]],
    ) -> Dict[str, Dict[str, Any]]:
        """Parse suggestions from text format response"""
        suggestions = {}

        try:
            lines = response_text.split("\n")
            current_category = None

            for line in lines:
                line = line.strip()

                if line.startswith("**Category:") and line.endswith("**"):
                    category_name = (
                        line.replace("**Category:", "").replace("**", "").strip()
                    )
                    if category_name in available_categories:
                        current_category = category_name
                        suggestions[current_category] = ""
                elif current_category and line.startswith("- Suggestion:"):
                    suggestion_text = line.replace("- Suggestion:", "").strip()
                    suggestions[current_category] += f"{suggestion_text}\n"

            suggestions = {k: v for k, v in suggestions.items() if v.strip()}
        except Exception:
            raise
        return suggestions
