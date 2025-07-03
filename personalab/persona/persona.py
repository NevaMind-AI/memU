"""
PersonaLab Persona Class

Provides a clean API for using PersonaLab's Memory and Memo functionality with LLM integration.
"""

from contextlib import contextmanager
from typing import Dict, List

from ..config import get_llm_config_manager
from ..config.database import get_database_manager
from ..llm import OpenAIClient
from ..memo import ConversationManager
from ..memory import Memory, MemoryUpdatePipeline


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
        use_memo: bool = True,
        db_manager=None,
    ):
        """Initialize Persona

        Args:
            agent_id: Agent identifier
            llm_client: LLM client instance (OpenAIClient, AnthropicClient, etc.)
                       If None, will create default OpenAI client
            personality: Personality description for the AI (e.g. "You are a friendly and helpful coding assistant")
                        This will be included in the system prompt to define the AI's character
            data_dir: Data directory for conversation storage (legacy parameter)
            show_retrieval: Whether to show retrieval process
            use_memory: Whether to enable Memory functionality (long-term memory)
            use_memo: Whether to enable Memo functionality (conversation recording & retrieval)
            db_manager: Database manager instance. If None, will use global PostgreSQL manager

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

        # Database manager setup
        if db_manager is not None:
            self.db_manager = db_manager
        else:
            # Use global database manager (PostgreSQL)
            self.db_manager = get_database_manager()

        # Session conversation buffers for different users
        self.session_conversations = {}  # user_id -> conversations

        # Memory and Memo instances will be created per user as needed
        self.memories = {}  # user_id -> Memory instance
        self.memos = {}  # user_id -> Memo instance

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
        # 1. Retrieve relevant conversations (if memo is enabled)
        retrieved_conversations = []
        memo = self._get_or_create_memo(user_id)
        if memo:
            try:
                search_results = memo.search_similar_conversations(
                    self.agent_id, message, limit=3
                )
                retrieved_conversations = search_results

                if self.show_retrieval and retrieved_conversations:
                    print(
                        f"\n🔍 Retrieved {len(retrieved_conversations)} relevant conversations:"
                    )
                    for i, conv in enumerate(retrieved_conversations, 1):
                        summary = conv.get(
                            "summary", conv.get("content_text", "No summary")
                        )[:50]
                        print(f"  {i}. {summary}...")
                    print()
            except Exception as e:
                if self.show_retrieval:
                    print(f"⚠️ Could not retrieve conversations: {e}")
                retrieved_conversations = []

        # 2. Build message with retrieved content
        enhanced_message = message
        if retrieved_conversations:
            context = "\n".join(
                [
                    f"Related history: {conv['summary']}"
                    for conv in retrieved_conversations
                ]
            )
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
            system_prompt_parts.append(
                "Please provide personalized responses based on your knowledge of the user."
            )

        system_prompt = "\n\n".join(system_prompt_parts)

        # 5. Call LLM
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": enhanced_message},
        ]
        response = self.llm_client.chat_completion(messages)

        # Handle different response formats
        if isinstance(response, str):
            response_content = response
        elif hasattr(response, "content"):
            response_content = response.content
        elif hasattr(response, "choices") and len(response.choices) > 0:
            response_content = response.choices[0].message.content
        else:
            response_content = str(response)

        # 6. Record conversation for potential batch update (if learn=True)
        if learn:
            # Record conversation to memo (if memo is enabled)
            if memo:
                messages = [
                    {"role": "user", "content": message},
                    {"role": "assistant", "content": response_content},
                ]
                memo.record_conversation(
                    agent_id=self.agent_id, user_id=user_id, messages=messages
                )

            # Store conversation in session buffer for later memory update
            self.session_conversations.setdefault(user_id, []).append(
                {"user_message": message, "ai_response": response_content}
            )

        return response_content

    def search(self, query: str, user_id: str, top_k: int = 5) -> List[Dict]:
        """Search for relevant memories

        Args:
            query: Search query
            user_id: User identifier (required)
            top_k: Number of results to return

        Returns:
            List of search results
        """
        memo = self._get_or_create_memo(user_id)
        if not memo:
            print(
                f"⚠️ Memo functionality is not enabled for user {user_id}, cannot perform search"
            )
            return []
        return memo.search_similar_conversations(query, top_k=top_k)

    def add_memory(
        self, content: str, user_id: str, memory_type: str = "profile"
    ) -> None:
        """Add memory

        Args:
            content: Memory content to add
            user_id: User identifier (required)
            memory_type: Type of memory - 'profile', 'event', or 'mind'
        """
        memory = self._get_or_create_memory(user_id)
        if not memory:
            print(
                f"⚠️ Memory functionality is not enabled for user {user_id}, cannot add memory"
            )
            return

        if memory_type == "profile":
            memory.add_profile(content)
        elif memory_type == "event":
            memory.add_events([content])
        elif memory_type == "mind":
            memory.add_mind([content])
        else:
            raise ValueError(
                f"Unsupported memory_type: {memory_type}. Supported types: 'profile', 'event', 'mind'"
            )

        # Save updated memory to database using the configured database manager
        db = self.db_manager.get_memory_db()
        db.save_memory(memory)

    def endsession(self, user_id: str) -> Dict[str, int]:
        """End conversation session and update memory with all conversations from this session

        Args:
            user_id: User identifier (required)

        Returns:
            Dict with counts of updated memory items
        """
        memory = self._get_or_create_memory(user_id)
        if not memory:
            print(
                f"⚠️ Memory functionality is not enabled for user {user_id}, cannot update memory"
            )
            self.session_conversations.setdefault(
                user_id, []
            ).clear()  # Clear buffer even if memory is disabled
            return {"events": 0}

        if not self.session_conversations.get(user_id):
            print(f"📝 No conversations to process in this session for user {user_id}")
            return {"events": 0}

        # Convert session conversations to pipeline format
        session_conversation = []
        for conv in self.session_conversations[user_id]:
            session_conversation.extend(
                [
                    {"role": "user", "content": conv["user_message"]},
                    {"role": "assistant", "content": conv["ai_response"]},
                ]
            )

        # Use memory update pipeline to update memory
        try:
            pipeline = MemoryUpdatePipeline(llm_client=self.llm_client)
            updated_memory, pipeline_result = pipeline.update_with_pipeline(
                memory, session_conversation
            )

            # Save updated memory to database using the configured database manager
            db = self.db_manager.get_memory_db()
            db.save_memory(updated_memory)

            # Update the memory reference
            self.memories[user_id] = updated_memory

            print(f"✅ Session ended: Memory updated using pipeline for user {user_id}")
            print(
                f"   - Profile updated: {pipeline_result.update_result.profile_updated}"
            )
            print(f"   - Event count: {len(updated_memory.get_event_content())}")

        except Exception as e:
            print(f"❌ Error updating memory with pipeline: {e}")
            # Fallback to clearing session without updating memory
            self.session_conversations[user_id].clear()
            return {"events": 0}

        # Clear session buffer
        _ = len(self.session_conversations[user_id])
        self.session_conversations[user_id].clear()

        return {
            "events": len(updated_memory.get_event_content()),
            "profile_updated": int(pipeline_result.update_result.profile_updated),
        }

    def get_session_info(self, user_id: str) -> Dict[str, int]:
        """Get information about the current session

        Args:
            user_id: User identifier (required)

        Returns:
            Dict with session information
        """
        return {
            "pending_conversations": len(self.session_conversations.get(user_id, [])),
            "memory_enabled": bool(self.use_memory and self.memories.get(user_id)),
            "memo_enabled": bool(self.use_memo and self.memos.get(user_id)),
        }

    def get_memory(self, user_id: str) -> Dict:
        """Get all memories

        Args:
            user_id: User identifier (required)

        Returns:
            Dict with user's memories
        """
        memory = self._get_or_create_memory(user_id)
        if not memory:
            print(
                f"⚠️ Memory functionality is not enabled for user {user_id}, cannot get memory"
            )
            return {"profile": "", "events": [], "mind": []}

        return {
            "profile": memory.get_profile(),
            "events": memory.get_events(),
            "mind": memory.get_mind(),
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

    def _parse_events_from_llm_response(self, response_content: str) -> List[str]:
        """Parse events from LLM response

        Args:
            response_content: LLM response text

        Returns:
            List of extracted events
        """
        events = []
        lines = response_content.strip().split("\n")

        # Look for events section
        in_events_section = False
        for line in lines:
            line = line.strip()

            if line.lower().startswith("events:"):
                in_events_section = True
                continue

            if in_events_section and line.startswith("- "):
                event = line[2:].strip()
                if event:  # Only add non-empty events
                    events.append(event)
            elif in_events_section and line and not line.startswith("-"):
                # Stop if we hit content that's not an event
                break

        return events

    def _get_or_create_memory(self, user_id: str):
        """Get or create Memory instance for a user"""
        if not self.use_memory:
            return None

        if user_id not in self.memories:
            # Try to load existing memory from database first
            db = self.db_manager.get_memory_db()
            existing_memory = db.get_memory_by_agent_and_user(self.agent_id, user_id)

            if existing_memory:
                # Load existing memory
                self.memories[user_id] = existing_memory
            else:
                # Create new memory if none exists
                new_memory = Memory(agent_id=self.agent_id, user_id=user_id)
                # Save the new memory to database
                db.save_memory(new_memory)
                self.memories[user_id] = new_memory
        return self.memories[user_id]

    def _get_or_create_memo(self, user_id: str):
        """Get or create Memo instance for a user"""
        if not self.use_memo:
            return None

        if user_id not in self.memos:
            self.memos[user_id] = ConversationManager(
                db_manager=self.db_manager,
                enable_embeddings=True,
                embedding_provider="auto",
            )
        return self.memos[user_id]

    def _get_memory_context(self, user_id: str) -> str:
        """Get memory context

        Args:
            user_id: User identifier (required)

        Returns:
            Formatted memory context string
        """
        memory = self._get_or_create_memory(user_id)
        if not memory:
            return ""

        context_parts = []

        profile = memory.get_profile()
        if profile:
            context_parts.append(f"User profile: {profile}")

        events = memory.get_events()
        if events:
            context_parts.append(f"Important events: {', '.join(events)}")

        mind = memory.get_mind()
        if mind:
            context_parts.append(f"Psychological insights: {', '.join(mind)}")

        return "\n".join(context_parts) if context_parts else ""
