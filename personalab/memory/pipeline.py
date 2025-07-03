"""
Memory Update Pipeline

LLM-powered memory analysis and update system for PersonaLab.
This module provides sophisticated memory processing through a three-stage pipeline:
- Modification: Extract and process information from conversations
- Update: Update profile and event memories
- Theory of Mind: Generate psychological insights and behavioral analysis
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..llm import BaseLLMClient
from .base import EventMemory, Memory, ProfileMemory

try:
    from ..config import get_llm_config_manager
except ImportError:
    get_llm_config_manager = None


@dataclass
class UpdateResult:
    """Results from the Update stage of the pipeline"""

    profile: ProfileMemory
    events: EventMemory
    profile_updated: bool
    raw_llm_response: str
    metadata: Dict[str, Any]


@dataclass
class MindResult:
    """Results from the Theory of Mind analysis stage"""

    insights: str  # Mind insights as string
    confidence_score: float
    raw_llm_response: str
    metadata: Dict[str, Any]


@dataclass
class PipelineResult:
    """Complete results from the memory update pipeline"""

    modification_result: str
    update_result: UpdateResult
    mind_result: MindResult
    new_memory: Memory
    pipeline_metadata: Dict[str, Any]


class MemoryUpdatePipeline:
    """
    Memory Update Pipeline for PersonaLab

    LLM-powered pipeline that performs comprehensive memory analysis and updates:
    1. LLM analyzes conversation content and extracts profile updates and events
    2. LLM updates user profiles with intelligent merging
    3. LLM performs Theory of Mind analysis for psychological insights
    """

    def __init__(
        self, llm_client: BaseLLMClient = None, llm_config_manager=None, **llm_config
    ):
        """
        Initialize the memory update pipeline

        Args:
            llm_client: LLM client instance for processing
            llm_config_manager: Unified LLM configuration manager
            **llm_config: Additional LLM configuration parameters
        """
        self.llm_client = llm_client

        # Use unified configuration manager if provided
        if llm_config_manager is not None:
            self.llm_config_manager = llm_config_manager
            self.llm_config = self.llm_config_manager.get_pipeline_config(**llm_config)
        else:
            # Fallback to old behavior for backward compatibility
            if get_llm_config_manager is not None:
                self.llm_config_manager = get_llm_config_manager()
                self.llm_config = self.llm_config_manager.get_pipeline_config(
                    **llm_config
                )
            else:
                # Legacy fallback
                self.llm_config_manager = None
                self.llm_config = {
                    "temperature": 0.3,  # Lower temperature for consistent results
                    "max_tokens": 2000,
                    **llm_config,
                }

    def update_with_pipeline(
        self, previous_memory: Memory, session_conversation: List[Dict[str, str]]
    ) -> Tuple[Memory, PipelineResult]:
        """
        Update memory using the LLM-powered pipeline

        Args:
            previous_memory: Previous Memory object to update
            session_conversation: Current session conversation content

        Returns:
            Tuple[Updated Memory object, Pipeline execution results]
        """
        # 1. LLM Modification stage: Analyze conversation and extract information
        modification_result = self.llm_modification_stage(
            previous_memory, session_conversation
        )

        # 2. LLM Update stage: Update profile and events
        update_result = self.llm_update_stage(previous_memory, modification_result)

        # 3. LLM Theory of Mind stage: Deep psychological analysis
        mind_result = self.llm_theory_of_mind_stage(update_result, session_conversation)

        # 4. Create new Memory object
        new_memory = self._create_updated_memory(
            previous_memory, update_result, mind_result
        )

        # 5. Build pipeline results
        pipeline_result = PipelineResult(
            modification_result=modification_result,
            update_result=update_result,
            mind_result=mind_result,
            new_memory=new_memory,
            pipeline_metadata={
                "execution_time": datetime.now().isoformat(),
                "conversation_length": len(session_conversation),
                "llm_model": getattr(self.llm_client, "model_name", "unknown"),
                "profile_updated": update_result.profile_updated,
            },
        )

        return new_memory, pipeline_result

    def llm_modification_stage(
        self, previous_memory: Memory, session_conversation: List[Dict[str, str]]
    ) -> str:
        """
        LLM Modification stage: Analyze conversation and extract relevant information
        """
        # Build LLM prompt
        conversation_text = self._format_conversation(session_conversation)
        current_profile = previous_memory.get_profile_content()
        current_events = previous_memory.get_event_content()

        prompt = f"""Please analyze the following conversation content and extract user profile updates and important events.

Current User Profile:
{current_profile if current_profile else "None"}

Current Event Records:
{self._format_events(current_events) if current_events else "None"}

Current Conversation Content:
{conversation_text}

Return the updated profile and events suggestion directly in the following format:
profile:
[profile update suggestion]
events:
[event update suggestion]
"""

        # Call LLM
        messages = [{"role": "user", "content": prompt}]

        if self.llm_client is None:
            raise Exception("No LLM client provided")

        response = self.llm_client.chat_completion(messages=messages, **self.llm_config)
        print(response.content)
        if not response.success:
            raise Exception(f"LLM call failed: {response.error}")

        return response.content

    def llm_update_stage(
        self, previous_memory: Memory, modification_result: str
    ) -> UpdateResult:
        """
        LLM Update stage: Update user profile using LLM analysis
        """
        # Parse modification_result to extract profile and events information
        profile_updates, events_updates = self._parse_modification_result(
            modification_result
        )

        # If no profile updates, return directly
        if not profile_updates:
            return UpdateResult(
                profile=ProfileMemory(previous_memory.get_profile_content() or ""),
                events=EventMemory(
                    events=previous_memory.get_event_content().copy(),
                    max_events=previous_memory.event_memory.max_events,
                ),
                profile_updated=False,
                raw_llm_response="No updates needed",
                metadata={
                    "stage": "llm_update",
                    "updated_at": datetime.now().isoformat(),
                    "profile_updated": False,
                },
            )

        current_profile = previous_memory.get_profile_content()
        current_events = previous_memory.get_event_content()
        # Build profile update prompt
        prompt = f"""Please update the user profile based on new information.

Current User Profile:
{current_profile if current_profile else "None"}

Current Event Records:
{self._format_events(current_events) if current_events else "None"}

Update Suggestion:
{modification_result}

Please integrate the new information into the user profile to generate a complete, coherent user profile description.
Requirements:
1. Maintain accuracy of existing information
2. Naturally incorporate new information
3. Avoid duplication and redundancy
4. Use third-person description
5. Keep it concise and clear

Please return the updated complete user profile directly in the following format:
profile:
- Update information 1
- Update information 2
- ...
events:
- Event 1
- Event 2
- ...
"""

        # Call LLM to update profile
        messages = [{"role": "user", "content": prompt}]

        if self.llm_client is None:
            raise Exception("No LLM client provided")

        response = self.llm_client.chat_completion(messages=messages, **self.llm_config)

        if not response.success:
            raise Exception(f"LLM update failed: {response.error}")

        # Parse LLM results and separate profile and events
        updated_profile, updated_events = self._parse_modification_result(
            response.content
        )

        # Create updated EventMemory with the combined event list
        updated_events = EventMemory(
            events=updated_events, max_events=previous_memory.event_memory.max_events
        )

        return UpdateResult(
            profile=ProfileMemory("\n".join(updated_profile)),
            events=updated_events,
            profile_updated=bool(updated_profile),
            raw_llm_response=response.content,
            metadata={
                "stage": "llm_update",
                "updated_at": datetime.now().isoformat(),
                "llm_usage": response.usage,
                "profile_updated": bool(updated_profile),
            },
        )

    def llm_theory_of_mind_stage(
        self, update_result: UpdateResult, session_conversation: List[Dict[str, str]]
    ) -> MindResult:
        """
        LLM Theory of Mind stage: Let LLM perform deep psychological analysis
        """
        conversation_text = self._format_conversation(session_conversation)
        updated_memory_content = (
            update_result.profile.get_content()
            + "\n"
            + "\n".join(update_result.events.get_content())
        )

        prompt = f"""Please conduct a Theory of Mind analysis on the following conversation to deeply understand the user's psychological state and behavioral patterns.

Conversation Content:
{conversation_text}
memory:
{updated_memory_content}

Please analyze the conversation and extract:
1. User's main purposes and motivations
2. User's emotional states and changes
3. User's communication style and engagement patterns
4. User's knowledge level and learning tendencies


Please return the insights directly in the following format:
Insights:
- Insight 1
- Insight 2
- ...
"""

        # Call LLM for Mind analysis
        messages = [{"role": "user", "content": prompt}]

        if self.llm_client is None:
            raise Exception("No LLM client provided")

        response = self.llm_client.chat_completion(messages=messages, **self.llm_config)

        if not response.success:
            raise Exception(f"LLM Mind analysis failed: {response.error}")

        # Store insights directly as string
        insights = response.content

        return MindResult(
            insights=insights,
            confidence_score=0.8,  # Fixed confidence score, can be generated by LLM later
            raw_llm_response=response.content,
            metadata={
                "stage": "llm_theory_of_mind",
                "analyzed_at": datetime.now().isoformat(),
                "llm_usage": response.usage,
            },
        )

    def _create_updated_memory(
        self,
        previous_memory: Memory,
        update_result: UpdateResult,
        mind_result: MindResult,
    ) -> Memory:
        """Create updated Memory object"""
        new_memory = Memory(
            agent_id=previous_memory.agent_id,
            user_id=previous_memory.user_id,
            memory_id=previous_memory.memory_id,
        )

        # Set updated components
        new_memory.profile_memory = update_result.profile
        new_memory.event_memory = update_result.events

        # Set Theory of Mind memory, parse insights text to list
        insights_text = mind_result.insights
        if insights_text:
            # Parse insights text, extract list items
            insights_list = []
            lines = insights_text.strip().split("\n")
            for line in lines:
                line = line.strip()
                if line.startswith("- "):
                    insights_list.append(line[2:].strip())
                elif line and not line.startswith("Insights:"):
                    insights_list.append(line)

            new_memory.update_mind(insights_list)

        # Save original metadata to mind_metadata (backward compatibility)
        new_memory.mind_metadata = {
            "insights": mind_result.insights,
            "confidence_score": mind_result.confidence_score,
            "analysis_metadata": mind_result.metadata,
            "raw_llm_response": mind_result.raw_llm_response,
        }

        return new_memory

    def _parse_modification_result(self, content: str) -> Tuple[List[str], List[str]]:
        """
        Parse LLM returned content, extract profile and events

        Returns:
            Tuple[profile_updates, events_updates]
        """
        profile_updates = []
        events_updates = []

        lines = content.strip().split("\n")
        current_section = None

        for line in lines:
            line = line.strip()
            if line.lower().startswith("profile:"):
                current_section = "profile"
                continue
            elif line.lower().startswith("events:"):
                current_section = "events"
                continue
            elif line.startswith("- ") and current_section:
                item = line[2:].strip()
                if current_section == "profile":
                    profile_updates.append(item)
                elif current_section == "events":
                    events_updates.append(item)

        return profile_updates, events_updates

    def _format_conversation(self, conversation: List[Dict[str, str]]) -> str:
        """Format conversation content"""
        formatted_lines = []
        for msg in conversation:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            formatted_lines.append(f"{role}: {content}")
        return "\n".join(formatted_lines)

    def _format_events(self, events: List[str]) -> str:
        """Format event list"""
        if not events:
            return "None"
        return "\n".join(
            f"- {event}" for event in events[-5:]
        )  # Only show recent 5 events
