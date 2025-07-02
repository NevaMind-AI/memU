"""
PersonaLab Persona Class

Provides a clean API for using PersonaLab's Memory and Memo functionality with LLM integration.
"""

from typing import List, Dict, Optional, Union, Any
from contextlib import contextmanager

from ..memory import Memory
from ..memo import Memo
from ..llm import OpenAIClient, AnthropicClient, CustomLLMClient
from ..config import config

class Persona:
    """PersonaLab core interface providing simple memory and conversation functionality
    
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
        
        # Usage
        response = persona.chat("I love hiking")
    """
    
    def __init__(
        self, 
        agent_id: str,
        llm_client=None,
        personality: str = None,
        data_dir: str = "data",
        show_retrieval: bool = False,
        use_memory: bool = True,
        use_memo: bool = True
    ):
        """Initialize Persona
        
        Args:
            agent_id: Agent identifier
            llm_client: LLM client instance (OpenAIClient, AnthropicClient, etc.)
                       If None, will create default OpenAI client
            personality: Personality description for the AI (e.g. "You are a friendly and helpful coding assistant")
                        This will be included in the system prompt to define the AI's character
            data_dir: Data directory for conversation storage
            show_retrieval: Whether to show retrieval process
            use_memory: Whether to enable Memory functionality (long-term memory)
            use_memo: Whether to enable Memo functionality (conversation recording & retrieval)
            
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
            
            # Usage with different users
            response1 = persona.chat("Hello", user_id="user123")
            response2 = persona.chat("Hi there", user_id="user456")
        """
        self.agent_id = agent_id
        self.personality = personality
        self.show_retrieval = show_retrieval
        self.use_memory = use_memory
        self.use_memo = use_memo
        self.data_dir = data_dir
        
        # Session conversation buffers for different users
        self.session_conversations = {}  # user_id -> conversations
        
        # Memory and Memo instances will be created per user as needed
        self.memories = {}  # user_id -> Memory instance
        self.memos = {}     # user_id -> Memo instance
        
        # Configure LLM client
        if llm_client is not None:
            self.llm_client = llm_client
        else:
            # Default to OpenAI client with environment configuration
            self.llm_client = self._create_default_openai_client()
    
    def _create_default_openai_client(self):
        """Create default OpenAI client using environment configuration"""
        try:
            from ..config import get_llm_config_manager
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
        

    def chat(self, message: str, learn: bool = True, user_id: str = "default_user") -> str:
        """Chat with AI, automatically retrieving relevant memories
        
        Note: Memory updates are deferred until endsession() is called.
        Conversations are stored in session buffer when learn=True.
        
        Args:
            message: User message
            learn: Whether to record conversation for later memory update
            user_id: User identifier
            
        Returns:
            AI response
        """
        # 1. Retrieve relevant conversations (if memo is enabled)
        retrieved_conversations = []
        memo = self._get_or_create_memo(user_id)
        if memo and memo.conversations:
            search_results = memo.search_similar_conversations(message, top_k=3)
            retrieved_conversations = search_results
            
            if self.show_retrieval and retrieved_conversations:
                print(f"\n🔍 Retrieved {len(retrieved_conversations)} relevant conversations:")
                for i, conv in enumerate(retrieved_conversations, 1):
                    print(f"  {i}. {conv['summary'][:50]}...")
                print()
        
        # 2. Build message with retrieved content
        enhanced_message = message
        if retrieved_conversations:
            context = "\n".join([
                f"Related history: {conv['summary']}" 
                for conv in retrieved_conversations
            ])
            enhanced_message = f"{message}\n\nRelevant context:\n{context}"
        
        # 3. Get memory context (if memory is enabled)
        memory_context = self._get_memory_context(user_id)
        
        # 4. Build system prompt
        system_prompt_parts = []
        
        # Add personality if provided
        if self.personality:
            system_prompt_parts.append(self.personality)
        else:
            system_prompt_parts.append("You are a helpful AI assistant.")
        
        # Add memory context if available
        if memory_context:
            system_prompt_parts.append("You have long-term memory about the user:")
            system_prompt_parts.append(memory_context)
            system_prompt_parts.append("Please provide personalized responses based on your knowledge of the user.")
        
        system_prompt = "\n\n".join(system_prompt_parts)
        
        # 5. Call LLM
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": enhanced_message}
        ]
        response = self.llm_client.chat_completion(messages)
        
        # 6. Record conversation for potential batch update (if learn=True)
        if learn:
            # Record conversation to memo (if memo is enabled)
            if memo:
                memo.add_conversation(message, response.content)
            
            # Store conversation in session buffer for later memory update
            self.session_conversations.setdefault(user_id, []).append({
                'user_message': message,
                'ai_response': response.content
            })
        
        return response.content

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search for relevant memories"""
        if not self.use_memo or not self.memos.get("default_user"):
            print("⚠️ Memo functionality is not enabled, cannot perform search")
            return []
        return self.memos["default_user"].search_similar_conversations(query, top_k=top_k)
    
    def add_memory(self, content: str, memory_type: str = "profile", user_id: str = "default_user") -> None:
        """Add memory
        
        Args:
            content: Memory content to add
            memory_type: Type of memory - 'profile', 'event', or 'mind'
            user_id: User identifier
        """
        memory = self._get_or_create_memory(user_id)
        if not memory:
            print(f"⚠️ Memory functionality is not enabled for user {user_id}, cannot add memory")
            return
            
        if memory_type == "profile":
            memory.add_profile([content])
        elif memory_type == "event":
            memory.add_events([content])
        elif memory_type == "mind":
            memory.add_mind([content])
        else:
            raise ValueError(f"Unsupported memory_type: {memory_type}. Supported types: 'profile', 'event', 'mind'")
    
    def endsession(self, user_id: str = "default_user") -> Dict[str, int]:
        """End conversation session and update memory with all conversations from this session
        
        Returns:
            Dict with counts of updated memory items
        """
        memory = self._get_or_create_memory(user_id)
        if not memory:
            print(f"⚠️ Memory functionality is not enabled for user {user_id}, cannot update memory")
            self.session_conversations.setdefault(user_id, []).clear()  # Clear buffer even if memory is disabled
            return {"events": 0}
        
        if not self.session_conversations.get(user_id):
            print(f"📝 No conversations to process in this session for user {user_id}")
            return {"events": 0}
        
        # Process all conversations in the session
        events_to_add = []
        for conv in self.session_conversations[user_id]:
            conversation_event = f"User: {conv['user_message']} | AI: {conv['ai_response']}"
            events_to_add.append(conversation_event)
        
        # Batch update memory
        if events_to_add:
            memory.add_events(events_to_add)
            print(f"✅ Session ended: {len(events_to_add)} conversations added to memory for user {user_id}")
        
        # Clear session buffer
        processed_count = len(self.session_conversations[user_id])
        self.session_conversations[user_id].clear()
        
        return {"events": processed_count}
    
    def get_session_info(self, user_id: str = "default_user") -> Dict[str, int]:
        """Get information about the current session
        
        Returns:
            Dict with session information
        """
        return {
            "pending_conversations": len(self.session_conversations.get(user_id, [])),
            "memory_enabled": bool(self.use_memory and self.memories.get(user_id)),
            "memo_enabled": bool(self.use_memo and self.memos.get(user_id))
        }
    
    def get_memory(self, user_id: str = "default_user") -> Dict:
        """Get all memories"""
        memory = self._get_or_create_memory(user_id)
        if not memory:
            print(f"⚠️ Memory functionality is not enabled for user {user_id}, cannot get memory")
            return {"profile": [], "events": [], "mind": []}
            
        return {
            "profile": memory.get_profile(),
            "events": memory.get_events(),
            "mind": memory.get_mind()
        }
    
    def close(self) -> None:
        """Close all resources"""
        # Automatically end session and update memory before closing
        for user_id, conversations in self.session_conversations.items():
            if conversations:
                self.endsession(user_id)
            
        for user_id, memory in self.memories.items():
            if memory:
                memory.close()
        for user_id, memo in self.memos.items():
            if memo:
                memo.close()
        if hasattr(self.llm_client, 'close'):
            self.llm_client.close()
    
    @contextmanager
    def session(self, user_id: str = "default_user"):
        """Context manager for automatic resource management"""
        try:
            yield self
        finally:
            self.close()
    
    # Internal methods
    def _get_or_create_memory(self, user_id: str):
        """Get or create Memory instance for a user"""
        if not self.use_memory:
            return None
            
        if user_id not in self.memories:
            self.memories[user_id] = Memory(agent_id=self.agent_id, user_id=user_id)
        return self.memories[user_id]
    
    def _get_or_create_memo(self, user_id: str):
        """Get or create Memo instance for a user"""
        if not self.use_memo:
            return None
            
        if user_id not in self.memos:
            self.memos[user_id] = Memo(agent_id=self.agent_id, user_id=user_id, data_dir=self.data_dir)
        return self.memos[user_id]
    
    def _get_memory_context(self, user_id: str = "default_user") -> str:
        """Get memory context"""
        memory = self._get_or_create_memory(user_id)
        if not memory:
            return ""
            
        context_parts = []
        
        profile = memory.get_profile()
        if profile:
            context_parts.append(f"User profile: {', '.join(profile)}")
        
        events = memory.get_events()
        if events:
            context_parts.append(f"Important events: {', '.join(events)}")
        
        mind = memory.get_mind()
        if mind:
            context_parts.append(f"Psychological insights: {', '.join(mind)}")
        
        return "\n".join(context_parts) if context_parts else ""
    
