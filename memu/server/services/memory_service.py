"""
Memory Service

Service for handling memory operations using MemU components.
"""

import asyncio
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...llm import OpenAIClient, AzureOpenAIClient, DeepSeekClient, OpenRouterClient
from ...memory import MemoryAgent, RecallAgent
from ...utils.logging import get_logger
from ..models import (
    ConversationMessage,
    DefaultCategoriesResponse,
    CategoryInfo,
    MemoryItem,
    RelatedMemoryItemsResponse,
    RelatedMemoryItem,
    RelatedClusteredCategoriesResponse,
    ClusteredCategory,
)

logger = get_logger(__name__)


class MemoryService:
    """Service for memory operations using MemU components"""
    
    def __init__(self):
        """Initialize memory service with environment variables"""
        self._memory_agent: Optional[MemoryAgent] = None
        self._llm_client = None
        
        # Load settings from environment
        self.llm_provider = (os.getenv("MEMU_LLM_PROVIDER", "openai")).lower()
        self.enable_embeddings = (os.getenv("MEMU_ENABLE_EMBEDDINGS", "true").lower() == "true")
        memory_dir = os.getenv("MEMU_MEMORY_DIR", "memu/server/memory")

        # Ensure memory directory exists
        self.memory_path = Path(memory_dir)
        self.memory_path.mkdir(exist_ok=True)
        
        logger.info(f"Memory service initialized with directory: {memory_dir}")
    
    def _get_llm_client(self):
        """Get or create LLM client"""
        if self._llm_client is None:
            provider = self.llm_provider

            if provider == "openai":
                self._llm_client = OpenAIClient(
                    api_key=os.getenv("OPENAI_API_KEY"),
                    model=os.getenv("MEMU_OPENAI_MODEL", "gpt-4.1-mini"),
                )
            elif provider == "azure":
                self._llm_client = AzureOpenAIClient(
                    api_key=os.getenv("AZURE_API_KEY"),
                    azure_endpoint=os.getenv("AZURE_ENDPOINT"),
                    model=os.getenv("MEMU_AZURE_DEPLOYMENT_NAME"),
                    api_version=os.getenv("AZURE_API_VERSION"),
                )
            # elif provider == "anthropic":
            #     self._llm_client = AnthropicClient.from_env()
            elif provider == "deepseek":
                self._llm_client = DeepSeekClient.from_env()
            elif provider == "openrouter":
                self._llm_client = OpenRouterClient.from_env()
            else:
                raise ValueError(f"Unsupported LLM provider: {provider}")
        
        return self._llm_client
    
    def _get_memory_agent(self) -> MemoryAgent:
        """Get or create memory agent"""
        if self._memory_agent is None:
            llm_client = self._get_llm_client()
            self._memory_agent = MemoryAgent(
                llm_client=llm_client,
                memory_dir=str(self.memory_path),
                enable_embeddings=self.enable_embeddings
            )
        return self._memory_agent
    

    
    async def memorize_conversation(
        self,
        conversation_text: Optional[str] = None,
        conversation: Optional[List[ConversationMessage]] = None,
        user_id: str = "",
        user_name: str = "",
        agent_id: str = "",
        agent_name: str = "",
        session_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process and memorize conversation using MemoryAgent
        
        Args:
            conversation_text: Conversation as plain text
            conversation: Conversation as structured messages
            user_id: User identifier
            user_name: User display name
            agent_id: Agent identifier
            agent_name: Agent display name
            session_date: Session date
            
        Returns:
            Dict with processing results
        """
        try:
            # Create a fresh MemoryAgent instance per request to avoid shared state across async jobs
            llm_client = self._get_llm_client()
            memory_agent = MemoryAgent(
                llm_client=llm_client,
                memory_dir=str(self.memory_path),
                enable_embeddings=self.enable_embeddings,
                agent_id=agent_id,
                user_id=user_id
            )
            
            # Convert conversation to the format expected by MemoryAgent
            conversation_data = []
            
            if conversation_text:
                # Split plain text into messages (simple heuristic)
                lines = conversation_text.strip().split('\n')
                for line in lines:
                    if ':' in line:
                        role, content = line.split(':', 1)
                        conversation_data.append({
                            "role": role.strip().lower(),
                            "content": content.strip()
                        })
                    else:
                        # Add as system message if no role specified
                        conversation_data.append({
                            "role": "system",
                            "content": line.strip()
                        })
            elif conversation:
                conversation_data = [
                    {"role": msg.role, "content": msg.content}
                    for msg in conversation
                ]
            else:
                raise ValueError("Either conversation_text or conversation must be provided")
            
            # Use user_name as character_name (no longer encode agent_id and user_id)
            character_name = user_name
            
            # Log the directory structure being used
            logger.info(f"Using directory structure: {os.getenv('MEMU_MEMORY_DIR')}/{agent_id}/{user_id}/ for character: {character_name}")
            
            # Run the memory processing
            # TODO: if there's already a memorization task on the same (agent_id, user_id) running,
            #       should let the new task wait for the old one to finish
            def run_memory_agent():
                return memory_agent.run(
                    conversation_data,
                    character_name,
                    session_date=session_date
                )
            result = await asyncio.get_event_loop().run_in_executor(None, run_memory_agent)
            
            logger.info(f"Memory processing completed for {agent_id}:{user_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error in memorize_conversation: {e}", exc_info=True)
            raise
    
    async def retrieve_default_categories(
        self,
        user_id: str,
        agent_id: Optional[str] = None,
        include_inactive: bool = False
    ) -> DefaultCategoriesResponse:
        """
        Retrieve default categories using RecallAgent
        
        Args:
            user_id: User identifier
            agent_id: Agent identifier
            include_inactive: Whether to include inactive categories
            
        Returns:
            DefaultCategoriesResponse with categories
        """
        try:
            # Create a fresh RecallAgent instance per request to avoid shared state across async jobs
            recall_agent = RecallAgent(
                memory_dir=str(self.memory_path),
                agent_id=agent_id or "default_agent",
                user_id=user_id
            )
            
            # Get default categories content
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                recall_agent.retrieve_default_category,
                agent_id or "default_agent",
                user_id
            )
            
            if not result.get("success"):
                logger.warning(f"Default category retrieval failed: {result.get('error')}")
                return DefaultCategoriesResponse(categories=[], total_categories=0)
            
            # Convert to API response format
            categories = []
            for item in result.get("results", []):
                # Parse memory content into individual memory items
                memories = self._parse_memory_content(
                    item["content"],
                    item["category"],
                    user_id
                )
                
                categories.append(CategoryInfo(
                    name=item["category"],
                    type="default",
                    description=f"Default {item['category']} memories",
                    is_active=True,
                    memories=memories,
                    memory_count=len(memories)
                ))
            
            return DefaultCategoriesResponse(
                categories=categories,
                total_categories=len(categories)
            )
            
        except Exception as e:
            logger.error(f"Error retrieving default categories: {e}", exc_info=True)
            raise
    
    async def retrieve_related_memory_items(
        self,
        user_id: str,
        agent_id: Optional[str] = None,
        query: str = "",
        top_k: int = 10,
        min_similarity: float = 0.3,
        include_categories: Optional[List[str]] = None
    ) -> RelatedMemoryItemsResponse:
        """
        Retrieve related memory items using semantic search
        
        Args:
            user_id: User identifier
            agent_id: Agent identifier
            query: Search query
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold
            include_categories: Categories to include in search
            
        Returns:
            RelatedMemoryItemsResponse with related memories
        """
        try:
            # Create a fresh RecallAgent instance per request to avoid shared state across async jobs
            recall_agent = RecallAgent(
                memory_dir=str(self.memory_path),
                agent_id=agent_id or "default_agent",
                user_id=user_id
            )

            # Retrieve relevant memories
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                recall_agent.retrieve_relevant_memories,
                agent_id or "default_agent",
                user_id,
                query,
                top_k,
            )
            
            if not result.get("success"):
                logger.warning(f"Memory retrieval failed: {result.get('error')}")
                return RelatedMemoryItemsResponse(
                    related_memories=[],
                    query=query,
                    total_found=0,
                    search_params={"query": query, "top_k": top_k, "min_similarity": min_similarity}
                )
            
            # Convert to API response format
            related_memories = []
            for item in result.get("results", []):
                if item.get("semantic_score", 0) >= min_similarity:
                    timestamp = datetime.strptime(item["metadata"]["mentioned_at"], "%Y-%m-%d")
                    memory = MemoryItem(
                        memory_id=item["memory_id"],
                        category=item.get("category", "unknown"),
                        content=item.get("content", ""),
                        happened_at=timestamp,
                        # created_at=timestamp,
                        # updated_at=timestamp,
                    )
                    
                    related_memories.append(RelatedMemoryItem(
                        memory=memory,
                        similarity_score=item.get("semantic_score", 0)
                    ))
            
            return RelatedMemoryItemsResponse(
                related_memories=related_memories,
                query=query,
                total_found=len(related_memories),
                search_params={
                    "query": query,
                    "top_k": top_k,
                    "min_similarity": min_similarity,
                    "include_categories": include_categories
                }
            )
            
        except Exception as e:
            logger.error(f"Error retrieving related memory items: {e}", exc_info=True)
            raise
    
    async def retrieve_related_clustered_categories(
        self,
        user_id: str,
        agent_id: Optional[str] = None,
        category_query: str = "",
        top_k: int = 5,
        min_similarity: float = 0.3
    ) -> RelatedClusteredCategoriesResponse:
        """
        Retrieve related clustered categories using semantic search
        
        Args:
            user_id: User identifier
            agent_id: Agent identifier
            category_query: Category search query
            top_k: Number of categories to return
            min_similarity: Minimum similarity threshold
            
        Returns:
            RelatedClusteredCategoriesResponse with clustered categories
        """
        try:
            # Create a fresh RecallAgent instance per request to avoid shared state across async jobs
            recall_agent = RecallAgent(
                memory_dir=str(self.memory_path),
                agent_id=agent_id or "default_agent",
                user_id=user_id
            )

            # Retrieve relevant categories
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                recall_agent.retrieve_relevant_category,
                agent_id or "default_agent",
                user_id,
                category_query,
                top_k,
            )
            
            if not result.get("success"):
                logger.warning(f"Category retrieval failed: {result.get('error')}")
                return RelatedClusteredCategoriesResponse(
                    clustered_categories=[],
                    category_query=category_query,
                    total_categories_found=0,
                    search_params={"category_query": category_query, "top_k": top_k, "min_similarity": min_similarity}
                )
            
            # Convert to API response format
            clustered_categories = []
            for item in result.get("results", []):
                if item.get("relevance_score", 0) >= min_similarity:
                    # Parse memory content into individual memory items
                    memories = self._parse_memory_content(
                        item["content"],
                        item["category"],
                        user_id
                    )
                    
                    clustered_categories.append(ClusteredCategory(
                        name=item["category"],
                        similarity_score=item.get("relevance_score", 0),
                        memories=memories,
                        memory_count=len(memories)
                    ))
            
            return RelatedClusteredCategoriesResponse(
                clustered_categories=clustered_categories,
                category_query=category_query,
                total_categories_found=len(clustered_categories),
                search_params={
                    "category_query": category_query,
                    "top_k": top_k,
                    "min_similarity": min_similarity
                }
            )
            
        except Exception as e:
            logger.error(f"Error retrieving clustered categories: {e}", exc_info=True)
            raise
    
    def _parse_memory_content(self, content: str, category: str, user_id: str) -> List[MemoryItem]:
        """
        Parse memory content into individual memory items
        
        Args:
            content: Raw memory content
            category: Memory category
            character_name: Character name
            
        Returns:
            List of MemoryItem objects
        """
        memories = []
        
        if not content:
            return memories
        
        # Split content by lines and create memory items
        lines = content.strip().split('\n')
        for i, line in enumerate(lines):
            line = line.strip()
            if line and not line.startswith('#'):  # Skip empty lines and headers

                pattern = r"^\[([^\]]+)\]\[mentioned at ([^\]]+)\]\s*(.*?)(?:\s*\[([^\]]*)\])?$"
                match = re.match(pattern, line)

                if match:
                    memory_id = match.group(1)
                    mentioned_at = match.group(2)
                    content = match.group(3).strip()
                    timestamp = datetime.strptime(mentioned_at, "%Y-%m-%d")
                else:
                    memory_id = f"{user_id}_{category}_{i}"
                    content = line
                    timestamp = datetime.now()

                memories.append(MemoryItem(
                    memory_id=memory_id,
                    category=category,
                    content=content,
                    happened_at=timestamp,
                    # created_at=timestamp,
                    # updated_at=timestamp,
                ))
        
        return memories
