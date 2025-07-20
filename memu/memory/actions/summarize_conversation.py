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
            
            # Create prompt for LLM to analyze conversation and extract memory items
            summary_prompt = f"""Analyze the following conversation for {character_name} and extract distinct memory items.

Conversation:
{conversation_text}

Character: {character_name}
Session Date: {session_date}

Your task is to:
1. Break down the conversation into multiple distinct memory items
2. Each memory item should contain one focused piece of information
3. Extract personal details, events, activities, preferences, plans, etc.
4. Make each item self-contained and meaningful

Return your analysis in the following format:

**SUMMARY:**
[Brief overall summary of the conversation]

**MEMORY ITEMS:**

**Item 1:**
- Memory ID: mem_001
- Content: [Simple, clear statement - one fact per item]
- Type: [personal_info|event|activity|preference|plan|other]

**Item 2:**
- Memory ID: mem_002  
- Content: [Another clear statement - avoid complex formatting]
- Type: [personal_info|event|activity|preference|plan|other]

[Continue for all memory items...]

Guidelines:
- Each memory item should be one clear, simple statement
- Avoid complex descriptions, use plain language
- Generate unique memory_ids (like "mem_001", "mem_002", etc.)
- Focus on factual information
- Aim for 3-8 memory items depending on conversation richness

Extract memory items:"""

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
                "message": f"Successfully extracted {len(memory_items)} memory items from conversation"
            })
            
        except Exception as e:
            return self._handle_error(e)
    
    def _parse_summary_from_text(self, response_text: str, character_name: str, session_date: str, conversation_text: str) -> tuple:
        """Parse summary and memory items from text format response"""
        summary = ""
        memory_items = []
        
        try:
            lines = response_text.split('\n')
            
            # Parse summary
            summary_section = False
            memory_section = False
            current_item = {}
            
            for line in lines:
                line = line.strip()
                
                # Look for summary section
                if line.upper().startswith('**SUMMARY:**'):
                    summary_section = True
                    memory_section = False
                    continue
                elif line.upper().startswith('**MEMORY ITEMS:**'):
                    summary_section = False
                    memory_section = True
                    continue
                
                # Parse summary content
                if summary_section and line and not line.startswith('**'):
                    summary = line.strip()
                
                # Parse memory items
                elif memory_section:
                    if line.startswith('**Item ') and line.endswith(':**'):
                        # Save previous item if exists
                        if current_item and 'memory_id' in current_item:
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
            
            # Add last item
            if current_item and 'memory_id' in current_item:
                memory_items.append(current_item)
            
            # Fallback if parsing failed
            if not summary:
                summary = f"Conversation session with {character_name} on {session_date}"
            
            if not memory_items:
                # Create basic memory items from conversation
                conv_lines = conversation_text.split('\n')
                item_id = 1
                
                for line in conv_lines:
                    if line.strip() and any(role in line.upper() for role in ['USER:', 'ASSISTANT:']):
                        content = line.strip()
                        if len(content) > 20:  # Only include substantial content
                            memory_items.append({
                                "memory_id": f"mem_{item_id:03d}",
                                "content": content,
                                "type": "activity"
                            })
                            item_id += 1
        
        except Exception:
            # Fallback: create basic memory items
            summary = f"Conversation session with {character_name} on {session_date}"
            lines = conversation_text.split('\n')
            memory_items = []
            item_id = 1
            
            for line in lines:
                if line.strip() and any(role in line.upper() for role in ['USER:', 'ASSISTANT:']):
                    content = line.strip()
                    if len(content) > 20:
                        memory_items.append({
                            "memory_id": f"mem_{item_id:03d}",
                            "content": content,
                            "type": "activity"
                        })
                        item_id += 1
        
        return summary, memory_items 