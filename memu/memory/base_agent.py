"""
Base Agent Class for MemU Memory System

Defines the common interface and capabilities for all specialized memory agents.
Each agent is responsible for managing its own memory type and has complete
LLM processing and storage capabilities.
"""

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..llm import BaseLLMClient
from ..utils import get_logger
from .file_manager import MemoryFileManager
from .db_manager import MemoryDatabaseManager
from .embeddings import get_default_embedding_client
from ..prompts.prompt_loader import get_prompt_loader

logger = get_logger(__name__)


class BaseAgent(ABC):
    """
    Base class for all specialized memory agents.
    
    Each agent has complete capabilities:
    - LLM processing for its domain
    - Direct file/database operations for its memory type
    - Embedding generation for semantic search
    - Independent execution and error handling
    """
    
    def __init__(
        self,
        agent_name: str,
        memory_type: str,
        llm_client: BaseLLMClient,
        memory_dir: str = "memory",
        use_database: bool = True,
        embedding_client=None,
        **db_kwargs
    ):
        """
        Initialize Base Agent
        
        Args:
            agent_name: Name of this agent (e.g., 'profile_agent')
            memory_type: Type of memory this agent manages (e.g., 'profile')
            llm_client: LLM client for processing conversations
            memory_dir: Directory to store memory files
            use_database: Whether to use database storage
            embedding_client: Embedding client for vector generation
            **db_kwargs: Database connection parameters
        """
        self.agent_name = agent_name
        self.memory_type = memory_type
        self.llm_client = llm_client
        self.memory_dir = Path(memory_dir)
        self.use_database = use_database
        
        # Initialize storage manager
        if use_database:
            self.storage_manager = MemoryDatabaseManager(**db_kwargs)
            
            # Setup embedding client
            if embedding_client:
                self.storage_manager.set_embedding_client(embedding_client)
            else:
                default_embedding = get_default_embedding_client()
                if default_embedding:
                    self.storage_manager.set_embedding_client(default_embedding)
                    logger.info(f"{self.agent_name}: Using default embedding client")
                else:
                    logger.warning(f"{self.agent_name}: No embedding client configured")
        else:
            self.storage_manager = MemoryFileManager(memory_dir)
        
        # Initialize prompt loader
        prompts_dir = Path(__file__).parent.parent / "prompts"
        self.prompt_loader = get_prompt_loader(str(prompts_dir))
        
        logger.info(f"{self.agent_name} initialized with {self.memory_type} memory type")
    
    @abstractmethod
    def get_prompt_template(self) -> str:
        """Get the prompt template for this agent"""
        pass
    
    @abstractmethod
    def get_output_filename(self) -> str:
        """Get the output filename for this agent (e.g., 'profile.md')"""
        pass
    
    @abstractmethod
    def get_dependencies(self) -> List[str]:
        """Get list of dependency files this agent needs (e.g., ['activity.md'])"""
        pass
    
    def process(
        self,
        character_name: str,
        input_content: str,
        session_date: str = "",
        existing_content: Dict[str, str] = None
    ) -> str:
        """
        Process input content and generate memory content for this agent's domain
        
        Args:
            character_name: Name of the character
            input_content: Input content to process (usually activity.md or raw conversation)
            session_date: Date of the session
            existing_content: Existing content from dependency files
            
        Returns:
            Generated content for this agent's memory type
        """
        try:
            if existing_content is None:
                existing_content = {}
            
            # Load existing memory for this type
            current_memory = self.read_memory(character_name)
            
            # Prepare prompt with all necessary context
            prompt = self._prepare_prompt(
                character_name, input_content, session_date, current_memory, existing_content
            )
            
            # Generate new content using LLM
            new_content = self._generate_content(prompt)
            
            # Save the new content
            self.write_memory(character_name, new_content)
            
            # Generate embeddings if using database
            if self.use_database and hasattr(self.storage_manager, 'embedding_client'):
                self._generate_embeddings(character_name, new_content)
            
            logger.info(f"{self.agent_name}: Successfully processed {character_name}")
            return new_content
            
        except Exception as e:
            logger.error(f"{self.agent_name}: Failed to process {character_name}: {e}")
            raise
    
    def read_memory(self, character_name: str) -> str:
        """Read existing memory content for this agent's type"""
        try:
            if hasattr(self.storage_manager, 'read_memory_file'):
                # Use memory type without .md extension for file manager
                return self.storage_manager.read_memory_file(character_name, self.memory_type)
            else:
                # Fallback to specific methods
                method_name = f"read_{self.memory_type}"
                if hasattr(self.storage_manager, method_name):
                    return getattr(self.storage_manager, method_name)(character_name)
                else:
                    logger.warning(f"No read method available for {self.memory_type}")
                    return ""
        except Exception as e:
            logger.warning(f"{self.agent_name}: Failed to read memory for {character_name}: {e}")
            return ""
    
    def write_memory(self, character_name: str, content: str) -> bool:
        """Write memory content for this agent's type"""
        try:
            if hasattr(self.storage_manager, 'write_memory_file'):
                # Use memory type without .md extension for file manager
                return self.storage_manager.write_memory_file(character_name, self.memory_type, content)
            else:
                # Fallback to specific methods
                method_name = f"write_{self.memory_type}"
                if hasattr(self.storage_manager, method_name):
                    return getattr(self.storage_manager, method_name)(character_name, content)
                else:
                    logger.error(f"No write method available for {self.memory_type}")
                    return False
        except Exception as e:
            logger.error(f"{self.agent_name}: Failed to write memory for {character_name}: {e}")
            return False
    
    def append_memory(self, character_name: str, content: str) -> bool:
        """Append content to existing memory for this agent's type"""
        try:
            if hasattr(self.storage_manager, 'append_memory_file'):
                # Use memory type without .md extension for file manager
                return self.storage_manager.append_memory_file(character_name, self.memory_type, content)
            else:
                # Fallback: read existing, append, and write back
                existing = self.read_memory(character_name)
                if existing:
                    new_content = existing + "\n\n" + content
                else:
                    new_content = content
                return self.write_memory(character_name, new_content)
        except Exception as e:
            logger.error(f"{self.agent_name}: Failed to append memory for {character_name}: {e}")
            return False
    
    def search_memory(self, character_name: str, query: str, limit: int = 5) -> List[Dict]:
        """Search memory content using semantic similarity (if available)"""
        try:
            if (self.use_database and 
                hasattr(self.storage_manager, 'search_memories') and 
                hasattr(self.storage_manager, 'embedding_client')):
                return self.storage_manager.search_memories(character_name, query, limit)
            else:
                # Fallback to simple text search
                content = self.read_memory(character_name)
                if query.lower() in content.lower():
                    return [{"content": content, "similarity": 1.0, "type": self.memory_type}]
                return []
        except Exception as e:
            logger.error(f"{self.agent_name}: Failed to search memory for {character_name}: {e}")
            return []
    
    def _prepare_prompt(
        self,
        character_name: str,
        input_content: str,
        session_date: str,
        current_memory: str,
        existing_content: Dict[str, str]
    ) -> str:
        """Prepare the prompt for LLM processing"""
        prompt_template = self.get_prompt_template()
        
        # Prepare base variables
        prompt_vars = {
            "character_name": character_name,
            "conversation": input_content,  # For backward compatibility
            "input_content": input_content,
            "session_date": session_date or datetime.now().strftime("%Y-%m-%d"),
            "current_memory": current_memory,
        }
        
        # Add existing content
        prompt_vars.update(existing_content)
        
        # Add common expected variables with fallbacks
        expected_vars = {
            "existing_profile": existing_content.get("profile", ""),
            "existing_events": existing_content.get("event", ""),  # Fixed: use singular form
            "existing_reminders": existing_content.get("reminder", ""),  # Fixed: use singular form
            "existing_interests": existing_content.get("interests", ""),
            "existing_study": existing_content.get("study", ""),
            "events": existing_content.get("event", ""),  # Fixed: use singular form
            "profile": existing_content.get("profile", "")  # Some prompts use 'profile' directly
        }
        prompt_vars.update(expected_vars)
        
        # Format the prompt with all variables
        try:
            formatted_prompt = prompt_template.format(**prompt_vars)
        except KeyError as e:
            # Handle missing variables gracefully
            missing_var = str(e).strip("'")
            logger.warning(f"{self.agent_name}: Missing variable '{missing_var}' in prompt, using empty string")
            prompt_vars[missing_var] = ""
            formatted_prompt = prompt_template.format(**prompt_vars)
        
        return formatted_prompt
    
    def _generate_content(self, prompt: str) -> str:
        """Generate content using LLM"""
        try:
            messages = [{"role": "user", "content": prompt}]
            response = self.llm_client.chat_completion(messages)
            
            if response.success:
                return response.content.strip()
            else:
                raise Exception(f"LLM call failed: {response.error}")
                
        except Exception as e:
            logger.error(f"{self.agent_name}: LLM generation failed: {e}")
            raise
    
    def _generate_embeddings(self, character_name: str, content: str):
        """Generate embeddings for the content"""
        try:
            if hasattr(self.storage_manager, 'add_memory_with_embedding'):
                self.storage_manager.add_memory_with_embedding(
                    character_name=character_name,
                    content=content,
                    memory_type=self.memory_type,
                    metadata={
                        "agent": self.agent_name,
                        "filename": self.get_output_filename(),
                        "session_date": datetime.now().isoformat()
                    }
                )
                logger.debug(f"{self.agent_name}: Generated embeddings for {character_name}")
        except Exception as e:
            logger.error(f"{self.agent_name}: Failed to generate embeddings: {e}")
            # Don't fail the whole process for embedding errors
    
    def get_priority(self) -> int:
        """Get the execution priority for this agent (higher = earlier)"""
        # Default priority mapping
        priority_map = {
            "activity_agent": 10,
            "profile_agent": 5,
            "event_agent": 4,
            "reminder_agent": 3,
            "interest_agent": 2,
            "study_agent": 1
        }
        return priority_map.get(self.agent_name, 0)
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(name={self.agent_name}, type={self.memory_type})"
    
    def __repr__(self) -> str:
        return self.__str__() 