"""
Generate Memory Suggestions Action

Analyzes new memory items and suggests what should be added to different memory categories.
"""

from typing import Dict, List, Any
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
                        "description": "Name of the character"
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
                    "available_categories": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of available memory categories"
                    }
                },
                "required": ["character_name", "new_memory_items", "available_categories"]
            }
        }
    
    def execute(
        self,
        character_name: str,
        new_memory_items: List[Dict[str, str]],
        available_categories: List[str]
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
                return self._add_metadata({
                    "success": False,
                    "error": "No memory items provided"
                })
            
            # Convert memory items to text for analysis
            memory_items_text = "\n".join([
                f"Memory ID: {item['memory_id']}\nContent: {item['content']}"
                for item in new_memory_items
            ])
            
            # Create enhanced prompt for LLM to analyze and generate suggestions
            suggestions_prompt = f"""Analyze the following new memory items for {character_name} and suggest what should be added to each memory category.

New Memory Items:
{memory_items_text}

Available Categories: {', '.join(available_categories)}

**CRITICAL REQUIREMENT: Suggestions must lead to SELF-CONTAINED MEMORY ITEMS**

When suggesting content for each category, ensure that the resulting memory items will:
- Be complete, standalone sentences with full subjects
- Always include "{character_name}" instead of pronouns like "she/he/they"
- Include specific names, places, dates, and full context
- Never use "the book", "the place", "the friend" - always specify full titles and names
- Be understandable without reading other memory items

**CATEGORY-SPECIFIC REQUIREMENTS:**

For each category, analyze the new memory items and suggest what specific information should be extracted and added to that category:

- **activity**: Detailed description of the conversation, including the time, place, and people involved
- **profile**: ONLY basic personal information (age, location, occupation, education, family status, demographics) - EXCLUDE events, activities, things they did
- **event**: Specific events, dates, milestones, appointments, meetings, activities with time references  
- **Other categories**: Relevant information for each specific category

**CRITICAL DISTINCTION - Profile vs Activity/Event:**
- ✅ Profile: "Alice lives in San Francisco", "Alice is 28 years old", "Alice works at TechFlow Solutions"
- ❌ Profile: "Alice went hiking" (this is activity), "Alice attended workshop" (this is event)
- ✅ Activity/Event: "Alice went hiking in Blue Ridge Mountains", "Alice attended photography workshop"

**SUGGESTION REQUIREMENTS:**
- Specify that memory items should include "{character_name}" as the subject
- Mention specific names, places, titles, and dates that should be included
- Ensure suggestions lead to complete, self-contained sentences
- Avoid suggesting content that would result in pronouns or incomplete sentences
- For profile: Focus ONLY on stable, factual, demographic information


For each category that has relevant information, provide your suggestions in the following format:

**Category: [category_name]**
- Suggestion: [What specific self-contained content should be added to this category, ensuring full subjects and complete context]

Only suggest categories where there is relevant new information to add/delete/update. Be specific about what content should be extracted and ensure suggestions lead to complete, self-contained memory items.

"""

            # Call LLM to generate suggestions
            response = self.llm_client.simple_chat(suggestions_prompt)
            
            if not response.strip():
                return self._add_metadata({
                    "success": False,
                    "error": "LLM returned empty suggestions"
                })
            
            # Parse text response
            suggestions = self._parse_suggestions_from_text(response.strip(), available_categories, new_memory_items)
            
            return self._add_metadata({
                "success": True,
                "character_name": character_name,
                "suggestions": suggestions,
                "memory_items_count": len(new_memory_items),
                "categories_analyzed": len(available_categories),
                "message": f"Generated self-contained suggestions for {len(suggestions)} categories based on {len(new_memory_items)} memory items"
            })
            
        except Exception as e:
            return self._handle_error(e)
    
    def _parse_suggestions_from_text(self, response_text: str, available_categories: List[str], new_memory_items: List[Dict[str, str]]) -> Dict[str, Dict[str, Any]]:
        """Parse suggestions from text format response"""
        suggestions = {}
        
        try:
            lines = response_text.split('\n')
            current_category = None
            
            for line in lines:
                line = line.strip()
                
                # Look for category headers: **Category: [category_name]**
                if line.startswith('**Category:') and line.endswith('**'):
                    category_name = line.replace('**Category:', '').replace('**', '').strip()
                    if category_name in available_categories:
                        current_category = category_name
                        suggestions[current_category] = {
                            "should_add": True,  # Default to True since category is mentioned
                            "suggestion": "",
                            "relevant_memory_ids": [item["memory_id"] for item in new_memory_items],
                            "priority": "medium"
                        }
                
                # Parse suggestion content: - Suggestion: [content]
                elif current_category and line.startswith('- Suggestion:'):
                    suggestion_text = line.replace('- Suggestion:', '').strip()
                    if suggestion_text:
                        suggestions[current_category]["suggestion"] = suggestion_text
                        suggestions[current_category]["should_add"] = True
            
            # Clean up categories with empty suggestions
            suggestions = {k: v for k, v in suggestions.items() if v["suggestion"].strip()}
            
            # Fallback: if no valid suggestions parsed, create basic ones
            if not suggestions:
                for category in available_categories:
                    suggestions[category] = {
                        "should_add": True,
                        "suggestion": f"Extract relevant {category} information ensuring each memory item starts with the character name and includes full context",
                        "relevant_memory_ids": [item["memory_id"] for item in new_memory_items],
                        "priority": "medium"
                    }
        
        except Exception as e:
            # Fallback: create basic suggestions for all categories
            suggestions = {}
            for category in available_categories:
                suggestions[category] = {
                    "should_add": True,
                    "suggestion": f"Extract relevant {category} information ensuring each memory item is a complete sentence with full subject and specific details",
                    "relevant_memory_ids": [item["memory_id"] for item in new_memory_items],
                    "priority": "medium"
                }
        
        return suggestions 