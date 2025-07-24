

from typing import Dict, Any, List
from datetime import datetime

from .base_action import BaseAction

class RunTheoryOfMindAction(BaseAction):
    """
    Run theory of mind on the conversation to infer subtle, obscure, and hidden information behind the conversation.
    This is a very important step to understand the characters and the conversation.
    The output should follow the same format as memory items.
    """

    @property
    def action_name(self) -> str:
        return "run_theory_of_mind"
    
    def get_schema(self) -> Dict[str, Any]:
        """Return OpenAI-compatible function schema"""
        return {
            "name": self.action_name,
            "description": "Analyze the conversation and memory items to extract subtle, obscure, and hidden information behind the conversation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "character_name": {
                        "type": "string",
                        "description": "Name of the character"
                    },
                    "conversation_text": {
                        "type": "string",
                        "description": "The full conversation text to analyze"
                    },
                    "memory_items": {
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
                },
                "required": ["character_name", "conversation_text", "memory_items"]
            }
        }

    def execute(
        self,
        character_name: str,
        conversation_text: str,
        memory_items: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Analyze the conversation and memory items to extract subtle, obscure, and hidden information behind the conversation.

        Args:
            character_name: Name of the character
            conversation_text: The full conversation text to analyze
            memory_items: List of new memory items from the conversation

        Returns:
            Dict containing memory items obtained through theory of mind
        """
        try:
            if not conversation_text.strip():
                return self._add_metadata({
                    "success": False,
                    "error": "Empty conversation text provided"
                })
            
            if not memory_items:
                return self._add_metadata({
                    "success": False,
                    "error": "No memory items provided"
                })
            
            # Create comprehensive prompt for LLM to analyze conversation and extract ALL details
            theory_of_mind_prompt = f"""Analyze the following conversation and memory items for {character_name} and try to infer information that is not explicitly mentioned in the conversation, but the character might meant to express or the listener can reasonably deduce.

Conversation:
{conversation_text}

Memory Items:
{memory_items}

**CRITICAL REQUIREMENT: Inference results must be SELF-CONTAINED MEMORY ITEMS**

Your task it to leverage your reasoning skills to infer the information that is not explicitly mentioned in the conversation, but the character might meant to express or the listener can reasonably deduce.

**SELF-CONTAINED MEMORY REQUIREMENTS:**
- EVERY memory item must be a complete, standalone sentence
- ALWAYS include the full subject (use "{character_name}" instead of "she/he/they")
- NEVER use pronouns that depend on context
- Each memory item should be understandable without reading other items
- Include specific names, places, dates, and full context in each item
- Avoid abbreviations or references that need explanation
- You can use words like "perhaps" or "maybe" to indicate that the information is obtained through reasoning and is not 100% certain

**EXTRACTION GUIDELINES:**
1. Make use of the reasoning skills to infer the information that is not explicitly mentioned
2. Use the memory items as a reference to help your reasoning process and inferences
3. DO NOT repeat the information that is already included in the memory items
4. Use modal Adverbs (perhaps, probably, likely, etc.) to indicate your confidence level of the inference

**COMPLETE SENTENCE EXAMPLES:**
✅ GOOD: "{character_name} perhaps has experience working abroad"
❌ BAD: "Have experience working abroad" (missing subject)
✅ GOOD: "{character_name} may not enjoy his trip to Europe this summer"
❌ BAD: "{character_name} may not enjoy his trip" (missing location and time)
✅ GOOD: "Harry Potter series are probably important to {character_name}'s childhood"
❌ BAD: "Harry Potter series are probably important to {character_name}'s childhood, because she mentioned it and recommended it to her friends many times" (no need to include verbose evidences or reasoning processes)

**OUTPUT FORMAT:**

**REASONING PROCESS:**
[Your reasoning process for what kind of implicit information can be hidden behind the conversation, what are the convidence, how you get to your conclusion, and your confidence level.]

**DETAILED MEMORY ITEMS:**
[If you insist there is no implicit information that can be inferred from the conversation beyong the explicit memory items after careful reasoning, you can leave this section empty]

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

[Continue summarizing memory items you resaonably infered...]
"""

            # Call LLM to run theory of mind
            response = self.llm_client.simple_chat(theory_of_mind_prompt)
            
            if not response.strip():
                return self._add_metadata({
                    "success": False,
                    "error": "LLM returned empty response"
                })
            
            # Parse text response
            reasoning_process, theory_of_mind_items = self._parse_theory_of_mind_from_text(response.strip(), character_name, conversation_text, memory_items)

            if not theory_of_mind_items:
                return self._add_metadata({
                    "success": False,
                    "error": "No theory of mind items could be extracted from conversation"
                })
            
            return self._add_metadata({
                "success": True,
                "character_name": character_name,
                "theory_of_mind_items": theory_of_mind_items,
                "memory_items_count": len(theory_of_mind_items),
                "reasoning_process": reasoning_process,
                "message": f"Successfully extracted {len(theory_of_mind_items)} self-contained theory of mind items from conversation"
            })
            
        except Exception as e:
            return self._handle_error(e)
    
    def _parse_theory_of_mind_from_text(self, response_text: str, character_name: str, conversation_text: str, memory_items: List[Dict[str, str]]) -> tuple:
        """Parse theory of mind items from text format response"""
        reasoning_process = ""
        theory_of_mind_items = []
        
        try:
            lines = response_text.split('\n')
            
            # Parse reasoning process
            reasoning_section = False
            memory_section = False
            current_item = {}
            
            for line in lines:
                line = line.strip()
                
                # Look for summary section
                if any(marker in line.upper() for marker in ['**REASONING PROCESS:**', '**REASONING:**']):
                    reasoning_section = True
                    memory_section = False
                    continue
                elif any(marker in line.upper() for marker in ['**DETAILED MEMORY ITEMS:**', '**MEMORY ITEMS:**']):
                    reasoning_section = False
                    memory_section = True
                    continue

                if reasoning_section and line and not line.startswith('**'):
                    if not reasoning_process:
                        reasoning_process = line.strip()
                    else:
                        reasoning_process += " " + line.strip()

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
                        current_item['content'] = f"[ToM] {content}"
                        dump_debug(f"[ToM] {content}")
                    
                    elif line.startswith('- Type:'):
                        item_type = line.replace('- Type:', '').strip()
                        current_item['type'] = item_type
                    
                    elif line.startswith('- Context:'):
                        context = line.replace('- Context:', '').strip() 
                        current_item['context'] = context

            # Add last item
            if current_item and 'memory_id' in current_item and 'content' in current_item:
                theory_of_mind_items.append(current_item)
            
            # Enhanced fallback if parsing failed - create comprehensive, self-contained memory items
            if not reasoning_process:
                reasoning_process = f"With Theory of Mind reasoning, we deduce these reasonable inferences from the conversation session with {character_name}"
            
        except Exception as e:
            import traceback
            print(repr(e))
            traceback.print_exc()
        
        return reasoning_process, theory_of_mind_items

def dump_debug(string: str):
    with open("debug/tom_debug.txt", "a") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] {string}\n")