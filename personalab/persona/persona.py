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
        
        # Method 3: Class methods for convenience
        persona = Persona.create_openai(agent_id="alice")
        persona = Persona.create_anthropic(agent_id="bob")
        
        # Usage
        response = persona.chat("I love hiking")
    """
    
    def __init__(
        self, 
        agent_id: str,
        llm_client=None,
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
        """
        self.agent_id = agent_id
        self.show_retrieval = show_retrieval
        self.use_memory = use_memory
        self.use_memo = use_memo
        
        # Session conversation buffer for batch memory updates
        self.session_conversations = []
        
        # Selectively initialize Memory and Memo based on parameters
        if use_memory:
            self.memory = Memory(agent_id=agent_id)
        else:
            self.memory = None
            
        if use_memo:
            self.memo = Memo(agent_id=agent_id, data_dir=data_dir)
        else:
            self.memo = None
        
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
    

    

    
    @classmethod
    def create_openai(cls, agent_id: str, api_key: str = None, **kwargs) -> 'Persona':
        """Create a Persona instance using OpenAI"""
        if api_key:
            client = OpenAIClient(api_key=api_key)
            return cls(agent_id=agent_id, llm_client=client, **kwargs)
        else:
            # Use default OpenAI configuration
            return cls(agent_id=agent_id, **kwargs)
    
    @classmethod  
    def create_anthropic(cls, agent_id: str, api_key: str = None, **kwargs) -> 'Persona':
        """Create a Persona instance using Anthropic"""
        if api_key:
            client = AnthropicClient(api_key=api_key)
            return cls(agent_id=agent_id, llm_client=client, **kwargs)
        else:
            from ..config import get_llm_config_manager
            llm_config_manager = get_llm_config_manager()
            anthropic_config = llm_config_manager.get_provider_config("anthropic")
            client = AnthropicClient(**anthropic_config)
            return cls(agent_id=agent_id, llm_client=client, **kwargs)
    
    @classmethod
    def create_custom(cls, agent_id: str, llm_function, **kwargs) -> 'Persona':
        """Create a Persona instance using custom LLM function"""
        client = CustomLLMClient(llm_function=llm_function)
        return cls(agent_id=agent_id, llm_client=client, **kwargs)
        

    def chat(self, message: str, learn: bool = True) -> str:
        """Chat with AI, automatically retrieving relevant memories
        
        Note: Memory updates are deferred until endsession() is called.
        Conversations are stored in session buffer when learn=True.
        
        Args:
            message: User message
            learn: Whether to record conversation for later memory update
            
        Returns:
            AI response
        """
        # 1. Retrieve relevant conversations (if memo is enabled)
        retrieved_conversations = []
        if self.use_memo and self.memo and self.memo.conversations:
            search_results = self.memo.search_similar_conversations(message, top_k=3)
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
        memory_context = self._get_memory_context()
        
        # 4. Build system prompt
        if memory_context:
            system_prompt = f"""You are an intelligent assistant with long-term memory about the user.

User memory information:
{memory_context}

Please provide personalized responses based on your knowledge of the user."""
        else:
            system_prompt = "You are a helpful AI assistant."
        
        # 5. Call LLM
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": enhanced_message}
        ]
        response = self.llm_client.chat_completion(messages)
        
        # 6. Record conversation for potential batch update (if learn=True)
        if learn:
            # Record conversation to memo (if memo is enabled)
            if self.use_memo and self.memo:
                self.memo.add_conversation(message, response.content)
            
            # Store conversation in session buffer for later memory update
            self.session_conversations.append({
                'user_message': message,
                'ai_response': response.content
            })
        
        return response.content

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search for relevant memories"""
        if not self.use_memo or not self.memo:
            print("⚠️ Memo functionality is not enabled, cannot perform search")
            return []
        return self.memo.search_similar_conversations(query, top_k=top_k)
    
    def add_memory(self, content: str, memory_type: str = "fact") -> None:
        """Add memory"""
        if not self.use_memory or not self.memory:
            print("⚠️ Memory functionality is not enabled, cannot add memory")
            return
            
        if memory_type == "fact":
            self.memory.add_facts([content])
        elif memory_type == "preference":
            self.memory.add_preferences([content])
        elif memory_type == "event":
            self.memory.add_events([content])
        elif memory_type == "tom":
            self.memory.add_tom([content])
        else:
            raise ValueError(f"Unsupported memory_type: {memory_type}")
    
    def endsession(self) -> Dict[str, int]:
        """End conversation session and update memory with all conversations from this session
        
        Returns:
            Dict with counts of updated memory items
        """
        if not self.use_memory or not self.memory:
            print("⚠️ Memory functionality is not enabled, cannot update memory")
            self.session_conversations.clear()  # Clear buffer even if memory is disabled
            return {"events": 0}
        
        if not self.session_conversations:
            print("📝 No conversations to process in this session")
            return {"events": 0}
        
        # Process all conversations in the session
        events_to_add = []
        for conv in self.session_conversations:
            conversation_event = f"User: {conv['user_message']} | AI: {conv['ai_response']}"
            events_to_add.append(conversation_event)
        
        # Batch update memory
        if events_to_add:
            self.memory.add_events(events_to_add)
            print(f"✅ Session ended: {len(events_to_add)} conversations added to memory")
        
        # Clear session buffer
        processed_count = len(self.session_conversations)
        self.session_conversations.clear()
        
        return {"events": processed_count}
    
    def get_session_info(self) -> Dict[str, int]:
        """Get information about the current session
        
        Returns:
            Dict with session statistics
        """
        return {
            "pending_conversations": len(self.session_conversations),
            "memory_enabled": bool(self.use_memory and self.memory),
            "memo_enabled": bool(self.use_memo and self.memo)
        }
    
    def get_memory(self) -> Dict:
        """Get all memories"""
        if not self.use_memory or not self.memory:
            print("⚠️ Memory functionality is not enabled, cannot get memory")
            return {"facts": [], "preferences": [], "events": [], "tom": []}
            
        return {
            "facts": self.memory.get_facts(),
            "preferences": self.memory.get_preferences(), 
            "events": self.memory.get_events(),
            "tom": self.memory.get_tom()
        }
    
    def close(self) -> None:
        """Close all resources"""
        # Automatically end session and update memory before closing
        if self.session_conversations:
            self.endsession()
            
        if self.memory:
            self.memory.close()
        if self.memo:
            self.memo.close()
        if hasattr(self.llm_client, 'close'):
            self.llm_client.close()
    
    @contextmanager
    def session(self):
        """Context manager for automatic resource management"""
        try:
            yield self
        finally:
            self.close()
    
    # Internal methods
    def _get_memory_context(self) -> str:
        """Get memory context"""
        if not self.use_memory or not self.memory:
            return ""
            
        context_parts = []
        
        facts = self.memory.get_facts()
        if facts:
            context_parts.append(f"Facts about user: {', '.join(facts)}")
        
        preferences = self.memory.get_preferences()
        if preferences:
            context_parts.append(f"User preferences: {', '.join(preferences)}")
        
        events = self.memory.get_events()
        if events:
            context_parts.append(f"Important events: {', '.join(events)}")
        
        tom = self.memory.get_tom()
        if tom:
            context_parts.append(f"User psychological model: {', '.join(tom)}")
        
        return "\n".join(context_parts) if context_parts else "No user memory information available"
    
