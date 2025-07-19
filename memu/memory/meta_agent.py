"""
Meta Agent System for MemU - Refactored Architecture

The Meta Agent is now a pure coordinator responsible for:
1. Creating and managing specialized agent instances
2. Orchestrating agent execution based on priorities and dependencies  
3. Coordinating the entire memory processing workflow
4. Error handling and result aggregation

Each specialized agent now has complete independence with its own LLM processing
and storage capabilities.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import threading

from ..llm import BaseLLMClient
from ..utils import get_logger
from .specialized_agents import create_agent, get_available_agents, get_default_agent_order

logger = get_logger(__name__)


class MetaAgent:
    """
    Meta Agent for orchestrating specialized memory agents.
    
    Pure coordinator that:
    1. Creates and manages specialized agent instances
    2. Orchestrates agent execution based on priorities and dependencies
    3. Handles error management and result aggregation
    4. Provides a unified interface for the memory processing pipeline
    """
    
    def __init__(
        self,
        llm_client: BaseLLMClient = None,
        memory_dir: str = "memory",
        use_database: bool = True,
        embedding_client=None,
        agent_list: List[str] = None,
        **db_kwargs
    ):
        """
        Initialize Meta Agent
        
        Args:
            llm_client: LLM client for processing conversations
            memory_dir: Directory to store memory files
            use_database: Whether to use database storage
            embedding_client: Embedding client for vector generation
            agent_list: List of agent names to use (defaults to all available)
            **db_kwargs: Database connection parameters
        """
        self.llm_client = llm_client
        self.memory_dir = Path(memory_dir)
        self.use_database = use_database
        self.embedding_client = embedding_client
        self.db_kwargs = db_kwargs
        
        # Initialize thread lock for operations
        self._operation_lock = threading.Lock()
        
        # Determine which agents to use
        if agent_list is None:
            self.agent_names = get_default_agent_order()
        else:
            self.agent_names = agent_list
        
        # Storage for agent instances (lazy loaded)
        self._agents: Dict[str, Any] = {}
        
        storage_type = "database" if use_database else "file"
        logger.info(f"Meta Agent initialized with {storage_type} storage")
        logger.info(f"Configured agents: {self.agent_names}")
    
    def get_agent(self, agent_name: str):
        """
        Get or create a specialized agent instance
        
        Args:
            agent_name: Name of the agent to get/create
            
        Returns:
            Specialized agent instance
        """
        if agent_name not in self._agents:
            if not self.llm_client:
                raise ValueError("LLM client is required to create agents")
            
            # Create agent with MetaAgent's configuration
            self._agents[agent_name] = create_agent(
                agent_name=agent_name,
                llm_client=self.llm_client,
                memory_dir=str(self.memory_dir),
                use_database=self.use_database,
                embedding_client=self.embedding_client,
                **self.db_kwargs
            )
            logger.debug(f"Created agent: {agent_name}")
        
        return self._agents[agent_name]
    
    def get_all_agents(self) -> Dict[str, Any]:
        """Get all configured agent instances"""
        agents = {}
        for agent_name in self.agent_names:
            agents[agent_name] = self.get_agent(agent_name)
        return agents
        
    def process_conversation(
        self,
        conversation: str,
        character_name: str,
        session_date: str = ""
    ) -> Dict[str, Any]:
        """
        Process a conversation using all configured specialized agents
        
        Args:
            conversation: Raw conversation text
            character_name: Name of the character
            session_date: Date of the session
            
        Returns:
            Dict containing processing results, agent outputs, and any errors
        """
        with self._operation_lock:
            results = {
                "success": True,
                "character_name": character_name,
                "session_date": session_date or datetime.now().strftime("%Y-%m-%d"),
                "agent_outputs": {},
                "activity_summary": "",
                "errors": []
            }
            
            try:
                logger.info(f"Processing conversation for {character_name} with {len(self.agent_names)} agents")
                
                # Load existing content from all agents
                existing_content = {}
                for agent_name in self.agent_names:
                    try:
                        agent = self.get_agent(agent_name)
                        content = agent.read_memory(character_name)
                        existing_content[agent.memory_type] = content
                    except Exception as e:
                        logger.warning(f"Failed to load existing content for {agent_name}: {e}")
                        existing_content[agent_name.replace("_agent", "")] = ""
                
                # Process agents in priority order
                for agent_name in self.agent_names:
                    try:
                        agent = self.get_agent(agent_name)
                        
                        # Determine input content
                        if agent_name == "activity_agent":
                            # ActivityAgent gets raw conversation
                            input_content = conversation
                        else:
                            # Other agents get activity summary
                            input_content = existing_content.get("activity", conversation)
                        
                        # Process with the agent
                        agent_output = agent.process(
                            character_name=character_name,
                            input_content=input_content,
                            session_date=session_date,
                            existing_content=existing_content
                        )
                        
                        results["agent_outputs"][agent_name] = agent_output
                        
                        # Update existing content for next agents
                        existing_content[agent.memory_type] = agent_output
                        
                        # Special handling for ActivityAgent output
                        if agent_name == "activity_agent":
                            results["activity_summary"] = agent_output
                        
                        logger.info(f"Successfully processed {agent_name} for {character_name}")
                        
                    except Exception as e:
                        error_msg = f"Agent {agent_name} failed: {str(e)}"
                        logger.error(error_msg)
                        results["errors"].append(error_msg)
                        results["success"] = False
                
                if results["errors"]:
                    logger.warning(f"Completed with {len(results['errors'])} errors for {character_name}")
                else:
                    logger.info(f"Successfully processed conversation for {character_name}")
                
            except Exception as e:
                error_msg = f"Failed to process conversation: {str(e)}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
                results["success"] = False
            
            return results
    
    def process_single_agent(
        self,
        agent_name: str,
        character_name: str,
        input_content: str,
        session_date: str = ""
    ) -> Dict[str, Any]:
        """
        Process using a single specific agent
        
        Args:
            agent_name: Name of the agent to use
            character_name: Name of the character
            input_content: Input content for the agent
            session_date: Date of the session
            
        Returns:
            Dict containing processing results
        """
        try:
            agent = self.get_agent(agent_name)
            
            # Load existing content for context
            existing_content = {}
            for name in self.agent_names:
                try:
                    temp_agent = self.get_agent(name)
                    content = temp_agent.read_memory(character_name)
                    existing_content[temp_agent.memory_type] = content
                except Exception as e:
                    logger.warning(f"Failed to load existing content for {name}: {e}")
                    existing_content[name.replace("_agent", "")] = ""
            
            # Process with the specific agent
            output = agent.process(
                character_name=character_name,
                input_content=input_content,
                session_date=session_date,
                existing_content=existing_content
            )
            
            return {
                "success": True,
                "agent_name": agent_name,
                "character_name": character_name,
                "output": output
            }
            
        except Exception as e:
            logger.error(f"Failed to process with {agent_name}: {e}")
            return {
                "success": False,
                "agent_name": agent_name,
                "character_name": character_name,
                "error": str(e)
            }
    
    def read_character_memory(self, character_name: str, memory_type: str = None) -> Dict[str, str]:
        """
        Read memory content for a character from specific agents or all agents
        
        Args:
            character_name: Name of the character
            memory_type: Specific memory type to read (None for all)
            
        Returns:
            Dict of memory type -> content
        """
        memories = {}
        
        if memory_type:
            # Read from specific agent
            for agent_name in self.agent_names:
                agent = self.get_agent(agent_name)
                if agent.memory_type == memory_type:
                    memories[memory_type] = agent.read_memory(character_name)
                    break
        else:
            # Read from all agents
            for agent_name in self.agent_names:
                try:
                    agent = self.get_agent(agent_name)
                    content = agent.read_memory(character_name)
                    memories[agent.memory_type] = content
                except Exception as e:
                    logger.warning(f"Failed to read memory from {agent_name}: {e}")
                    memories[agent_name.replace("_agent", "")] = ""
        
        return memories
    
    def search_character_memories(
        self,
        character_name: str,
        query: str,
        memory_types: List[str] = None,
        limit: int = 5
    ) -> List[Dict]:
        """
        Search across character memories using semantic similarity
        
        Args:
            character_name: Name of the character
            query: Search query
            memory_types: Specific memory types to search (None for all)
            limit: Maximum number of results
            
        Returns:
            List of search results with similarity scores
        """
        all_results = []
        
        agents_to_search = []
        if memory_types:
            # Search specific memory types
            for agent_name in self.agent_names:
                agent = self.get_agent(agent_name)
                if agent.memory_type in memory_types:
                    agents_to_search.append(agent_name)
        else:
            # Search all agents
            agents_to_search = self.agent_names
        
        for agent_name in agents_to_search:
            try:
                agent = self.get_agent(agent_name)
                results = agent.search_memory(character_name, query, limit)
                all_results.extend(results)
            except Exception as e:
                logger.warning(f"Failed to search {agent_name}: {e}")
        
        # Sort by similarity if available
        if all_results and "similarity" in all_results[0]:
            all_results.sort(key=lambda x: x.get("similarity", 0), reverse=True)
        
        return all_results[:limit]
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get status information about all configured agents"""
        status = {
            "total_agents": len(self.agent_names),
            "loaded_agents": len(self._agents),
            "agent_details": {}
        }
        
        for agent_name in self.agent_names:
            if agent_name in self._agents:
                agent = self._agents[agent_name]
                status["agent_details"][agent_name] = {
                    "loaded": True,
                    "memory_type": agent.memory_type,
                    "priority": agent.get_priority(),
                    "dependencies": agent.get_dependencies()
                }
            else:
                status["agent_details"][agent_name] = {
                    "loaded": False
                }
        
        return status 