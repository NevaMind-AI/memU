"""
Data models for conversation recording and management.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ConversationMessage:
    """Individual message within a conversation."""

    message_id: str
    role: str  # 'user', 'assistant', 'system'
    content: str
    message_index: int
    created_at: datetime

    def __init__(
        self,
        role: str,
        content: str,
        message_index: int,
        message_id: Optional[str] = None,
        created_at: Optional[datetime] = None,
    ):
        self.message_id = message_id or str(uuid.uuid4())
        self.role = role
        self.content = content
        self.message_index = message_index
        self.created_at = created_at or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "message_id": self.message_id,
            "role": self.role,
            "content": self.content,
            "message_index": self.message_index,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationMessage":
        """Create from dictionary format."""
        return cls(
            role=data["role"],
            content=data["content"],
            message_index=data["message_index"],
            message_id=data.get("message_id"),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if "created_at" in data
                else None
            ),
        )


@dataclass
class Conversation:
    """Complete conversation with metadata and messages."""

    conversation_id: str
    agent_id: str
    user_id: str  # REQUIRED: User identifier for conversation filtering
    session_id: str
    created_at: datetime
    messages: List[ConversationMessage]
    memory_id: Optional[str] = None
    pipeline_result: Optional[Dict[str, Any]] = None
    summary: Optional[str] = None

    def __init__(
        self,
        agent_id: str,
        user_id: str,  # REQUIRED: User identifier
        messages: List[Dict[str, str]] = None,
        session_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        created_at: Optional[datetime] = None,
        memory_id: Optional[str] = None,
        pipeline_result: Optional[Dict[str, Any]] = None,
    ):
        # Validate required fields
        if not agent_id:
            raise ValueError("agent_id is required")
        if not user_id:
            raise ValueError("user_id is required")

        self.conversation_id = conversation_id or str(uuid.uuid4())
        self.agent_id = agent_id
        self.user_id = user_id
        self.session_id = session_id or str(uuid.uuid4())
        self.created_at = created_at or datetime.now()  # created_at is always set
        self.memory_id = memory_id
        self.pipeline_result = pipeline_result

        # Convert message dicts to ConversationMessage objects
        self.messages = []
        if messages:
            for idx, msg_data in enumerate(messages):
                if isinstance(msg_data, dict):
                    message = ConversationMessage(
                        role=msg_data.get("role", "unknown"),
                        content=msg_data.get("content", ""),
                        message_index=idx,
                    )
                    self.messages.append(message)
                elif isinstance(msg_data, ConversationMessage):
                    self.messages.append(msg_data)

        # Generate summary
        self.summary = self._generate_summary()

    def _generate_summary(self) -> str:
        """Generate a simple summary of the conversation."""
        if not self.messages:
            return "Empty conversation"

        # Find first user message
        first_user_msg = next(
            (msg.content[:100] for msg in self.messages if msg.role == "user"),
            "No user message",
        )

        return f"Conversation with {len(self.messages)} turns: {first_user_msg}..."

    @property
    def turn_count(self) -> int:
        """Get the number of conversation turns."""
        return len(self.messages)

    def get_conversation_text(self) -> str:
        """Get all conversation content as formatted text."""
        text_parts = []
        for message in self.messages:
            text_parts.append(f"{message.role}: {message.content}")
        return "\n".join(text_parts)

    def get_message_contents(self) -> List[str]:
        """Get list of message contents only."""
        return [msg.content for msg in self.messages]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "conversation_id": self.conversation_id,
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "messages": [msg.to_dict() for msg in self.messages],
            "user_id": self.user_id,
            "memory_id": self.memory_id,
            "pipeline_result": self.pipeline_result,
            "summary": self.summary,
            "turn_count": self.turn_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Conversation":
        """Create from dictionary format."""
        messages = [
            ConversationMessage.from_dict(msg_data)
            for msg_data in data.get("messages", [])
        ]

        # Validate required fields in data
        if "agent_id" not in data:
            raise ValueError("agent_id is required in data")
        if "user_id" not in data:
            raise ValueError("user_id is required in data")

        conversation = cls(
            agent_id=data["agent_id"],
            user_id=data["user_id"],
            messages=[],  # Will be set below
            session_id=data.get("session_id"),
            conversation_id=data.get("conversation_id"),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if "created_at" in data
                else None
            ),
            memory_id=data.get("memory_id"),
            pipeline_result=data.get("pipeline_result"),
        )

        conversation.messages = messages
        conversation.summary = data.get("summary", conversation._generate_summary())

        return conversation

    def to_memory_format(self) -> List[Dict[str, str]]:
        """Convert to format expected by memory system."""
        return [{"role": msg.role, "content": msg.content} for msg in self.messages]
