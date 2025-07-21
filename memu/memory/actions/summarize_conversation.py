"""
Summarize Conversation Action

Analyzes a conversation and extracts multiple distinct memory items.
"""

from typing import Dict, List, Any
from .base_action import BaseAction


class SummarizeConversationAction(BaseAction):
    """
    Summarize conversation content and extract multiple distinct memory items.
    Each memory item should be a focused piece of information that can be processed separately.
    """
    
    @property
    def action_name(self) -> str:
        return "summarize_conversation"
    
    def get_schema(self) -> Dict[str, Any]:
        """Return OpenAI-compatible function schema"""
        return {
            "name": self.action_name,
            "description": "Analyze a conversation and extract multiple distinct memory items, each containing a focused piece of information",
            "parameters": {
                "type": "object",
                "properties": {
                    "conversation_text": {
                        "type": "string",
                        "description": "The full conversation text to analyze"
                    },
                    "character_name": {
                        "type": "string",
                        "description": "Name of the character the conversation is about"
                    },
                    "session_date": {
                        "type": "string",
                        "description": "Date of the conversation session"
                    }
                },
                "required": ["conversation_text", "character_name", "session_date"]
            }
        }
    
    def execute(
        self,
        conversation_text: str,
        character_name: str,
        session_date: str
    ) -> Dict[str, Any]:
        """
        Summarize conversation and extract distinct memory items
        
        Args:
            conversation_text: The full conversation text to analyze
            character_name: Name of the character
            session_date: Date of the conversation session
            
        Returns:
            Dict containing extracted memory items
        """
        try:
            if not conversation_text.strip():
                return self._add_metadata({
                    "success": False,
                    "error": "Empty conversation text provided"
                })
            
            # Create comprehensive prompt for LLM to analyze conversation and extract ALL details
            summary_prompt = f"""Analyze the following conversation for {character_name} and extract ALL possible details comprehensively. 

**CRITICAL REQUIREMENT: CAPTURE EVERY DETAIL - DO NOT OMIT ANYTHING**
**CRITICAL REQUIREMENT: EVERY MEMORY ITEM MUST BE COMPLETE AND SELF-CONTAINED**

Conversation:
{conversation_text}

Character: {character_name}
Session Date: {session_date}

Your task is to exhaustively analyze this conversation and extract EVERY piece of information, no matter how small. This is for a complete activity log that must preserve ALL details.

**SELF-CONTAINED MEMORY REQUIREMENTS:**
- EVERY memory item must be a complete, standalone sentence
- ALWAYS include the full subject (use "{character_name}" instead of "she/he/they")
- NEVER use pronouns that depend on context
- Each memory item should be understandable without reading other items
- Include specific names, places, dates, and full context in each item
- Avoid abbreviations or references that need explanation

**EXTRACTION GUIDELINES:**
1. Extract EVERY fact, opinion, feeling, plan, event, preference, concern, goal, memory, etc.
2. Include ALL names, places, dates, times, books, activities, relationships mentioned
3. Capture emotional context, reactions, and sentiments
4. Record ALL current situations, past experiences, and future plans
5. Document ALL interests, hobbies, work details, personal struggles, achievements
6. Note ALL conversations topics, questions asked, responses given
7. Include ALL specific details like book titles, friend names, locations, activities
8. Record thought processes, realizations, decisions, and considerations
9. Preserve context about why things were mentioned or how they relate
10. Extract both explicit information and implicit insights

**COMPLETE SENTENCE EXAMPLES:**
✅ GOOD: "{character_name} works as a product manager at TechFlow Solutions"
❌ BAD: "Works as a product manager" (missing subject)
✅ GOOD: "{character_name} went hiking with Sarah Johnson in Blue Ridge Mountains"
❌ BAD: "Went hiking with Sarah" (missing location and full name context)
✅ GOOD: "{character_name} read 'The Midnight Library' by Matt Haig and found it inspiring"
❌ BAD: "Found the book inspiring" (missing book title and author)

**OUTPUT FORMAT:**

**COMPREHENSIVE SUMMARY:**
[Detailed paragraph summarizing the ENTIRE conversation, including all topics discussed, emotional context, and key information shared. This should be comprehensive enough that someone could understand the full scope of what was discussed.]

**DETAILED MEMORY ITEMS:**

**Item 1:**
- Memory ID: mem_001
- Content: [{character_name} + complete, specific, self-contained statement with all necessary context and names]
- Type: [personal_info|event|activity|preference|plan|emotion|relationship|work|interest|goal|concern|realization|other]
- Context: [Why this was mentioned or how it connects to other topics]

**Item 2:**
- Memory ID: mem_002  
- Content: [{character_name} + another complete, specific, self-contained statement with full details]
- Type: [personal_info|event|activity|preference|plan|emotion|relationship|work|interest|goal|concern|realization|other]
- Context: [Relationship to conversation flow and other topics]

[Continue extracting EVERY piece of information...]

**COMPREHENSIVE EXTRACTION REQUIREMENTS:**
- Personal Details: Extract ALL personal information, current job, feelings about job, background, relationships
- Events & Activities: Document ALL past events, current activities, weekend activities, specific places visited
- Reading & Media: Include ALL books, titles, authors, opinions, emotional reactions, impacts
- Interests & Hobbies: Capture ALL interests mentioned, past interests, rekindled passions, future plans
- Relationships: Document ALL people mentioned, friends, colleagues, family, their roles
- Emotions & Thoughts: Record ALL feelings, realizations, concerns, motivations, thought processes
- Future Plans: Extract ALL plans, considerations, goals, things being contemplated
- Work & Career: Include ALL job details, career thoughts, professional concerns, work satisfaction
- Learning & Development: Document ALL educational interests, courses considered, skill development
- Specific Details: Include ALL specific names, titles, locations, dates, descriptions

**QUALITY STANDARDS FOR SELF-CONTAINED MEMORY:**
- Each memory item must be a complete sentence with full subject and context
- Include sufficient detail so each item makes sense independently  
- Use specific names, titles, places, and dates in every relevant item
- Never use "he", "she", "they", "it" - always use the person's actual name
- Never use "the book", "the place", "the friend" - always include full titles and names
- Aim for 10-20 comprehensive, self-contained memory items
- Prioritize completeness and independence over brevity
- Never summarize multiple facts into one item - keep them separate but complete

Extract ALL memory items as complete, self-contained statements:"""

            # Call LLM to extract memory items
            response = self.llm_client.simple_chat(summary_prompt)
            
            if not response.strip():
                return self._add_metadata({
                    "success": False,
                    "error": "LLM returned empty response"
                })
            
            # Parse text response
            summary, memory_items = self._parse_summary_from_text(response.strip(), character_name, session_date, conversation_text)
            
            if not memory_items:
                return self._add_metadata({
                    "success": False,
                    "error": "No memory items could be extracted from conversation"
                })
            
            return self._add_metadata({
                "success": True,
                "character_name": character_name,
                "session_date": session_date,
                "memory_items": memory_items,
                "summary": summary,
                "items_count": len(memory_items),
                "message": f"Successfully extracted {len(memory_items)} self-contained memory items from conversation"
            })
            
        except Exception as e:
            return self._handle_error(e)
    
    def _parse_summary_from_text(self, response_text: str, character_name: str, session_date: str, conversation_text: str) -> tuple:
        """Parse summary and memory items from text format response"""
        summary = ""
        memory_items = []
        
        try:
            lines = response_text.split('\n')
            
            # Parse summary and memory items
            summary_section = False
            memory_section = False
            current_item = {}
            
            for line in lines:
                line = line.strip()
                
                # Look for summary section
                if any(marker in line.upper() for marker in ['**COMPREHENSIVE SUMMARY:**', '**SUMMARY:**']):
                    summary_section = True
                    memory_section = False
                    continue
                elif any(marker in line.upper() for marker in ['**DETAILED MEMORY ITEMS:**', '**MEMORY ITEMS:**']):
                    summary_section = False
                    memory_section = True
                    continue
                
                # Parse summary content
                if summary_section and line and not line.startswith('**'):
                    if not summary:  # Take the first substantial line as summary
                        summary = line.strip()
                    else:
                        summary += " " + line.strip()  # Append additional content
                
                # Parse memory items
                elif memory_section:
                    if line.startswith('**Item ') and line.endswith(':**'):
                        # Save previous item if exists
                        if current_item and 'memory_id' in current_item and 'content' in current_item:
                            memory_items.append(current_item)
                        # Start new item
                        current_item = {}
                    
                    elif line.startswith('- Memory ID:'):
                        memory_id = line.replace('- Memory ID:', '').strip()
                        current_item['memory_id'] = memory_id
                    
                    elif line.startswith('- Content:'):
                        content = line.replace('- Content:', '').strip()
                        current_item['content'] = content
                    
                    elif line.startswith('- Type:'):
                        item_type = line.replace('- Type:', '').strip()
                        current_item['type'] = item_type
                    
                    elif line.startswith('- Context:'):
                        context = line.replace('- Context:', '').strip()
                        current_item['context'] = context
            
            # Add last item
            if current_item and 'memory_id' in current_item and 'content' in current_item:
                memory_items.append(current_item)
            
            # Enhanced fallback if parsing failed - create comprehensive, self-contained memory items
            if not summary:
                summary = f"Comprehensive conversation session with {character_name} on {session_date} covering multiple topics and detailed information exchange"
            
            if not memory_items:
                # Create detailed, self-contained memory items from conversation lines
                conv_lines = conversation_text.split('\n')
                item_id = 1
                
                for line in conv_lines:
                    line = line.strip()
                    if line and any(role in line for role in ['User:', 'user:', 'USER:', character_name + ':', 'Assistant:', 'assistant:', 'ASSISTANT:']):
                        # Extract role and content
                        if ':' in line:
                            role_part, content_part = line.split(':', 1)
                            content_part = content_part.strip()
                            
                            if len(content_part) > 15:  # Only include substantial content
                                # Make content self-contained with proper subject
                                if role_part.strip().lower() in ['user', 'assistant'] or character_name.lower() in role_part.lower():
                                    if character_name.lower() in role_part.lower():
                                        complete_content = f"{character_name} said: {content_part}"
                                    else:
                                        complete_content = f"User said to {character_name}: {content_part}"
                                else:
                                    complete_content = f"{role_part.strip()} said: {content_part}"
                                
                                memory_items.append({
                                    "memory_id": f"mem_{item_id:03d}",
                                    "content": complete_content,
                                    "type": "conversation",
                                    "context": f"Part of conversation exchange on {session_date}"
                                })
                                item_id += 1
        
        except Exception as e:
            # Enhanced fallback: create comprehensive, self-contained basic memory items
            summary = f"Detailed conversation session with {character_name} on {session_date} - comprehensive activity record"
            lines = conversation_text.split('\n')
            memory_items = []
            item_id = 1
            
            for line in lines:
                line = line.strip()
                if line and len(line) > 10:  # Include all substantial content
                    # Make each line self-contained with proper subject
                    if character_name.lower() in line.lower():
                        complete_content = f"{character_name} participated in conversation: {line}"
                    else:
                        complete_content = f"In conversation with {character_name}: {line}"
                    
                    memory_items.append({
                        "memory_id": f"mem_{item_id:03d}",
                        "content": complete_content,
                        "type": "conversation_detail",
                        "context": f"Conversation content from session {session_date}"
                    })
                    item_id += 1
        
        return summary, memory_items 