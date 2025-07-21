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
- Include specific names, places, dates, and full context
- Never use "the book", "the place", "the friend" - always specify full titles and names
- Be understandable without reading other memory items

For each category, analyze the new memory items and suggest what specific information should be extracted and added to that category. Consider:

- profile: Personal information, traits, characteristics, background, skills, preferences
- event: Specific events, dates, milestones, appointments, meetings, activities with time references  
- activity: General activities, conversations, interactions, daily activities
- interests: Hobbies, interests, passions, things they enjoy or dislike
- study: Learning activities, courses, education, skill development
- Other categories: Relevant information for each specific category

**SUGGESTION REQUIREMENTS:**
- Specify that memory items should include "{character_name}" as the subject
- Mention specific names, places, titles, and dates that should be included
- Ensure suggestions lead to complete, self-contained sentences
- Avoid suggesting content that would result in pronouns or incomplete sentences

For each category that has relevant information, provide your suggestions in the following format:

**Category: [category_name]**
- Should add: [yes/no]
- Suggestion: [What specific self-contained content should be added to this category, ensuring full subjects and complete context]
- Priority: [high/medium/low]

Only suggest categories where there is relevant new information to add. Be specific about what content should be extracted and ensure suggestions lead to complete, self-contained memory items.

Example of good suggestion:
"Add information about {character_name}'s hiking activities including the specific location Blue Ridge Mountains, companion Sarah Johnson, and the waterfall called Crystal Falls that {character_name} discovered"

Example of bad suggestion:
"Add information about hiking activities" (too vague, doesn't specify subjects or context)
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
                
                # Look for category headers
                if line.startswith('**Category:') and line.endswith('**'):
                    category_name = line.replace('**Category:', '').replace('**', '').strip()
                    if category_name in available_categories:
                        current_category = category_name
                        suggestions[current_category] = {
                            "should_add": False,
                            "suggestion": "",
                            "relevant_memory_ids": [item["memory_id"] for item in new_memory_items],
                            "priority": "medium"
                        }
                
                # Parse suggestion details
                elif current_category and line.startswith('- '):
                    if line.startswith('- Should add:'):
                        should_add_text = line.replace('- Should add:', '').strip().lower()
                        suggestions[current_category]["should_add"] = should_add_text in ['yes', 'true']
                    
                    elif line.startswith('- Suggestion:'):
                        suggestion_text = line.replace('- Suggestion:', '').strip()
                        suggestions[current_category]["suggestion"] = suggestion_text
                    
                    elif line.startswith('- Priority:'):
                        priority_text = line.replace('- Priority:', '').strip().lower()
                        if priority_text in ['high', 'medium', 'low']:
                            suggestions[current_category]["priority"] = priority_text
            
            # Fallback: if no suggestions parsed, create basic ones with self-contained guidance
            if not suggestions:
                for category in available_categories:
                    suggestions[category] = {
                        "should_add": True,
                        "suggestion": f"Extract relevant {category} information ensuring each memory item starts with the character name and includes full context",
                        "relevant_memory_ids": [item["memory_id"] for item in new_memory_items],
                        "priority": "medium"
                    }
        
        except Exception:
            # Fallback: create basic suggestions with self-contained guidance for all categories
            suggestions = {}
            for category in available_categories:
                suggestions[category] = {
                    "should_add": True,
                    "suggestion": f"Extract relevant {category} information ensuring each memory item is a complete sentence with full subject and specific details",
                    "relevant_memory_ids": [item["memory_id"] for item in new_memory_items],
                    "priority": "medium"
                }
        
        return suggestions 