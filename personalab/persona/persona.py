"""
PersonaLab Persona Class

Provides a clean API for using PersonaLab's Memory functionality with LLM integration.
All memory operations are performed through remote API calls.
"""

from contextlib import contextmanager
from typing import Dict, List
import requests
import json

from ..config import get_llm_config_manager
from ..llm import OpenAIClient
from ..memory import MemoryClient


class Persona:
    """PersonaLab core interface providing simple memory and conversation functionality

    All memory operations are performed through remote API calls.
    Architecture: Client -> API -> Backend -> Database

    The main parameter is `llm_client` - pass any LLM client instance you want to use.
    If no llm_client is provided, uses OpenAI by default (reading API key from .env file).
    Use `personality` parameter to define the AI's character and behavior.

    Usage Examples:
        from personalab import Persona
        from personalab.llm import OpenAIClient, AnthropicClient

        # Method 1: Pass llm_client directly
        openai_client = OpenAIClient(api_key="your-key", model="gpt-4")
        persona = Persona(agent_id="alice", llm_client=openai_client)

        anthropic_client = AnthropicClient(api_key="your-key")
        persona = Persona(agent_id="bob", llm_client=anthropic_client)

        # Method 2: Use default OpenAI (reads from .env)
        persona = Persona(agent_id="charlie")

        # Method 3: Add personality
        persona = Persona(
            agent_id="coding_assistant",
            personality="You are a friendly and patient Python programming tutor. "
                       "You explain concepts clearly and provide practical examples."
        )

        # Method 4: Specify custom API URL
        persona = Persona(
            agent_id="remote_assistant",
            api_url="http://remote-server:8000"
        )

        # Usage
        response = persona.chat("I love hiking", user_id="user123")
    """

    def __init__(
        self,
        agent_id: str,
        llm_client=None,
        personality: str = None,
        api_url: str = "http://localhost:8000",
        show_retrieval: bool = False,
        use_memory: bool = True,
        timeout: int = 30,
    ):
        """Initialize Persona

        Args:
            agent_id: Agent identifier
            llm_client: LLM client instance (OpenAIClient, AnthropicClient, etc.)
                       If None, will create default OpenAI client
            personality: Personality description for the AI (e.g. "You are a friendly and helpful coding assistant")
                        This will be included in the system prompt to define the AI's character
            api_url: Remote API URL for memory operations (default: "http://localhost:8000")
            show_retrieval: Whether to show retrieval process
            use_memory: Whether to enable Memory functionality (long-term memory)
            timeout: Request timeout in seconds for API calls

        Example:
            from personalab import Persona
            from personalab.llm import OpenAIClient, AnthropicClient

            # Using OpenAI
            openai_client = OpenAIClient(api_key="your-key", model="gpt-4")
            persona = Persona(agent_id="alice", llm_client=openai_client)

            # Using Anthropic
            anthropic_client = AnthropicClient(api_key="your-key")
            persona = Persona(agent_id="bob", llm_client=anthropic_client)

            # Default OpenAI (reads from .env)
            persona = Persona(agent_id="charlie")  # Uses default OpenAI client

            # With personality
            persona = Persona(
                agent_id="tutor",
                personality="You are a supportive math tutor who makes learning fun."
            )

            # Custom API server
            persona = Persona(
                agent_id="remote_assistant",
                api_url="http://remote-server:8000"
            )

            # Usage with different users
            response1 = persona.chat("Hello", user_id="user123")
            response2 = persona.chat("Hi there", user_id="user456")
        """
        self.agent_id = agent_id
        self.personality = personality
        self.show_retrieval = show_retrieval
        self.use_memory = use_memory
        self.api_url = api_url.rstrip('/') if api_url else "http://localhost:8000"

        # Initialize Memory client (API-only)
        if self.use_memory:
            self.memory_client = MemoryClient(agent_id=self.agent_id, api_url=self.api_url, timeout=timeout)
        else:
            self.memory_client = None

        # Session conversation buffers for different users
        self.session_conversations = {}  # user_id -> conversations

        # Memory instances will be created per user as needed
        self.memories = {}  # user_id -> Memory instance

        # Configure LLM client
        if llm_client is not None:
            self.llm_client = llm_client
        else:
            # Default to OpenAI client with environment configuration
            self.llm_client = self._create_default_openai_client()

    def _create_default_openai_client(self):
        """Create default OpenAI client using environment configuration"""
        try:
            llm_config_manager = get_llm_config_manager()
            openai_config = llm_config_manager.get_provider_config("openai")

            if not openai_config.get("api_key"):
                raise ValueError(
                    "OpenAI API key not found. Please set OPENAI_API_KEY in .env file or "
                    "pass a configured llm_client parameter."
                )

            return OpenAIClient(**openai_config)
        except Exception as e:
            raise ValueError(f"Failed to create default OpenAI client: {e}")

    def chat(self, message: str, user_id: str, learn: bool = True) -> str:
        """Chat with AI, automatically retrieving relevant memories

        Note: Memory updates are deferred until endsession() is called.
        Conversations are stored in session buffer when learn=True.

        Args:
            message: User message
            user_id: User identifier (required)
            learn: Whether to record conversation for later memory update

        Returns:
            AI response
        """
        # 1. Get memory context
        memory_context = self._get_memory_context(user_id)

        # 2. Build system prompt
        system_parts = []
        if self.personality:
            system_parts.append(self.personality)

        if memory_context:
            system_parts.append(f"\nRelevant context about this user:\n{memory_context}")

        system_prompt = "\n".join(system_parts) if system_parts else None

        # 3. Generate response using LLM
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Add session history
        if user_id in self.session_conversations:
            for conv in self.session_conversations[user_id]:
                messages.append({"role": "user", "content": conv["user_message"]})
                messages.append({"role": "assistant", "content": conv["ai_response"]})
        
        messages.append({"role": "user", "content": message})

        response = self.llm_client.chat_completion(messages)
        ai_response = response.content if hasattr(response, 'content') else str(response)

        # 4. Store conversation in session buffer for context continuity
        self.session_conversations.setdefault(user_id, []).append({
            "user_message": message,
            "ai_response": ai_response,
            "learn": learn  # Track whether this conversation should be learned
        })

        return ai_response

    def get_memory(self, user_id: str) -> "Memory":
        """Get memory instance for the specified user
        
        Convenience method that uses the agent_id from this persona.

        Args:
            user_id: User identifier (required)

        Returns:
            Memory instance for this agent and specified user
        """
        if not self.use_memory or not self.memory_client:
            raise ValueError("Memory functionality is not enabled")
        
        return self.memory_client.get_memory(user_id)

    def update_memory(
        self, content: str, user_id: str, memory_type: str = "profile"
    ) -> None:
        """Update memory content via API

        Args:
            content: Content to add
            user_id: User identifier (required)
            memory_type: Type of memory ('profile', 'events')
        """
        if not self.use_memory or not self.memory_client:
            print("⚠️ Memory functionality is not enabled")
            return

        try:
            if memory_type == "profile":
                success = self.memory_client.update_profile(user_id=user_id, profile_info=content)
            elif memory_type == "events":
                success = self.memory_client.update_events(user_id=user_id, events=[content])
            else:
                print(f"⚠️ Unsupported memory type: {memory_type}")
                return

            if success:
                print(f"✅ {memory_type.title()} memory added via API")
                # Clear cached memory to force reload
                if user_id in self.memories:
                    del self.memories[user_id]
            else:
                print(f"❌ Failed to add {memory_type} memory via API")

        except Exception as e:
            print(f"❌ Error adding memory: {e}")

    def endsession(self, user_id: str) -> Dict[str, int]:
        """End conversation session and update memory with all conversations from this session

        Args:
            user_id: User identifier (required)

        Returns:
            Dict with counts of updated memory items
        """
        if not self.use_memory or not self.memory_client:
            print(f"⚠️ Memory functionality is not enabled for user {user_id}")
            self.session_conversations.setdefault(user_id, []).clear()
            return {"events": 0}

        if not self.session_conversations.get(user_id):
            print(f"📝 No conversations to process in this session for user {user_id}")
            return {"events": 0}

        # Convert session conversations to API format (only learn=True conversations)
        conversation = []
        for conv in self.session_conversations[user_id]:
            if conv.get("learn", True):  # Default to True for backward compatibility
                conversation.append({
                    "user_message": conv["user_message"],
                    "ai_response": conv["ai_response"]
                })

        if not conversation:
            print(f"📝 No learnable conversations in this session for user {user_id}")
            self.session_conversations[user_id].clear()
            return {"events": 0}

        print(f"📤 Sending {len(conversation)} conversations to API for processing...")

        try:
            # Update memory via API
            success = self.memory_client.update_memory_with_conversation(
                user_id=user_id, 
                conversation=conversation
            )

            if success:
                print(f"✅ Successfully updated memory with {len(conversation)} conversations")
                
                # Clear session buffer
                self.session_conversations[user_id].clear()
                
                # Clear cached memory to force reload next time
                if user_id in self.memories:
                    del self.memories[user_id]
                
                return {"events": len(conversation)}
            else:
                print(f"❌ Failed to update memory via API")
                return {"events": 0}

        except Exception as e:
            print(f"❌ Error updating memory: {e}")
            return {"events": 0}

    def get_session_info(self, user_id: str) -> Dict[str, int]:
        """Get information about the current session

        Args:
            user_id: User identifier (required)

        Returns:
            Dict with session information
        """
        return {
            "pending_conversations": len(self.session_conversations.get(user_id, [])),
            "memory_enabled": bool(self.use_memory and self.memory_client),
            "memo_enabled": False,  # Memo not supported in API-only mode
        }



    def close(self) -> None:
        """Close all resources"""
        # Automatically end session and update memory before closing
        for user_id, conversations in self.session_conversations.items():
            if conversations:
                self.endsession(user_id)

        # Close memory instances
        for user_id, memory in self.memories.items():
            if memory and hasattr(memory, 'close'):
                memory.close()

        # Close LLM client if it has a close method
        if hasattr(self.llm_client, "close"):
            self.llm_client.close()

    @contextmanager
    def session(self, user_id: str):
        """Context manager for automatic resource management

        Args:
            user_id: User identifier (required)
        """
        try:
            yield self
        finally:
            self.endsession(user_id)

    def _get_or_create_memory(self, user_id: str):
        """Get or create Memory instance for a user"""
        if not self.use_memory or not self.memory_client:
            return None

        if user_id not in self.memories:
            # Use MemoryClient to get memory (API-only)
            memory = self.memory_client.get_memory(user_id)
            self.memories[user_id] = memory

        return self.memories[user_id]

    def _get_memory_context(self, user_id: str) -> str:
        """Get memory context

        Args:
            user_id: User identifier (required)

        Returns:
            Formatted memory context string
        """
        if not self.use_memory or not self.memory_client:
            return ""

        try:
            memory_context = self.memory_client.get_memory_prompt(user_id=user_id)
            return memory_context
        except Exception as e:
            print(f"Warning: Failed to get memory context: {e}")
            return ""
