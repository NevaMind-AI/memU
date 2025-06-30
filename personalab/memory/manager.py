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
from ..llm import BaseLLMClient, create_llm_client
from .storage import MemoryDB
from .embeddings import EmbeddingManager, create_embedding_manager


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
        enable_embeddings: bool = True,
        embedding_provider: str = "auto",
        **llm_config
    ):
        """
        Initialize MemoryClient.
        
        Args:
            db_path: Database file path
            enable_embeddings: Whether to enable vector embeddings
            embedding_provider: Type of embedding provider ('auto', 'openai', 'sentence-transformers', 'simple')
            **llm_config: LLM configuration parameters
        """
        self.database = MemoryDB(db_path)
        self.pipeline = MemoryUpdatePipeline(**llm_config)
        
        # Initialize embedding manager
        self.enable_embeddings = enable_embeddings
        if enable_embeddings:
            self.embedding_manager = create_embedding_manager(embedding_provider)
        else:
            self.embedding_manager = None
    
    def get_memory_by_agent(self, agent_id: str) -> Memory:
        """
        Get or create Agent's Memory.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Memory: Agent's Memory object
        """
        # Try to load existing Memory from database
        existing_memory = self.database.get_memory_by_agent(agent_id)
        
        if existing_memory:
            return existing_memory
        
        # Create new Memory
        new_memory = Memory(agent_id=agent_id)
        
        # Save to database
        self.database.save_memory(new_memory)
        
        return new_memory
    
    def update_memory_with_conversation(
        self, 
        agent_id: str, 
        conversation: List[Dict[str, str]],
        session_id: Optional[str] = None,
        enable_vectorization: bool = True
    ) -> Tuple[Memory, PipelineResult]:
        """
        Update Memory through conversation with recording and vectorization.
        
        Args:
            agent_id: Agent ID
            conversation: Conversation content
            session_id: Session identifier (optional)
            enable_vectorization: Whether to generate embeddings
            
        Returns:
            Tuple[Updated Memory, Pipeline result]
        """
        # 1. Get current Memory
        current_memory = self.get_memory_by_agent(agent_id)
        
        # 2. Update Memory through LLM Pipeline
        updated_memory, pipeline_result = self.pipeline.update_with_pipeline(
            current_memory, 
            conversation
        )
        
        # 3. Save updated Memory
        self.database.save_memory(updated_memory)
        
        # 4. Record conversation in database
        conversation_id = self.database.save_conversation(
            agent_id=agent_id,
            conversation=conversation,
            memory_id=updated_memory.memory_id,
            session_id=session_id,
            pipeline_result=pipeline_result.to_dict() if hasattr(pipeline_result, 'to_dict') else None
        )
        
        # 5. Generate and save embeddings if enabled
        if enable_vectorization and self.enable_embeddings and conversation_id:
            self._generate_conversation_embeddings(
                conversation_id, agent_id, conversation
            )
        
        return updated_memory, pipeline_result
    
    def _generate_conversation_embeddings(
        self, 
        conversation_id: str, 
        agent_id: str, 
        conversation: List[Dict[str, str]]
    ):
        """Generate and save embeddings for conversation and individual messages."""
        if not self.embedding_manager:
            return
        
        try:
            # Generate conversation-level embedding
            conv_embedding = self.embedding_manager.generate_conversation_embedding(conversation)
            conv_text = " ".join([msg.get('content', '') for msg in conversation])
            
            self.database.save_embedding(
                source_type="conversation",
                source_id=conversation_id,
                agent_id=agent_id,
                vector=conv_embedding,
                content_text=conv_text,
                embedding_model=self.embedding_manager.model_name
            )
            
            # Generate message-level embeddings for important messages
            for idx, message in enumerate(conversation):
                if len(message.get('content', '')) > 20:  # Only embed substantial messages
                    msg_embedding = self.embedding_manager.generate_message_embedding(message)
                    message_id = f"{conversation_id}_msg_{idx}"
                    
                    self.database.save_embedding(
                        source_type="message",
                        source_id=message_id,
                        agent_id=agent_id,
                        vector=msg_embedding,
                        content_text=message.get('content', ''),
                        embedding_model=self.embedding_manager.model_name
                    )
        
        except Exception as e:
            print(f"Error generating embeddings: {e}")
    
    def get_memory_prompt(self, agent_id: str) -> str:
        """
        Get Agent's Memory prompt.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            str: Formatted Memory prompt
        """
        memory = self.get_memory_by_agent(agent_id)
        return memory.to_prompt()
    
    def update_profile(self, agent_id: str, profile_info: str) -> bool:
        """
        Directly update profile information.
        
        Args:
            agent_id: Agent ID
            profile_info: Profile information
            
        Returns:
            bool: Whether update was successful
        """
        try:
            memory = self.get_memory_by_agent(agent_id)
            memory.update_profile(profile_info)
            return self.database.save_memory(memory)
        except Exception as e:
            print(f"Error updating profile: {e}")
            return False
    
    def update_events(self, agent_id: str, events: List[str]) -> bool:
        """
        Directly add events.
        
        Args:
            agent_id: Agent ID
            events: Event list
            
        Returns:
            bool: Whether addition was successful
        """
        try:
            memory = self.get_memory_by_agent(agent_id)
            memory.update_events(events)
            return self.database.save_memory(memory)
        except Exception as e:
            print(f"Error adding events: {e}")
            return False
    
    def get_memory_info(self, agent_id: str) -> Dict[str, Any]:
        """
        Get Memory information.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Dict: Memory information
        """
        memory = self.get_memory_by_agent(agent_id)
        
        return {
            'memory_id': memory.memory_id,
            'agent_id': memory.agent_id,
            'created_at': memory.created_at.isoformat(),
            'updated_at': memory.updated_at.isoformat(),
            'profile_content_length': len(memory.get_profile_content()),
            'event_count': len(memory.get_event_content()),
            'has_tom_metadata': memory.tom_metadata is not None,
            'confidence_score': memory.tom_metadata.get('confidence_score') if memory.tom_metadata else None
        }
    
    def export_memory(self, agent_id: str) -> Dict[str, Any]:
        """
        Export Memory data.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Dict: Complete Memory data
        """
        memory = self.get_or_create_memory(agent_id)
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
            
            # Set ToM metadata
            if 'tom_metadata' in memory_data:
                memory.tom_metadata = memory_data['tom_metadata']
            
            # Save to database
            return self.repository.save_memory(memory)
            
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
    
    def search_similar_conversations(
        self,
        agent_id: str,
        query: str,
        limit: int = 10,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Search for similar conversations using semantic similarity.
        
        Args:
            agent_id: Agent ID
            query: Search query text
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score
            
        Returns:
            List[Dict]: Similar conversations with similarity scores
        """
        if not self.enable_embeddings or not self.embedding_manager:
            print("Embeddings not enabled. Using text-based search.")
            return self._text_based_conversation_search(agent_id, query, limit)
        
        try:
            # Generate query embedding
            query_embedding = self.embedding_manager.provider.generate_embedding(query)
            
            # Search for similar conversation embeddings
            similar_vectors = self.database.search_similar_vectors(
                agent_id=agent_id,
                query_vector=query_embedding,
                source_type="conversation",
                limit=limit,
                similarity_threshold=similarity_threshold
            )
            
            # Enrich results with conversation details
            results = []
            for vector_result in similar_vectors:
                conversation_id = vector_result['source_id']
                conversation = self.database.get_conversation(conversation_id)
                
                if conversation:
                    results.append({
                        **conversation,
                        'similarity_score': vector_result['similarity_score'],
                        'matched_content': vector_result['content_text']
                    })
            
            return results
            
        except Exception as e:
            print(f"Error in semantic search: {e}")
            return self._text_based_conversation_search(agent_id, query, limit)
    
    def _text_based_conversation_search(
        self, 
        agent_id: str, 
        query: str, 
        limit: int
    ) -> List[Dict[str, Any]]:
        """Fallback text-based conversation search."""
        conversations = self.database.get_conversations_by_agent(agent_id, limit * 2)
        
        # Simple keyword matching
        query_words = set(query.lower().split())
        scored_conversations = []
        
        for conv in conversations:
            conv_detail = self.database.get_conversation(conv['conversation_id'])
            if not conv_detail:
                continue
            
            # Calculate simple text similarity
            conv_text = " ".join([msg['content'] for msg in conv_detail['messages']]).lower()
            conv_words = set(conv_text.split())
            
            # Jaccard similarity
            intersection = len(query_words.intersection(conv_words))
            union = len(query_words.union(conv_words))
            similarity = intersection / union if union > 0 else 0
            
            if similarity > 0.1:  # Basic threshold
                scored_conversations.append({
                    **conv_detail,
                    'similarity_score': similarity,
                    'matched_content': conv_text[:200]
                })
        
        # Sort by similarity and return top results
        scored_conversations.sort(key=lambda x: x['similarity_score'], reverse=True)
        return scored_conversations[:limit]
    
    def get_conversation_history(
        self,
        agent_id: str,
        limit: int = 20,
        session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get conversation history for an agent.
        
        Args:
            agent_id: Agent ID
            limit: Maximum number of conversations
            session_id: Filter by session ID
            
        Returns:
            List[Dict]: Conversation history
        """
        return self.database.get_conversations_by_agent(agent_id, limit, session_id)
    
    def get_conversation_detail(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed conversation by ID.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Dict: Conversation details or None
        """
        return self.database.get_conversation(conversation_id)

 