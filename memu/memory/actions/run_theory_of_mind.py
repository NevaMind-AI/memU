from datetime import datetime
from typing import Any, Dict, List

from .base_action import BaseAction
from ...utils import get_logger

logger = get_logger(__name__)


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
                        "description": "Name of the character",
                    },
                    "conversation_text": {
                        "type": "string",
                        "description": "The full conversation text to analyze",
                    },
                    "activity_items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "memory_id": {"type": "string"},
                                "content": {"type": "string"},
                            },
                            "required": ["memory_id", "content"],
                        },
                        "description": "List of new activity items from the conversation",
                    },
                    "session_date": {
                        "type": "string",
                        "description": "Date of the session (e.g., '2024-01-15')",
                        "default": None,
                    },
                    "embeddings_enabled": {
                        "type": "boolean",
                        "description": "Whether to generate embeddings for the theory of mind items",
                        "default": True,
                    },
                },
                "required": ["character_name", "conversation_text", "activity_items"],
            },
        }

    def execute(
        self,
        character_name: str,
        conversation_text: str,
        activity_items: List[Dict[str, str]],
        session_date: str = None,
        embeddings_enabled: bool = True,
    ) -> Dict[str, Any]:
        """
        Analyze the conversation and memory items to extract subtle, obscure, and hidden information behind the conversation.

        Args:
            character_name: Name of the character
            conversation_text: The full conversation text to analyze
            activity_items: List of new memory items from the conversation
            session_date: Date of the session
            embeddings_enabled: Whether to generate embeddings for the theory of mind items

        Returns:
            Dict containing memory items obtained through theory of mind
        """
        try:
            if not conversation_text.strip():
                return self._add_metadata(
                    {"success": False, "error": "Empty conversation text provided"}
                )

            if not activity_items:
                return self._add_metadata(
                    {"success": False, "error": "No memory items provided"}
                )

            if not session_date:
                session_date = datetime.now().strftime("%Y-%m-%d")

            # Call LLM to run theory of mind
            response = self._extract_theory_of_mind_with_llm(
                character_name, conversation_text, activity_items
            )

            if not response.strip():
                return self._add_metadata(
                    {"success": False, "error": "LLM returned empty response"}
                )

            # Parse text response
            reasoning_process, theory_of_mind_items = (
                self._parse_theory_of_mind_from_text(
                    character_name, response.strip(), session_date
                )
            )

            if not theory_of_mind_items:
                return self._add_metadata(
                    {
                        "success": False,
                        "error": "No theory of mind items could be extracted from conversation",
                    }
                )

            return self._add_metadata(
                {
                    "success": True,
                    "character_name": character_name,
                    "theory_of_mind_items_added": len(theory_of_mind_items),
                    "theory_of_mind_items": theory_of_mind_items,
                    "reasoning_process": reasoning_process,
                    "message": f"Successfully extracted {len(theory_of_mind_items)} theory of mind items from conversation",
                }
            )

        except Exception as e:
            return self._handle_error(e)

    def _extract_theory_of_mind_with_llm(
        self,
        character_name: str,
        conversation_text: str,
        activity_items: List[Dict[str, str]],
    ) -> str:
        """Extract theory of mind items from conversation and activity items with LLM"""

        activity_items_text = "\n".join(
            [
                # f"Memory ID: {item['memory_id']}\nContent: {item['content']}"
                f"- {item['content']}"
                for item in activity_items
            ]
        )

        user_name = character_name
            
        theory_of_mind_prompt = f"""You are analyzing the following conversation and activity items for {user_name} to try to infer information that is not explicitly mentioned by {user_name} in the conversation, but he or she might meant to express or the listener can reasonably deduce.

Conversation:
{conversation_text}

Activity Items:
{activity_items_text}

**CRITICAL REQUIREMENT: Inference results must be SELF-CONTAINED MEMORY ITEMS**

Your task it to leverage your reasoning skills to infer the information that is not explicitly mentioned in the conversation, but the character might meant to express or the listener can reasonably deduce.

**SELF-CONTAINED MEMORY REQUIREMENTS:**
- Plain text only, no markdown grammar
- EVERY activity item must be complete and standalone
- ALWAYS include the full subject (do not use "she/he/they/it")
- NEVER use pronouns that depend on context (no "she", "he", "they", "it")
- Include specific names, places, dates, and full context in each item
- Each activity should be understandable without reading other items
- You can use words like "perhaps" or "maybe" to indicate that the information is obtained through reasoning and is not 100% certain
- NO need to include evidences or reasoning processes in the items

**INFERENCE GUIDELINES:**
- Leverage your reasoning skills to infer the information that is not explicitly mentioned
- Use the activity items as a reference to assist your reasoning process and inferences
- DO NOT repeat the information that is already included in the activity items
- Use modal adverbs (perhaps, probably, likely, etc.) to indicate your confidence level of the inference

**COMPLETE SENTENCE EXAMPLES:**
GOOD: "{user_name} may have experience working abroad"
BAD: "Have experience working abroad" (missing subject)
BAD: "He may have experience working abroad" (pronouns as subject)
GOOD: "{user_name} perhaps not enjoy his trip to Europe this summer"
BAD: "{user_name} perhaps not enjoy his trip" (missing location and time)
GOOD: "Harry Potter series are probably important to {user_name}'s childhood"
BAD: "Harry Potter series are probably important to {user_name}'s childhood, because she mentioned it and recommended it to her friends many times" (no need to include evidences or reasoning processes)

**OUTPUT FORMAT:**

**REASONING PROCESS:**
[Your reasoning process for what kind of implicit information can be hidden behind the conversation, what are the evidences, how you get to your conclusion, and how confident you are.]

**INFERENCE ITEMS:**
[One piece of inference per line, no markdown headers, no structure, no numbering, no bullet points, ends with a period]
[After carefully reasoning, if you determine that there is no implicit information that can be inferred from the conversation beyong the explicit information already mentioned in the activity items, you can leave this section empty. DO NOT output things like "No inference available".]

"""

        # Call LLM to run theory of mind
        response = self.llm_client.simple_chat(theory_of_mind_prompt)
        return response

    def _parse_theory_of_mind_from_text(
        self, character_name: str, response_text: str, session_date: str
    ) -> tuple:
        """Parse theory of mind items from text format response"""

        reasoning_process = ""
        theory_of_mind_items = []

        try:
            lines = response_text.split("\n")

            # Parse reasoning process
            reasoning_section = False
            inference_section = False

            for line in lines:
                line = line.strip()

                if (
                    line.upper().startswith("**REASONING PROCESS:")
                    or line.startswith("**")
                    and "REASONING PROCESS" in line.upper()
                ):
                    reasoning_section = True
                    inference_section = False
                    continue
                elif (
                    line.upper().startswith("**INFERENCE ITEMS:")
                    or line.startswith("**")
                    and "INFERENCE ITEMS" in line.upper()
                ):
                    reasoning_section = False
                    inference_section = True
                    continue

                if reasoning_section and line and not line.startswith("**"):
                    if not reasoning_process:
                        reasoning_process = line.strip()
                    else:
                        reasoning_process += "\n" + line.strip()

                # Parse memory items
                elif inference_section:
                    line = line.strip()
                    if line:
                        memory_id = self._generate_memory_id()
                        theory_of_mind_items.append(
                            {
                                "memory_id": memory_id,
                                "mentioned_at": session_date,
                                "content": line,
                                "links": "",
                            }
                        )

        except Exception as e:
            logger.error(f"Failed to parse theory of mind from text: {repr(e)}")

        return reasoning_process, theory_of_mind_items
