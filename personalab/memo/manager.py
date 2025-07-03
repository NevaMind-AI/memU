"""
Conversation management module.

Provides high-level interface for conversation recording, retrieval, and semantic search.
Uses PostgreSQL backend with pgvector for vector operations.
"""

from typing import Any, Dict, List, Optional, Tuple

from ..config.database import DatabaseManager, get_database_manager
from .embeddings import create_embedding_manager
from .models import Conversation, ConversationMessage


class ConversationManager:
    """
    High-level conversation management interface with PostgreSQL backend.

    Provides unified interface for:
    - Conversation recording and storage
    - Conversation retrieval and history
    - Vector embeddings and semantic search with PostgreSQL + pgvector
    - Integration with memory system
    """

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        enable_embeddings: bool = True,
        embedding_provider: str = "auto",
    ):
        """
        Initialize ConversationManager.

        Args:
            db_manager: Database manager instance. If None, the global PostgreSQL manager will be used.
            enable_embeddings: Whether to enable embedding generation
            embedding_provider: Type of embedding provider ('auto', 'openai', 'sentence-transformers')
        """
        # Use provided database manager or fallback to global one (PostgreSQL-only)
        self.db_manager = db_manager or get_database_manager()

        self.db = self.db_manager.get_conversation_db()
        self.enable_embeddings = enable_embeddings

        # Initialize embedding manager
        if enable_embeddings:
            self.embedding_manager = create_embedding_manager(embedding_provider)
        else:
            self.embedding_manager = None

    def record_conversation(
        self,
        agent_id: str,
        user_id: str,
        messages: List[Dict[str, str]],
        session_id: Optional[str] = None,
        memory_id: Optional[str] = None,
        pipeline_result: Optional[Dict[str, Any]] = None,
        enable_vectorization: bool = True,
    ) -> Conversation:
        """
        Record a conversation with optional embedding generation.

        Args:
            agent_id: Agent ID (REQUIRED)
            user_id: User identifier (REQUIRED)
            messages: List of conversation messages
            session_id: Session identifier (optional)
            memory_id: Associated memory ID (optional)
            pipeline_result: Pipeline execution results (optional)
            enable_vectorization: Whether to generate embeddings

        Returns:
            Conversation: Recorded conversation object
        """
        # Validate required parameters
        if not agent_id:
            raise ValueError("agent_id is required")
        if not user_id:
            raise ValueError("user_id is required")

        # Create conversation object
        conversation = Conversation(
            agent_id=agent_id,
            user_id=user_id,
            messages=messages,
            session_id=session_id,
            memory_id=memory_id,
            pipeline_result=pipeline_result,
        )

        # Save to database
        success = self.db.save_conversation(conversation)
        if not success:
            raise RuntimeError("Failed to save conversation to database")

        # Generate embeddings if enabled
        if enable_vectorization and self.enable_embeddings and self.embedding_manager:
            self._generate_conversation_embeddings(conversation)

        return conversation

    def _generate_conversation_embeddings(self, conversation: Conversation):
        """Generate and save embeddings for conversation and messages."""
        try:
            # Generate conversation-level embedding
            conv_text = conversation.get_conversation_text()
            conv_embedding = self.embedding_manager.provider.generate_embedding(
                conv_text
            )

            # Save conversation embedding directly in conversation table
            if hasattr(self.db, "save_conversation_embedding"):
                self.db.save_conversation_embedding(
                    conversation.conversation_id, conv_embedding, conv_text
                )

            # Generate message-level embeddings for substantial messages
            for message in conversation.messages:
                if len(message.content) > 20:  # Only embed substantial messages
                    msg_embedding = self.embedding_manager.provider.generate_embedding(
                        message.content
                    )

                    # Save message embedding directly in message table
                    if hasattr(self.db, "save_message_embedding"):
                        self.db.save_message_embedding(
                            message.message_id, msg_embedding
                        )

        except Exception as e:
            print(f"Error generating embeddings: {e}")

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """
        Get conversation by ID.

        Args:
            conversation_id: Conversation ID

        Returns:
            Conversation: Conversation object or None
        """
        return self.db.get_conversation(conversation_id)

    def get_conversation_history(
        self,
        agent_id: str,
        limit: int = 20,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get conversation history for an agent.

        Args:
            agent_id: Agent ID
            limit: Maximum number of conversations
            session_id: Filter by session ID (optional)
            user_id: Filter by user ID (optional)

        Returns:
            List[Dict]: Conversation history summaries
        """
        return self.db.get_conversations_by_agent(agent_id, limit, session_id, user_id)

    def search_similar_conversations(
        self,
        agent_id: str,
        query: str,
        limit: int = 10,
        similarity_threshold: float = 0.7,
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
            print("Embeddings not enabled. Search functionality is not available.")
            return []

        try:
            # Generate query embedding
            query_embedding = self.embedding_manager.provider.generate_embedding(query)

            # Search using conversation vectors
            if hasattr(self.db, "search_similar_conversations"):
                similar_conversations = self.db.search_similar_conversations(
                    agent_id=agent_id,
                    query_vector=query_embedding,
                    limit=limit,
                    similarity_threshold=similarity_threshold,
                )

                # Convert to expected format
                results = []
                for conv in similar_conversations:
                    results.append(
                        {
                            "conversation_id": conv["conversation_id"],
                            "agent_id": conv["agent_id"],
                            "created_at": (
                                conv["created_at"].isoformat()
                                if hasattr(conv["created_at"], "isoformat")
                                else conv["created_at"]
                            ),
                            "summary": conv.get("summary"),
                            "session_id": conv.get("session_id"),
                            "turn_count": conv.get("turn_count"),
                            "similarity_score": conv["similarity_score"],
                            "matched_content": f"Conversation from {conv['created_at']}",
                        }
                    )

                return results
            else:
                # Database doesn't support direct conversation vector search
                print("Vector search not supported by current database configuration")
                return []

        except Exception as e:
            print(f"Error in semantic search: {e}")
            return []

    def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete conversation and its embeddings.

        Args:
            conversation_id: Conversation ID

        Returns:
            bool: Whether deletion was successful
        """
        return self.db.delete_conversation(conversation_id)

    def get_session_conversations(
        self,
        agent_id: str,
        session_id: str,
        limit: int = 50,
        user_id: Optional[str] = None,
    ) -> List[Conversation]:
        """
        Get all conversations for a specific session.

        Args:
            agent_id: Agent ID
            session_id: Session ID
            limit: Maximum conversations to return
            user_id: Filter by user ID (optional)

        Returns:
            List[Conversation]: List of conversation objects
        """
        conv_summaries = self.db.get_conversations_by_agent(
            agent_id, limit, session_id, user_id
        )

        conversations = []
        for summary in conv_summaries:
            conversation = self.db.get_conversation(summary["conversation_id"])
            if conversation:
                conversations.append(conversation)

        return conversations

    def get_conversation_stats(self, agent_id: str) -> Dict[str, Any]:
        """
        Get conversation statistics for an agent.

        Args:
            agent_id: Agent ID

        Returns:
            Dict: Statistics about conversations
        """
        # Get recent conversations to calculate stats
        recent_convs = self.db.get_conversations_by_agent(agent_id, limit=100)

        if not recent_convs:
            return {
                "total_conversations": 0,
                "total_sessions": 0,
                "total_turns": 0,
                "embedding_enabled": self.enable_embeddings,
                "embedding_model": (
                    self.embedding_manager.model_name
                    if self.embedding_manager
                    else None
                ),
            }

        # Calculate statistics
        total_turns = sum(conv["turn_count"] for conv in recent_convs)
        unique_sessions = len(set(conv["session_id"] for conv in recent_convs))

        return {
            "total_conversations": len(recent_convs),
            "total_sessions": unique_sessions,
            "total_turns": total_turns,
            "average_turns_per_conversation": total_turns / len(recent_convs),
            "embedding_enabled": self.enable_embeddings,
            "embedding_model": (
                self.embedding_manager.model_name if self.embedding_manager else None
            ),
            "most_recent_conversation": (
                recent_convs[0]["created_at"] if recent_convs else None
            ),
        }

    def close(self):
        """Close database connections."""
        self.db.close()
