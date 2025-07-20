"""
Base Action Class for Memory Operations

Defines the interface and common functionality for all memory actions.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any
from datetime import datetime

from ...utils import get_logger

logger = get_logger(__name__)


class BaseAction(ABC):
    """
    Base class for all memory actions
    
    Defines the standard interface that all actions must implement:
    - get_schema(): Return OpenAI-compatible function schema
    - execute(**kwargs): Execute the action with given arguments
    - validate_arguments(): Validate input arguments
    """
    
    def __init__(self, memory_core):
        """
        Initialize action with memory core
        
        Args:
            memory_core: Core memory functionality (file manager, embeddings, config, etc.)
        """
        self.memory_core = memory_core
        self.llm_client = memory_core.llm_client
        self.storage_manager = memory_core.storage_manager
        self.embedding_client = memory_core.embedding_client
        self.embeddings_enabled = memory_core.embeddings_enabled
        self.config_manager = memory_core.config_manager
        self.memory_types = memory_core.memory_types
        self.processing_order = memory_core.processing_order
        self.embeddings_dir = memory_core.embeddings_dir
        
    @property
    @abstractmethod
    def action_name(self) -> str:
        """Return the name of this action"""
        pass
    
    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """
        Return OpenAI-compatible function schema for this action
        
        Returns:
            Dict containing function schema with name, description, and parameters
        """
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the action with provided arguments
        
        Args:
            **kwargs: Action-specific arguments
            
        Returns:
            Dict containing execution result with success status and data
        """
        pass
    
    def validate_arguments(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate input arguments against schema
        
        Args:
            arguments: Arguments to validate
            
        Returns:
            Dict with validation result
        """
        try:
            schema = self.get_schema()
            required_params = schema["parameters"].get("required", [])
            
            # Check for missing required parameters
            missing_params = [param for param in required_params if param not in arguments]
            
            if missing_params:
                return {
                    "valid": False,
                    "error": f"Missing required parameters: {missing_params}",
                    "required_parameters": required_params
                }
            
            return {
                "valid": True,
                "message": f"Validation passed for {self.action_name}"
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": f"Validation error: {str(e)}"
            }
    
    def _add_metadata(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Add standard metadata to action result"""
        if isinstance(result, dict):
            result["action_name"] = self.action_name
            result["timestamp"] = datetime.now().isoformat()
        return result
    
    def _handle_error(self, error: Exception) -> Dict[str, Any]:
        """Standard error handling for actions"""
        error_result = {
            "success": False,
            "error": str(error),
            "action_name": self.action_name,
            "timestamp": datetime.now().isoformat()
        }
        logger.error(f"Action {self.action_name} failed: {error}")
        return error_result
    
    # Common utility methods that actions can use
    def _load_existing_memory(self, character_name: str) -> Dict[str, str]:
        """Load existing memory content for all types"""
        existing_memory = {}
        
        for memory_type in self.memory_types:
            try:
                content = self._read_memory_content(character_name, memory_type)
                existing_memory[memory_type] = content if isinstance(content, str) else ""
            except Exception as e:
                logger.warning(f"Failed to load existing {memory_type} for {character_name}: {e}")
                existing_memory[memory_type] = ""
        
        return existing_memory
    
    def _read_memory_content(self, character_name: str, memory_type: str) -> str:
        """Read memory content from storage"""
        try:
            if hasattr(self.storage_manager, 'read_memory_file'):
                return self.storage_manager.read_memory_file(character_name, memory_type)
            else:
                method_name = f"read_{memory_type}"
                if hasattr(self.storage_manager, method_name):
                    return getattr(self.storage_manager, method_name)(character_name)
                else:
                    logger.warning(f"No read method available for {memory_type}")
                    return ""
        except Exception as e:
            logger.warning(f"Failed to read {memory_type} for {character_name}: {e}")
            return ""
    
    def _save_memory_content(self, character_name: str, memory_type: str, content: str) -> bool:
        """Save memory content to storage"""
        try:
            if hasattr(self.storage_manager, 'write_memory_file'):
                return self.storage_manager.write_memory_file(character_name, memory_type, content)
            else:
                method_name = f"write_{memory_type}"
                if hasattr(self.storage_manager, method_name):
                    return getattr(self.storage_manager, method_name)(character_name, content)
                else:
                    logger.error(f"No write method available for {memory_type}")
                    return False
        except Exception as e:
            logger.error(f"Failed to save {memory_type} for {character_name}: {e}")
            return False
    
    def _convert_conversation_to_text(self, conversation: List[Dict]) -> str:
        """Convert conversation list to text format for LLM processing"""
        if not conversation or not isinstance(conversation, list):
            return ""
        
        text_parts = []
        for message in conversation:
            role = message.get("role", "unknown")
            content = message.get("content", "")
            text_parts.append(f"{role.upper()}: {content}")
        
        return "\n".join(text_parts) 