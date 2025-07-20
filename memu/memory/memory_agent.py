"""
MemU Memory Agent - Action-Based Architecture

Modern memory management system with function calling interface.
Each operation is implemented as a separate action module for modularity and maintainability.
"""

import threading
from pathlib import Path
from typing import Dict, List, Any, Callable
from datetime import datetime

from ..llm import BaseLLMClient
from ..utils import get_logger
from .file_manager import MemoryFileManager
from .embeddings import get_default_embedding_client
from ..config.markdown_config import get_config_manager
from .actions import ACTION_REGISTRY

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
        memory_dir: str = "memory",
        enable_embeddings: bool = True
    ):
        self.llm_client = llm_client
        self.memory_dir = Path(memory_dir)
        self._stop_flag = threading.Event()
        
        # Initialize memory types from config
        self.config_manager = get_config_manager()
        self.memory_types = self.config_manager.get_file_types_mapping()
        self.processing_order = self.config_manager.get_processing_order()
        
        # Initialize file-based storage manager
        self.storage_manager = MemoryFileManager(memory_dir)
        
        # Initialize embedding client
        self.enable_embeddings = enable_embeddings
        if enable_embeddings:
            try:
                self.embedding_client = get_default_embedding_client()
                self.embeddings_enabled = True
                logger.info("Embeddings enabled for semantic retrieval")
            except Exception as e:
                logger.warning(f"Failed to initialize embedding client: {e}. Embeddings disabled.")
                self.embedding_client = None
                self.embeddings_enabled = False
        else:
            self.embedding_client = None
            self.embeddings_enabled = False
        
        # Create storage directories
        self.embeddings_dir = self.memory_dir / "embeddings"
        self.embeddings_dir.mkdir(exist_ok=True)
        
        logger.info(f"Memory Core initialized: {len(self.memory_types)} memory types, embeddings: {self.embeddings_enabled}")


class MemoryAgent:
    """
    Modern Memory Agent with Action-Based Architecture
    
    Uses independent action modules for each memory operation:
    - add_memory: Add new memory content  
    - read_memory: Read memory content
    - search_memory: Search memory using embeddings
    - update_memory: Update specific memory item by ID
    - delete_memory: Delete memory content
    - get_available_categories: Get available categories
    - link_related_memories: Find and link related memories using embedding search
    
    Each action is implemented as a separate module in the actions/ directory.
    """
    
    def __init__(
        self,
        llm_client: BaseLLMClient,
        memory_dir: str = "memory",
        enable_embeddings: bool = True
    ):
        """
        Initialize Memory Agent
        
        Args:
            llm_client: LLM client for processing conversations
            memory_dir: Directory to store memory files
            enable_embeddings: Whether to generate embeddings for semantic search
        """
        # Initialize memory core
        self.memory_core = MemoryCore(llm_client, memory_dir, enable_embeddings)
        
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
                logger.error(f"Failed to get schema for action {action.action_name}: {e}")
        return schemas

    def call_function(self, function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
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
                    "available_functions": list(self.actions.keys())
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
                "timestamp": datetime.now().isoformat()
            }
            logger.error(f"Function call failed: {function_name} - {e}")
            return error_result

    def validate_function_call(self, function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
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
                    "available_functions": list(self.actions.keys())
                }
            
            # Use the action's validation method
            action = self.actions[function_name]
            return action.validate_arguments(arguments)
            
        except Exception as e:
            return {
                "valid": False,
                "error": f"Validation error: {str(e)}"
            }

    # ================================
    # Direct Method Access (Compatibility)
    # ================================

    def add_memory(
        self,
        character_name: str,
        category: str,
        content: str,
        append: bool = True,
        generate_embeddings: bool = True
    ) -> Dict[str, Any]:
        """Add new memory content"""
        return self.actions["add_memory"].execute(
            character_name=character_name,
            category=category,
            content=content,
            append=append,
            generate_embeddings=generate_embeddings
        )

    def read_memory(
        self,
        character_name: str,
        category: str = None
    ) -> Dict[str, Any]:
        """Read memory content"""
        return self.actions["read_memory"].execute(
            character_name=character_name,
            category=category
        )

    def search_memory(
        self,
        character_name: str,
        query: str,
        categories: List[str] = None,
        limit: int = 5,
        use_embeddings: bool = True
    ) -> Dict[str, Any]:
        """Search memory content"""
        return self.actions["search_memory"].execute(
            character_name=character_name,
            query=query,
            categories=categories,
            limit=limit,
            use_embeddings=use_embeddings
        )

    def update_memory(
        self,
        character_name: str,
        category: str,
        memory_id: str,
        new_content: str,
        regenerate_embeddings: bool = True
    ) -> Dict[str, Any]:
        """Update existing memory content by memory ID"""
        return self.actions["update_memory"].execute(
            character_name=character_name,
            category=category,
            memory_id=memory_id,
            new_content=new_content,
            regenerate_embeddings=regenerate_embeddings
        )

    def delete_memory(
        self,
        character_name: str,
        category: str = None,
        delete_embeddings: bool = True
    ) -> Dict[str, Any]:
        """Delete memory content"""
        return self.actions["delete_memory"].execute(
            character_name=character_name,
            category=category,
            delete_embeddings=delete_embeddings
        )

    def get_available_categories(self) -> Dict[str, Any]:
        """Get available memory categories"""
        return self.actions["get_available_categories"].execute()

    def link_related_memories(
        self,
        character_name: str,
        memory_id: str,
        category: str,
        top_k: int = 5,
        min_similarity: float = 0.3,
        search_categories: List[str] = None,
        link_format: str = "markdown",
        write_to_memory: bool = False
    ) -> Dict[str, Any]:
        """Find and link related memories using embedding search"""
        return self.actions["link_related_memories"].execute(
            character_name=character_name,
            memory_id=memory_id,
            category=category,
            top_k=top_k,
            min_similarity=min_similarity,
            search_categories=search_categories,
            link_format=link_format,
            write_to_memory=write_to_memory
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
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error stopping operations: {e}")
            return {
                "success": False,
                "error": str(e)
            }

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
            "config_source": "markdown_config.py (dynamic folder structure)",
            "total_actions": len(self.actions),
            "available_actions": list(self.actions.keys()),
            "total_functions": len(self.function_registry),
            "available_functions": list(self.function_registry.keys()),
            "function_calling_enabled": True,
            "stop_flag_set": self.memory_core._stop_flag.is_set(),
            "embedding_capabilities": {
                "embeddings_enabled": self.memory_core.embeddings_enabled,
                "embedding_client": str(type(self.memory_core.embedding_client)) if self.memory_core.embedding_client else None,
                "embeddings_directory": str(self.memory_core.embeddings_dir)
            },
            "config_details": {
                "total_file_types": len(self.memory_core.memory_types),
                "categories_from_config": True,
                "config_structure": "Dynamic folder configuration"
            },
            "last_updated": datetime.now().isoformat()
        } 