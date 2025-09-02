"""
MemU Memory Agent - Action-Based Architecture

Modern memory management system with function calling interface.
Each operation is implemented as a separate action module for modularity and maintainability.
"""

import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List

from ..config.markdown_config import get_config_manager
from ..llm import BaseLLMClient
from ..utils import get_logger
from .actions import ACTION_REGISTRY
from .embeddings import get_default_embedding_client
from .file_manager import MemoryFileManager

logger = get_logger(__name__)


class MemoryCore:
    """
    Core memory functionality shared across all actions

    Provides the shared resources and utilities that actions need:
    - LLM client
    - Storage manager
    - Embedding client
    - Configuration
    """

    def __init__(
        self,
        llm_client: BaseLLMClient,
        memory_dir: str = "memu/server/memory",
        enable_embeddings: bool = True,
        agent_id: str = "",
        user_id: str = "",
    ):
        self.llm_client = llm_client
        self.memory_dir = Path(memory_dir)
        self._stop_flag = threading.Event()

        # Initialize config manager and processing order (basic only)
        self.config_manager = get_config_manager()
        self.processing_order = self.config_manager.get_processing_order()

        # Initialize file-based storage manager with context (shared by actions)
        self.storage_manager = MemoryFileManager(memory_dir, agent_id=agent_id, user_id=user_id)
        # Initialize memory types from storage manager (includes cluster for this context)
        self.memory_types = self.storage_manager.memory_types

        # Initialize embedding client
        self.enable_embeddings = enable_embeddings
        if enable_embeddings:
            try:
                self.embedding_client = get_default_embedding_client()
                self.embeddings_enabled = True
                logger.info("Embeddings enabled for semantic retrieval")
            except Exception as e:
                logger.warning(
                    f"Failed to initialize embedding client: {e}. Embeddings disabled."
                )
                self.embedding_client = None
                self.embeddings_enabled = False
        else:
            self.embedding_client = None
            self.embeddings_enabled = False

        # Create storage directories
        self.embeddings_dir = self.memory_dir / "embeddings"
        self.embeddings_dir.mkdir(exist_ok=True)

        logger.info(
            f"Memory Core initialized: {len(self.memory_types)} memory types, embeddings: {self.embeddings_enabled}"
        )


class MemoryAgent:
    """
    Modern Memory Agent with Action-Based Architecture

    Uses independent action modules for each memory operation:
    - add_activity_memory: Add new activity memory content with strict formatting
    - get_available_categories: Get available categories (excluding activity)
    - link_related_memories: Find and link related memories using embedding search
    - generate_memory_suggestions: Generate suggestions for memory categories
    - update_memory_with_suggestions: Update memory categories based on suggestions


    Each action is implemented as a separate module in the actions/ directory.
    """

    def __init__(
        self, *,
        llm_client: BaseLLMClient,
        agent_id: str = "default_agent",
        user_id: str = "default_user",
        memory_dir: str = "memu/server/memory",
        enable_embeddings: bool = True,
    ):
        """
        Initialize Memory Agent

        Args:
            llm_client: LLM client for processing conversations
            memory_dir: Directory to store memory files
            enable_embeddings: Whether to generate embeddings for semantic search
        """
        # Initialize memory core
        self.memory_core = MemoryCore(llm_client, memory_dir, enable_embeddings, agent_id, user_id)

        # Initialize actions
        self.actions = {}
        self._load_actions()

        # Build function registry for compatibility
        self.function_registry = self._build_function_registry()

        logger.info(f"Memory Agent initialized: {len(self.actions)} actions available")

    def _load_actions(self):
        """Load all available actions from the registry"""
        for action_name, action_class in ACTION_REGISTRY.items():
            try:
                action_instance = action_class(self.memory_core)
                self.actions[action_name] = action_instance
                logger.debug(f"Loaded action: {action_name}")
            except Exception as e:
                logger.error(f"Failed to load action {action_name}: {e}")

    def _build_function_registry(self) -> Dict[str, Callable]:
        """Build registry of callable functions from actions"""
        registry = {}
        for action_name, action in self.actions.items():
            registry[action_name] = action.execute
        return registry

    # ================================
    # Smart Conversation Processing
    # ================================

    def run(
        self,
        conversation: List[Dict[str, str]],
        character_name: str,
        max_iterations: int = 20,
        session_date: str = None,
    ) -> Dict[str, Any]:
        """
        Intelligent conversation processing using iterative function calling

        This function allows the LLM to autonomously decide which memory operations to perform
        through function calling, iterating until the LLM decides it's complete or max iterations reached.

        Args:
            conversation: List of conversation messages
            character_name: Name of the character to store memories for
            max_iterations: Maximum number of function calling iterations (default: 20)

        Returns:
            Dict containing processing results and file paths
        """
        try:
            if not conversation or not isinstance(conversation, list):
                return {
                    "success": False,
                    "error": "Invalid conversation format. Expected list of message dictionaries.",
                }

            if not character_name:
                return {"success": False, "error": "Character name is required."}

            try:
                session_date = datetime.fromisoformat(session_date).strftime("%Y-%m-%d")
            except Exception as e:
                logger.info(f"session date unavaiable, use system datetime")
                session_date = datetime.now().strftime("%Y-%m-%d")

            logger.info(
                f"🚀 Starting iterative conversation processing for {character_name}"
            )

            # Convert conversation to text for processing
            conversation_text = self._convert_conversation_to_text(conversation)

            # Initialize results tracking
            results = {
                "success": True,
                "character_name": character_name,
                "session_date": session_date,
                "conversation_length": len(conversation),
                "iterations": 0,
                "function_calls": [],
                # "files_generated": [],
                "processing_log": [],
            }

            # Get function schemas for LLM
            function_schemas = self.get_functions_schema()

            # Build initial system message
            system_message = f"""You are a memory processing agent. Follow this structured process to analyze and store conversation information for "{character_name}":

CONVERSATION TO PROCESS:
{conversation_text}

CHARACTER: {character_name}
SESSION DATE: {session_date}

PROCESSING WORKFLOW:
1. STORE TO ACTIVITY: Call add_activity_memory with the COMPLETE RAW CONVERSATION TEXT as the 'content' parameter. This will automatically append to existing activity memories. DO NOT extract, modify, or summarize the conversation - pass the entire original conversation text exactly as shown above.

2. THEORY OF MIND: Call run_theory_of_mind to analyze the subtle information behind the conversation and extract the theory of mind of the characters.

3. GENERATE SUGGESTIONS: Call generate_memory_suggestions with the available memory items to get suggestions for what should be added to each category.

4. UPDATE CATEGORIES: For each category that should be updated (based on suggestions), call update_memory_with_suggestions to update that category with the new memory items and suggestions. This will return structured modifications.

5. LINK MEMORIES: For each category that was modified, call link_related_memories with link_all_items=true and write_to_memory=true to add relevant links between ALL memories in that category.

6. CLUSTER MEMORIES: Call cluster_memories to cluster the memories into different categories.

IMPORTANT GUIDELINES:
- Step 1: CRITICAL: For add_activity_memory, the 'content' parameter MUST be the complete original conversation text exactly as shown above. Do NOT modify, extract, or summarize it.
- Step 2: Use both the original conversation and the extracted activity memoryitems from step 1 for the theory of mind analysis
- Step 3: Use BOTH the extracted memory items from step 1 and theory-of-mind items from step 2 for generating suggestions. You can simply concatenate the two lists of memory items and pass them to the subsequent function.
- Step 4: Use the memory suggestions from step 3 to update EVERY memory categories in suggestions.
- Step 5-6: Use the new memory items returned from step 4 for linking and clustering memories. DO NOT include the memory items returned from step 1 and 2.
- Each memory item should have its own memory_id and focused content
- Follow the suggestions when updating categories
- The update_memory_with_suggestions function will return structured format with memory_id and content
- Always link related memories after updating categories by setting link_all_items=true and write_to_memory=true

Start with step 1 and work through the process systematically. When you complete all steps, respond with "PROCESSING_COMPLETE"."""

            # Start iterative function calling
            messages = [{"role": "system", "content": system_message}]

            for iteration in range(max_iterations):
                results["iterations"] = iteration + 1
                logger.info(f"🔄 Iteration {iteration + 1}/{max_iterations}")

                try:
                    # Call LLM with function calling enabled
                    response = self.memory_core.llm_client.chat_completion(
                        messages=messages,
                        tools=[
                            {"type": "function", "function": schema}
                            for schema in function_schemas
                        ],
                        tool_choice="auto",
                        temperature=0.3,
                    )

                    if not response.success:
                        logger.error(f"LLM call failed: {response.error}")
                        break

                    # Add assistant response to conversation
                    assistant_message = {
                        "role": "assistant",
                        "content": response.content or "",
                    }

                    # Check if processing is complete
                    if response.content and "PROCESSING_COMPLETE" in response.content:
                        logger.info("✅ LLM indicated processing is complete")
                        results["processing_log"].append(
                            f"Iteration {iteration + 1}: Processing completed"
                        )
                        break

                    # Handle tool calls if present
                    if response.tool_calls:
                        assistant_message["tool_calls"] = response.tool_calls
                        messages.append(assistant_message)

                        # Execute each tool call
                        for tool_call in response.tool_calls:
                            function_name = tool_call.function.name

                            try:
                                arguments = json.loads(tool_call.function.arguments)
                            except json.JSONDecodeError as e:
                                logger.error(f"Failed to parse function arguments: {e}")
                                logger.error(f"Function name: {function_name}")
                                logger.error(
                                    f"Arguments raw: {repr(tool_call.function.arguments)}"
                                )
                                continue

                            logger.info(f"🔧 Calling function: {function_name}")

                            # Execute the function call
                            time_start = time.time()
                            function_result = self.call_function(
                                function_name, arguments
                            )
                            time_end = time.time()

                            logger.info(
                                f"    Function time used: {time_end - time_start:.2f} seconds"
                            )

                            # Track function call
                            call_record = {
                                "iteration": iteration + 1,
                                "function_name": function_name,
                                "arguments": arguments,
                                "result": function_result,
                            }
                            results["function_calls"].append(call_record)

                            # Add tool result to conversation
                            tool_message = {
                                "role": "tool",
                                "tool_call_id": getattr(
                                    tool_call, "id", f"call_{iteration}_{function_name}"
                                ),
                                "content": json.dumps(
                                    function_result, ensure_ascii=False
                                ),
                            }
                            messages.append(tool_message)

                            results["processing_log"].append(
                                f"Iteration {iteration + 1}: Called {function_name} - "
                                + (
                                    "Success"
                                    if function_result.get("success")
                                    else f"Failed: {function_result.get('error', 'Unknown error')}"
                                )
                            )
                    else:
                        # No tool calls, add response and continue
                        messages.append(assistant_message)
                        if response.content:
                            results["processing_log"].append(
                                f"Iteration {iteration + 1}: {response.content[:100]}..."
                            )

                except Exception as e:
                    logger.error(f"Error in iteration {iteration + 1}: {e}")
                    results["processing_log"].append(
                        f"Iteration {iteration + 1}: Error - {str(e)}"
                    )
                    break

            # Finalize results
            if results["iterations"] >= max_iterations:
                logger.warning(f"⚠️ Reached maximum iterations ({max_iterations})")
                results["processing_log"].append(
                    f"Reached maximum iterations ({max_iterations})"
                )

            logger.info(
                f"🎉 Conversation processing completed after {results['iterations']} iterations"
            )
            # logger.info(f"📁 Generated {len(results['files_generated'])} files")
            logger.info(f"🔧 Made {len(results['function_calls'])} function calls")

            return results

        except Exception as e:
            logger.error(f"Error in conversation processing: {e}")
            return {
                "success": False,
                "error": str(e),
                "character_name": character_name,
                "timestamp": datetime.now().isoformat(),
            }

    def _convert_conversation_to_text(self, conversation: List[Dict]) -> str:
        """Convert conversation list to text format for LLM processing"""
        if not conversation or not isinstance(conversation, list):
            return ""

        text_parts = []
        for message in conversation:
            role = message.get("role", "unknown")
            content = message.get("content", "")
            text_parts.append(f"{role.upper()}: {content.strip()}")

        return "\n".join(text_parts)

    # ================================
    # Function Calling Interface
    # ================================

    def get_functions_schema(self) -> List[Dict[str, Any]]:
        """
        Get OpenAI-compatible function schemas for all memory functions

        Returns:
            List of function schemas that can be used with OpenAI function calling
        """
        schemas = []
        for action in self.actions.values():
            try:
                schema = action.get_schema()
                schemas.append(schema)
            except Exception as e:
                logger.error(
                    f"Failed to get schema for action {action.action_name}: {e}"
                )
        return schemas

    def call_function(
        self, function_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Call a memory function with the provided arguments

        Args:
            function_name: Name of the function to call
            arguments: Arguments to pass to the function

        Returns:
            Dict containing the function result
        """
        try:
            if function_name not in self.actions:
                return {
                    "success": False,
                    "error": f"Unknown function: {function_name}",
                    "available_functions": list(self.actions.keys()),
                }

            # Get the action instance
            action = self.actions[function_name]

            # Execute the action with arguments
            result = action.execute(**arguments)

            logger.debug(f"Function call successful: {function_name}")
            return result

        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "function_name": function_name,
                "timestamp": datetime.now().isoformat(),
            }
            logger.error(f"Function call failed: {function_name} - {repr(e)}")
            import traceback

            traceback.print_exc()
            return error_result

    def validate_function_call(
        self, function_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate a function call before execution

        Args:
            function_name: Name of the function
            arguments: Arguments for the function

        Returns:
            Dict with validation result
        """
        try:
            if function_name not in self.actions:
                return {
                    "valid": False,
                    "error": f"Unknown function: {function_name}",
                    "available_functions": list(self.actions.keys()),
                }

            # Use the action's validation method
            action = self.actions[function_name]
            return action.validate_arguments(arguments)

        except Exception as e:
            return {"valid": False, "error": f"Validation error: {str(e)}"}

    # ================================
    # Direct Method Access (Compatibility)
    # ================================

    def get_available_categories(self) -> Dict[str, Any]:
        """Get available memory categories"""
        return self.actions["get_available_categories"].execute()

    def link_related_memories(
        self,
        character_name: str,
        category: str,
        memory_id: str = None,
        top_k: int = 5,
        min_similarity: float = 0.3,
        search_categories: List[str] = None,
        link_all_items: bool = False,
        write_to_memory: bool = False,
    ) -> Dict[str, Any]:
        """Find and link related memories using embedding search"""
        return self.actions["link_related_memories"].execute(
            character_name=character_name,
            category=category,
            memory_id=memory_id,
            top_k=top_k,
            min_similarity=min_similarity,
            search_categories=search_categories,
            link_all_items=link_all_items,
            write_to_memory=write_to_memory,
        )

    # ================================
    # Utility Methods
    # ================================

    def get_function_list(self) -> List[str]:
        """Get list of available function names"""
        return list(self.actions.keys())

    def get_function_description(self, function_name: str) -> str:
        """Get description for a specific function"""
        if function_name in self.actions:
            try:
                schema = self.actions[function_name].get_schema()
                return schema.get("description", "No description available")
            except Exception:
                return "Description not available"
        return "Function not found"

    def get_action_instance(self, action_name: str):
        """Get a specific action instance (for advanced usage)"""
        return self.actions.get(action_name)

    def stop_action(self) -> Dict[str, Any]:
        """
        Stop current operations

        Returns:
            Dict containing stop result
        """
        try:
            self.memory_core._stop_flag.set()
            logger.info("Memory Agent: Stop flag set")

            return {
                "success": True,
                "message": "Stop signal sent to Memory Agent operations",
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error stopping operations: {e}")
            return {"success": False, "error": str(e)}

    def reset_stop_flag(self):
        """Reset the stop flag to allow new operations"""
        self.memory_core._stop_flag.clear()
        logger.debug("Memory Agent: Stop flag reset")

    def get_status(self) -> Dict[str, Any]:
        """Get status information about the memory agent"""
        return {
            "agent_name": "memory_agent",
            "architecture": "action_based",
            "memory_types": list(self.memory_core.memory_types.keys()),
            "processing_order": self.memory_core.processing_order,
            "storage_type": "file_system",
            "memory_dir": str(self.memory_core.memory_dir),
            "config_source": "memory_cat_config.yaml (system + custom)",
            "total_actions": len(self.actions),
            "available_actions": list(self.actions.keys()),
            "total_functions": len(self.function_registry),
            "available_functions": list(self.function_registry.keys()),
            "function_calling_enabled": True,
            "stop_flag_set": self.memory_core._stop_flag.is_set(),
            "embedding_capabilities": {
                "embeddings_enabled": self.memory_core.embeddings_enabled,
                "embedding_client": (
                    str(type(self.memory_core.embedding_client))
                    if self.memory_core.embedding_client
                    else None
                ),
                "embeddings_directory": str(self.memory_core.embeddings_dir),
            },
            "config_details": {
                "total_file_types": len(self.memory_core.memory_types),
                "categories_from_config": True,
                "config_structure": "Dynamic folder configuration",
            },
            "last_updated": datetime.now().isoformat(),
        }
