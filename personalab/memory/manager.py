"""
Memory client module.

Provides unified Memory management interface, integrating Memory, Pipeline and Storage layers:
- MemoryClient: Main Memory client class
- Complete Memory lifecycle management implementation
- LLM integration support
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from .base import Memory
from .pipeline import MemoryUpdatePipeline, PipelineResult
from ..llm import BaseLLMClient
from .storage import MemoryDB


class MemoryClient:
    """
    Memory client.
    
    Provides complete Memory lifecycle management, including:
    - Memory creation, loading, updating, saving
    - Pipeline execution and management
    - Database interaction
    """
    
    def __init__(
        self, 
        db_path: str = "memory.db", 
        **llm_config
    ):
        """
        Initialize MemoryClient.
        
        Args:
            db_path: Database file path
            **llm_config: LLM configuration parameters
        """
        self.database = MemoryDB(db_path)
        self.pipeline = MemoryUpdatePipeline(**llm_config)
    
    def get_memory_by_agent(self, agent_id: str, user_id: str = "default_user") -> Memory:
        """
        Get or create Agent's Memory for a specific user.
        
        Args:
            agent_id: Agent ID
            user_id: User ID, defaults to "default_user"
            
        Returns:
            Memory: Agent's Memory object for the user
        """
        # Try to load existing Memory from database
        existing_memory = self.database.get_memory_by_agent_and_user(agent_id, user_id)
        
        if existing_memory:
            return existing_memory
        
        # Create new Memory
        new_memory = Memory(agent_id=agent_id, user_id=user_id)
        
        # Save to database
        self.database.save_memory(new_memory)
        
        return new_memory
    
    def update_memory_with_conversation(
        self, 
        agent_id: str, 
        user_id: str,
        conversation: List[Dict[str, str]]
    ) -> Tuple[Memory, PipelineResult]:
        """
        Update Memory through conversation.
        
        Args:
            agent_id: Agent ID
            user_id: User ID
            conversation: Conversation content
            
        Returns:
            Tuple[Updated Memory, Pipeline result]
        """
        # 1. Get current Memory
        current_memory = self.get_memory_by_agent(agent_id, user_id)
        
        # 2. Update Memory through LLM Pipeline
        updated_memory, pipeline_result = self.pipeline.update_with_pipeline(
            current_memory, 
            conversation
        )
        
        # 3. Save updated Memory
        self.database.save_memory(updated_memory)
        
        return updated_memory, pipeline_result
    

    
    def get_memory_prompt(self, agent_id: str, user_id: str = "default_user") -> str:
        """
        Get Agent's Memory prompt for a specific user.
        
        Args:
            agent_id: Agent ID
            user_id: User ID, defaults to "default_user"
            
        Returns:
            str: Formatted Memory prompt
        """
        memory = self.get_memory_by_agent(agent_id, user_id)
        return memory.to_prompt()
    
    def update_profile(self, agent_id: str, user_id: str, profile_info: str) -> bool:
        """
        Directly update profile information.
        
        Args:
            agent_id: Agent ID
            user_id: User ID
            profile_info: Profile information
            
        Returns:
            bool: Whether update was successful
        """
        try:
            memory = self.get_memory_by_agent(agent_id, user_id)
            memory.update_profile(profile_info)
            return self.database.save_memory(memory)
        except Exception as e:
            print(f"Error updating profile: {e}")
            return False
    
    def update_events(self, agent_id: str, user_id: str, events: List[str]) -> bool:
        """
        Directly add events.
        
        Args:
            agent_id: Agent ID
            user_id: User ID
            events: Event list
            
        Returns:
            bool: Whether addition was successful
        """
        try:
            memory = self.get_memory_by_agent(agent_id, user_id)
            memory.update_events(events)
            return self.database.save_memory(memory)
        except Exception as e:
            print(f"Error adding events: {e}")
            return False
    
    def get_memory_info(self, agent_id: str, user_id: str = "default_user") -> Dict[str, Any]:
        """
        Get Memory information.
        
        Args:
            agent_id: Agent ID
            user_id: User ID, defaults to "default_user"
            
        Returns:
            Dict: Memory information
        """
        memory = self.get_memory_by_agent(agent_id, user_id)
        
        return {
            'memory_id': memory.memory_id,
            'agent_id': memory.agent_id,
            'user_id': memory.user_id,
            'created_at': memory.created_at.isoformat(),
            'updated_at': memory.updated_at.isoformat(),
            'profile_content_length': len(memory.get_profile_content()),
            'event_count': len(memory.get_event_content()),
            'has_mind_metadata': memory.mind_metadata is not None,
            'confidence_score': memory.mind_metadata.get('confidence_score') if memory.mind_metadata else None
        }
    
    def export_memory(self, agent_id: str, user_id: str = "default_user") -> Dict[str, Any]:
        """
        Export Memory data.
        
        Args:
            agent_id: Agent ID
            user_id: User ID, defaults to "default_user"
            
        Returns:
            Dict: Complete Memory data
        """
        memory = self.get_memory_by_agent(agent_id, user_id)
        return memory.to_dict()
    
    def import_memory(self, memory_data: Dict[str, Any]) -> bool:
        """
        Import Memory data.
        
        Args:
            memory_data: Memory data dictionary
            
        Returns:
            bool: Whether import was successful
        """
        try:
            # Create Memory object
            memory = Memory(
                agent_id=memory_data['agent_id'],
                user_id=memory_data.get('user_id', 'default_user'),
                memory_id=memory_data.get('memory_id')
            )
            
            # Set timestamps
            if 'created_at' in memory_data:
                memory.created_at = datetime.fromisoformat(memory_data['created_at'])
            if 'updated_at' in memory_data:
                memory.updated_at = datetime.fromisoformat(memory_data['updated_at'])
            
            # Set Profile Memory
            if 'profile_memory' in memory_data:
                profile_data = memory_data['profile_memory']
                memory.update_profile(profile_data.get('content', ''))
            
            # Set Event Memory
            if 'event_memory' in memory_data:
                event_data = memory_data['event_memory']
                memory.update_events(event_data.get('content', []))
            
            # Set mind metadata
            if 'mind_metadata' in memory_data:
                memory.mind_metadata = memory_data['mind_metadata']
            elif 'tom_metadata' in memory_data:  # Backward compatibility
                memory.mind_metadata = memory_data['tom_metadata']
            
            # Save to database
            return self.database.save_memory(memory)
            
        except Exception as e:
            print(f"Error importing memory: {e}")
            return False
    
    
    def get_memory_stats(self, agent_id: str) -> Dict[str, Any]:
        """
        Get Memory statistics.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Dict: Statistics information
        """
        return self.database.get_memory_stats(agent_id)
    


 