"""
Memory Update Pipeline

LLM-powered memory analysis and update system for PersonaLab.
This module provides sophisticated memory processing through a three-stage pipeline:
- Modification: Extract and process information from conversations
- Update: Update profile and event memories
- Theory of Mind: Generate psychological insights and behavioral analysis
"""

import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..llm import BaseLLMClient
from ..utils import get_logger
from .base import EventMemory, Memory, ProfileMemory

try:
    from ..config import get_llm_config_manager
except ImportError:
    get_llm_config_manager = None

logger = get_logger(__name__)


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
            # Only use basic config - api_key and model
            basic_config = self.llm_config_manager.get_provider_config()
            self.llm_config = {k: v for k, v in basic_config.items() if k in ['api_key', 'model']}
            logger.info(f"[PIPELINE] Initialized with provided config manager, model: {self.llm_config.get('model', 'unknown')}")
        else:
            # Fallback to old behavior for backward compatibility
            if get_llm_config_manager is not None:
                self.llm_config_manager = get_llm_config_manager()
                basic_config = self.llm_config_manager.get_provider_config()
                self.llm_config = {k: v for k, v in basic_config.items() if k in ['api_key', 'model']}
                logger.info(f"[PIPELINE] Initialized with fallback config manager, model: {self.llm_config.get('model', 'unknown')}")
            else:
                # Legacy fallback
                self.llm_config_manager = None
                self.llm_config = {}
                logger.warning("[PIPELINE] Initialized without config manager - using legacy fallback")
        
        logger.info(f"[PIPELINE] MemoryUpdatePipeline initialized with LLM client: {type(self.llm_client).__name__ if self.llm_client else 'None'}")


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
        pipeline_start_time = time.time()
        logger.info(f"[PIPELINE] Starting memory update pipeline for agent_id={previous_memory.agent_id}, user_id={previous_memory.user_id}")
        logger.debug(f"[PIPELINE] Processing {len(session_conversation)} conversation messages")
        
        # Log current memory state
        current_profile = previous_memory.get_profile_content()
        current_events = previous_memory.get_event_content()
        current_mind = previous_memory.get_mind_content()
        logger.debug(f"[PIPELINE] Current memory state: profile_items={len(current_profile)}, events={len(current_events)}, mind_insights={len(current_mind)}")
        
        # 1. LLM Modification stage: Analyze conversation and extract information
        stage1_start = time.time()
        logger.debug("[PIPELINE] Stage 1: Running LLM Modification stage...")
        modification_result = self.llm_modification_stage(
            previous_memory, session_conversation
        )
        stage1_time = time.time() - stage1_start
        logger.debug(f"[PIPELINE] Stage 1 completed in {stage1_time:.3f}s: extracted {len(modification_result)} chars of analysis")

        # 2. LLM Update stage: Update profile and events
        stage2_start = time.time()
        logger.debug("[PIPELINE] Stage 2: Running LLM Update stage...")
        update_result = self.llm_update_stage(previous_memory, modification_result)
        stage2_time = time.time() - stage2_start
        logger.debug(f"[PIPELINE] Stage 2 completed in {stage2_time:.3f}s: profile_updated={update_result.profile_updated}")

        # 3. LLM Theory of Mind stage: Deep psychological analysis
        stage3_start = time.time()
        logger.debug("[PIPELINE] Stage 3: Running LLM Theory of Mind stage...")
        mind_result = self.llm_theory_of_mind_stage(update_result, session_conversation)
        stage3_time = time.time() - stage3_start
        logger.debug(f"[PIPELINE] Stage 3 completed in {stage3_time:.3f}s: confidence={mind_result.confidence_score}")

        # 4. Create new Memory object
        stage4_start = time.time()
        logger.debug("[PIPELINE] Stage 4: Creating updated Memory object...")
        new_memory = self._create_updated_memory(
            previous_memory, update_result, mind_result
        )
        stage4_time = time.time() - stage4_start
        logger.debug(f"[PIPELINE] Stage 4 completed in {stage4_time:.3f}s: Memory object created with ID={new_memory.memory_id}")

        # 5. Build pipeline results
        logger.debug("[PIPELINE] Stage 5: Building pipeline results...")
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

        # Log final results
        new_profile = new_memory.get_profile_content()
        new_events = new_memory.get_event_content()
        new_mind = new_memory.get_mind_content()
        
        total_pipeline_time = time.time() - pipeline_start_time
        
        logger.info(f"[PIPELINE] ✅ Pipeline completed successfully!")
        logger.info(f"[PIPELINE] Performance summary: total_time={total_pipeline_time:.3f}s, stage1={stage1_time:.3f}s, stage2={stage2_time:.3f}s, stage3={stage3_time:.3f}s, stage4={stage4_time:.3f}s")
        logger.info(f"[PIPELINE] Final memory state: profile_items={len(new_profile)}, events={len(new_events)}, mind_insights={len(new_mind)}")
        logger.info(f"[PIPELINE] Memory changes: profile_delta={len(new_profile)-len(current_profile)}, events_delta={len(new_events)-len(current_events)}, mind_delta={len(new_mind)-len(current_mind)}")
        logger.info(f"[PIPELINE] Model used: {getattr(self.llm_client, 'model_name', 'unknown')}, Total stages: 5")
        
        return new_memory, pipeline_result

    def llm_modification_stage(
        self, previous_memory: Memory, session_conversation: List[Dict[str, str]]
    ) -> str:
        """
        LLM Modification stage: Analyze conversation and extract relevant information
        """
        logger.info("[PIPELINE] [MOD] Analyzing conversation and extracting information...")
        
        # Build LLM prompt
        conversation_text = self._format_conversation(session_conversation)
        current_profile = previous_memory.get_profile_content()
        current_events = previous_memory.get_event_content()
        
        logger.info(f"[PIPELINE] [MOD] Input analysis: profile_items={len(current_profile) if current_profile else 0}, events={len(current_events) if current_events else 0}")
        logger.info(f"[PIPELINE] [MOD] Conversation text length: {len(conversation_text)} chars")
        logger.debug(f"[PIPELINE] [MOD] Conversation content: {conversation_text[:200]}{'...' if len(conversation_text) > 200 else ''}")

        prompt = f"""Please analyze the following conversation content and extract user profile updates and important events.

Current User Profile:
{self._format_profile(current_profile) if current_profile else "None"}

Current Event Records:
{self._format_events(current_events) if current_events else "None"}

Current Conversation Content:
{conversation_text}

Note:
1. the profile must be factual and accurate.
2. the profile must be very concise and clear.
3. the events must be very concise and clear.
4. the profile and events must be updated based on the conversation content.

Return the updated profile and events suggestion directly in the following XML format:
<update>
Add: profile [new profile item]
Delete: profile [profile item to remove]
Update: profile [profile item to update] -> profile [new profile item]
Add: event [new event item]
Delete: event [event item to remove]
Update: event [event item to update] -> event [new event item]
...
</update>
"""

        # Call LLM
        messages = [{"role": "user", "content": prompt}]

        if self.llm_client is None:
            logger.error("[PIPELINE] [MOD] No LLM client provided for modification stage")
            raise Exception("No LLM client provided")

        logger.info("[PIPELINE] [MOD] Calling LLM for conversation analysis...")
        logger.debug(f"[PIPELINE] [MOD] LLM prompt length: {len(prompt)} chars")
        
        response = self.llm_client.chat_completion(messages=messages)
        if not response.success:
            logger.error(f"[PIPELINE] [MOD] LLM call failed: {response.error}")
            raise Exception(f"LLM call failed: {response.error}")

        logger.info(f"[PIPELINE] [MOD] LLM analysis completed: {len(response.content)} chars generated")
        logger.debug(f"[PIPELINE] [MOD] LLM response preview: {response.content[:200]}{'...' if len(response.content) > 200 else ''}")
        
        # Log the full LLM response
        logger.info(f"[PIPELINE] [MOD] Full LLM response:")
        logger.info(f"[PIPELINE] [MOD] Response content: {response.content}")
        
        if hasattr(response, 'usage') and response.usage:
            logger.info(f"[PIPELINE] [MOD] LLM usage: {response.usage}")
        
        return response.content

    def llm_update_stage(
        self, previous_memory: Memory, modification_result: str
    ) -> UpdateResult:
        """
        LLM Update stage: Update user profile using LLM analysis
        """
        logger.info("[PIPELINE] [UPD] Updating user profile and events...")
        
        # Parse modification_result to extract profile and events information
        profile_updates, events_updates = self._parse_modification_result(
            modification_result
        )

        current_profile = previous_memory.get_profile_content()
        current_events = previous_memory.get_event_content()
        
        logger.info(f"[PIPELINE] [UPD] Extracted updates: profile_items={len(profile_updates)}, events={len(events_updates)}")
        logger.debug(f"[PIPELINE] [UPD] Profile updates: {profile_updates}")
        logger.debug(f"[PIPELINE] [UPD] Event updates: {events_updates}")
        # Build profile update prompt
        prompt = f"""Please update the user profile based on new information.

Current User Profile:
{self._format_profile(current_profile) if current_profile else "None"}

Current Event Records:
{self._format_events(current_events) if current_events else "None"}

Update Suggestion:
{modification_result}

Please integrate the new information into the user profile to generate a complete, coherent user profile description.
Requirements:
1. Based on the update suggestion, update the user profile and event records.
2. must follow the update suggestion.
3. all suggestions should be followed.
4. the profile must be factual and accurate.
5. the profile must be very concise and clear.
6. the events must be very concise and clear.

Please return the updated complete user profile directly in the following XML format:
<memory>
<profile>
<item>profile item 1</item>
<item>profile item 2</item>
</profile>
<events>
<item>event item 1</item>
<item>event item 2</item>
</events>
</memory>
"""

        # Call LLM to update profile
        messages = [{"role": "user", "content": prompt}]

        if self.llm_client is None:
            logger.error("[PIPELINE] [UPD] No LLM client provided for update stage")
            raise Exception("No LLM client provided")

        logger.info("[PIPELINE] [UPD] Calling LLM for profile and events update...")
        logger.debug(f"[PIPELINE] [UPD] Update prompt length: {len(prompt)} chars")
        
        response = self.llm_client.chat_completion(messages=messages)

        if not response.success:
            logger.error(f"[PIPELINE] [UPD] LLM update failed: {response.error}")
            raise Exception(f"LLM update failed: {response.error}")

        # Log the full LLM response
        logger.info(f"[PIPELINE] [UPD] Full LLM response:")
        logger.info(f"[PIPELINE] [UPD] Response content: {response.content}")

        # Parse LLM results and separate profile and events
        updated_profile, updated_events = self._parse_modification_result(
            response.content
        )
        
        logger.info(f"[PIPELINE] [UPD] Generated updates: profile_items={len(updated_profile)}, events={len(updated_events)}")
        logger.debug(f"[PIPELINE] [UPD] Updated profile content: {updated_profile}")
        logger.debug(f"[PIPELINE] [UPD] Updated events content: {updated_events}")
        
        if hasattr(response, 'usage') and response.usage:
            logger.info(f"[PIPELINE] [UPD] LLM usage: {response.usage}")

        # Create updated EventMemory with the combined event list
        updated_events = EventMemory(
            events=updated_events, max_events=previous_memory.event_memory.max_events
        )

        return UpdateResult(
            profile=ProfileMemory(updated_profile),
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
        logger.info("[PIPELINE] [MIND] Performing Theory of Mind analysis...")
        
        conversation_text = self._format_conversation(session_conversation)
        updated_memory_content = (
            "\n".join(update_result.profile.get_content())
            + "\n"
            + "\n".join(update_result.events.get_content())
        )
        
        logger.info(f"[PIPELINE] [MIND] Analysis input: memory_content={len(updated_memory_content)} chars, conversation={len(conversation_text)} chars")
        logger.debug(f"[PIPELINE] [MIND] Memory content preview: {updated_memory_content[:200]}{'...' if len(updated_memory_content) > 200 else ''}")
        logger.debug(f"[PIPELINE] [MIND] Conversation preview: {conversation_text[:200]}{'...' if len(conversation_text) > 200 else ''}")

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
5. should be concise and clear

Please return the insights directly in the following XML format:
<insights>
<item>Insight 1</item>
<item>Insight 2</item>
<item>Insight 3</item>
</insights>
"""

        # Call LLM for Mind analysis
        messages = [{"role": "user", "content": prompt}]

        if self.llm_client is None:
            logger.error("[PIPELINE] [MIND] No LLM client provided for mind analysis stage")
            raise Exception("No LLM client provided")

        logger.info("[PIPELINE] [MIND] Calling LLM for psychological analysis...")
        logger.debug(f"[PIPELINE] [MIND] Analysis prompt length: {len(prompt)} chars")
        
        response = self.llm_client.chat_completion(messages=messages)

        if not response.success:
            logger.error(f"[PIPELINE] [MIND] LLM Mind analysis failed: {response.error}")
            raise Exception(f"LLM Mind analysis failed: {response.error}")

        # Log the full LLM response
        logger.info(f"[PIPELINE] [MIND] Full LLM response:")
        logger.info(f"[PIPELINE] [MIND] Response content: {response.content}")

        # Store insights directly as string
        insights = response.content
        
        logger.info(f"[PIPELINE] [MIND] Psychological analysis completed: {len(insights)} chars generated")
        logger.debug(f"[PIPELINE] [MIND] Insights preview: {insights[:200]}{'...' if len(insights) > 200 else ''}")
        
        if hasattr(response, 'usage') and response.usage:
            logger.info(f"[PIPELINE] [MIND] LLM usage: {response.usage}")

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
        logger.info("[PIPELINE] [CREATE] Creating updated Memory object...")
        logger.debug(f"[PIPELINE] [CREATE] Memory ID: {previous_memory.memory_id}")
        
        new_memory = Memory(
            agent_id=previous_memory.agent_id,
            user_id=previous_memory.user_id,
            memory_client=previous_memory.memory_client,
            memory_id=previous_memory.memory_id,
        )
        
        # Preserve timestamps from previous memory
        new_memory.created_at = previous_memory.created_at
        new_memory.updated_at = datetime.now()

        # Set updated components
        new_memory.profile_memory = update_result.profile
        new_memory.event_memory = update_result.events

        # Set Theory of Mind memory, parse insights text to list
        insights_text = mind_result.insights
        if insights_text:
            # Parse insights using XML parsing with text fallback
            insights_list = self._parse_insights_content(insights_text)

            # Create MindMemory component directly instead of calling update_mind
            from .base import MindMemory
            new_memory.mind_memory = MindMemory(insights_list)
            
            logger.info(f"[PIPELINE] [CREATE] Mind insights parsed: {len(insights_list)} items")
            logger.debug(f"[PIPELINE] [CREATE] Mind insights content: {insights_list}")
        else:
            # Create empty MindMemory if no insights
            from .base import MindMemory  
            new_memory.mind_memory = MindMemory([])

        # Get insights count for logging
        insights_count = len(new_memory.mind_memory.get_content()) if new_memory.mind_memory else 0
        logger.info(f"[PIPELINE] [CREATE] Memory object created with components: profile={len(update_result.profile.get_content())}, events={len(update_result.events.get_content())}, mind_insights={insights_count}")
        logger.debug(f"[PIPELINE] [CREATE] Created memory ID: {new_memory.memory_id}")
        return new_memory

    def _parse_modification_result(self, content: str) -> Tuple[List[str], List[str]]:
        """
        Parse LLM returned content, extract profile and events
        Uses XML parsing for accurate extraction

        Returns:
            Tuple[profile_updates, events_updates]
        """
        profile_updates = []
        events_updates = []

        try:
            # First try XML parsing
            logger.info("[PIPELINE] [PARSE] Attempting XML parsing...")
            
            # Clean the content and extract XML
            xml_content = self._extract_xml_content(content)
            if xml_content:
                logger.debug(f"[PIPELINE] [PARSE] Extracted XML: {xml_content}")
                
                # Parse XML
                root = ET.fromstring(xml_content)
                
                # Handle <memory> format (from update stage)
                if root.tag == 'memory':
                    # Extract profile items
                    for profile_section in root.findall('.//profile'):
                        for item in profile_section.findall('item'):
                            if item.text and item.text.strip():
                                profile_updates.append(item.text.strip())
                    
                    # Extract events items
                    for events_section in root.findall('.//events'):
                        for item in events_section.findall('item'):
                            if item.text and item.text.strip():
                                events_updates.append(item.text.strip())
                
                # Handle <update> format (from modification stage) - parse text instructions
                elif root.tag == 'update':
                    text_content = root.text if root.text else ""
                    for child in root:
                        if child.text:
                            text_content += child.text
                        if child.tail:
                            text_content += child.tail
                    
                    # Parse Add/Update/Remove instructions
                    lines = text_content.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line.startswith('Add: profile '):
                            item = line.replace('Add: profile ', '').strip('[]"')
                            if item:
                                profile_updates.append(item)
                        elif line.startswith('Update: profile '):
                            # Extract the new profile item after '->'
                            if ' -> profile ' in line:
                                item = line.split(' -> profile ')[1].strip('[]"')
                                if item:
                                    profile_updates.append(item)
                        elif line.startswith('Add: event '):
                            item = line.replace('Add: event ', '').strip('[]"')
                            if item:
                                events_updates.append(item)
                        elif line.startswith('Update: event '):
                            # Extract the new event item after '->'
                            if ' -> event ' in line:
                                item = line.split(' -> event ')[1].strip('[]"')
                                if item:
                                    events_updates.append(item)
                
                # Handle <analysis> format (legacy)
                elif root.tag == 'analysis':
                    # Extract profile items
                    for profile_section in root.findall('.//profile'):
                        for item in profile_section.findall('item'):
                            if item.text and item.text.strip():
                                profile_updates.append(item.text.strip())
                    
                    # Extract events items
                    for events_section in root.findall('.//events'):
                        for item in events_section.findall('item'):
                            if item.text and item.text.strip():
                                events_updates.append(item.text.strip())
                
                logger.info(f"[PIPELINE] [PARSE] XML parsing successful: {len(profile_updates)} profile items, {len(events_updates)} events")
                logger.debug(f"[PIPELINE] [PARSE] Profile content: {profile_updates}")
                logger.debug(f"[PIPELINE] [PARSE] Events content: {events_updates}")
                
                return profile_updates, events_updates
            
            # Fallback to text parsing if XML parsing fails
            logger.warning("[PIPELINE] [PARSE] XML parsing failed, falling back to text parsing...")
            return self._parse_text_format(content)
            
        except Exception as e:
            logger.error(f"[PIPELINE] [PARSE] XML parsing error: {e}")
            logger.debug(f"[PIPELINE] [PARSE] Content that failed to parse: {content[:500]}{'...' if len(content) > 500 else ''}")
            
            # Fallback to text parsing
            return self._parse_text_format(content)
    
    def _extract_xml_content(self, content: str) -> str:
        """Extract XML content from LLM response"""
        try:
            # Look for XML tags in the content
            xml_patterns = [
                r'<update>.*?</update>',
                r'<memory>.*?</memory>',
                r'<analysis>.*?</analysis>',
                r'<insights>.*?</insights>'
            ]
            
            for pattern in xml_patterns:
                match = re.search(pattern, content, re.DOTALL)
                if match:
                    return match.group(0)
            
            return None
        except Exception as e:
            logger.error(f"[PIPELINE] [PARSE] Error extracting XML: {e}")
            return None
    
    def _parse_text_format(self, content: str) -> Tuple[List[str], List[str]]:
        """Fallback text parsing for non-XML content"""
        profile_updates = []
        events_updates = []

        try:
            lines = content.strip().split("\n")
            current_section = None

            for line in lines:
                line = line.strip()
                
                # Skip empty lines
                if not line:
                    continue
                    
                # Detect section headers (case insensitive)
                if line.lower().startswith("profile:"):
                    current_section = "profile"
                    # Check if there's content after "profile:" on the same line
                    profile_text = line[8:].strip()
                    if profile_text:
                        profile_updates.append(profile_text)
                    continue
                elif line.lower().startswith("events:"):
                    current_section = "events"
                    # Check if there's content after "events:" on the same line
                    events_text = line[7:].strip()
                    if events_text:
                        events_updates.append(events_text)
                    continue
                elif line.lower().startswith("insights:"):
                    # Skip insights section for this function
                    current_section = "insights"
                    continue
                
                # Add content to current section - each line becomes an item
                if current_section == "profile":
                    # Remove "- " prefix if present, but keep the content
                    clean_line = line[2:].strip() if line.startswith("- ") else line
                    if clean_line:
                        profile_updates.append(clean_line)
                elif current_section == "events":
                    # Remove "- " prefix if present, but keep the content
                    clean_line = line[2:].strip() if line.startswith("- ") else line
                    if clean_line:
                        events_updates.append(clean_line)

            logger.info(f"[PIPELINE] [PARSE] Text parsing successful: {len(profile_updates)} profile items, {len(events_updates)} events")
            logger.debug(f"[PIPELINE] [PARSE] Profile content: {profile_updates}")
            logger.debug(f"[PIPELINE] [PARSE] Events content: {events_updates}")
            return profile_updates, events_updates
        
        except Exception as e:
            logger.error(f"[PIPELINE] [PARSE] Text parsing error: {e}")
            logger.debug(f"[PIPELINE] [PARSE] Content that failed to parse: {content[:500]}{'...' if len(content) > 500 else ''}")
            return [], []
    
    def _parse_insights_content(self, content: str) -> List[str]:
        """Parse insights content using XML parsing with text fallback"""
        insights_list = []
        
        try:
            # First try XML parsing
            logger.info("[PIPELINE] [PARSE] Attempting XML parsing for insights...")
            
            # Extract XML content
            xml_content = self._extract_xml_content(content)
            if xml_content:
                logger.debug(f"[PIPELINE] [PARSE] Extracted insights XML: {xml_content}")
                
                # Parse XML
                root = ET.fromstring(xml_content)
                
                # Extract insights items
                for item in root.findall('.//item'):
                    if item.text and item.text.strip():
                        insights_list.append(item.text.strip())
                
                logger.info(f"[PIPELINE] [PARSE] XML parsing successful for insights: {len(insights_list)} items")
                logger.debug(f"[PIPELINE] [PARSE] Insights content: {insights_list}")
                
                return insights_list
            
            # Fallback to text parsing if XML parsing fails
            logger.warning("[PIPELINE] [PARSE] XML parsing failed for insights, falling back to text parsing...")
            return self._parse_insights_text_format(content)
            
        except Exception as e:
            logger.error(f"[PIPELINE] [PARSE] XML parsing error for insights: {e}")
            logger.debug(f"[PIPELINE] [PARSE] Content that failed to parse: {content[:500]}{'...' if len(content) > 500 else ''}")
            
            # Fallback to text parsing
            return self._parse_insights_text_format(content)
    
    def _parse_insights_text_format(self, content: str) -> List[str]:
        """Fallback text parsing for insights"""
        insights_list = []
        
        try:
            lines = content.strip().split("\n")
            
            for line in lines:
                line = line.strip()
                
                # Skip empty lines
                if not line:
                    continue
                    
                # Skip section headers like "Insights:"
                if line.lower().startswith("insights:"):
                    continue
                    
                # Remove "- " prefix if present, but keep the content
                clean_line = line[2:].strip() if line.startswith("- ") else line
                if clean_line:
                    insights_list.append(clean_line)
            
            logger.info(f"[PIPELINE] [PARSE] Text parsing successful for insights: {len(insights_list)} items")
            logger.debug(f"[PIPELINE] [PARSE] Insights content: {insights_list}")
            return insights_list
            
        except Exception as e:
            logger.error(f"[PIPELINE] [PARSE] Text parsing error for insights: {e}")
            logger.debug(f"[PIPELINE] [PARSE] Content that failed to parse: {content[:500]}{'...' if len(content) > 500 else ''}")
            return []

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

    def _format_profile(self, profile_items: List[str]) -> str:
        """Format profile items for prompt"""
        if not profile_items:
            return "None"
        return "\n".join(f"- {item}" for item in profile_items)
