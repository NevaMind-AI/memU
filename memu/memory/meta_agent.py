"""
Meta Agent System for MemU

The Meta Agent is responsible for:
1. Summarizing conversations into activity.md files
2. Managing and executing all registered sub-agents  
3. Coordinating the entire memory processing workflow
4. Handling embedding generation for new content
"""

import os
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import threading

from ..llm import BaseLLMClient
from ..utils import get_logger
from .agent_registry import get_agent_registry, AgentConfig
from .file_manager import MemoryFileManager
from .db_manager import MemoryDatabaseManager
from .embeddings import get_default_embedding_client
from ..prompts.prompt_loader import get_prompt_loader

logger = get_logger(__name__)


class MetaAgent:
    """
    Meta Agent for orchestrating the entire memory processing pipeline.
    
    Workflow:
    1. Analyze conversation and generate activity.md summary
    2. Execute all registered sub-agents based on priority
    3. Generate embeddings for new content
    4. Update memory storage with results
    """
    
    def __init__(
        self,
        llm_client: BaseLLMClient = None,
        memory_dir: str = "memory",
        agents_dir: str = "agents", 
        use_database: bool = True,
        embedding_client=None,
        **db_kwargs
    ):
        """
        Initialize Meta Agent
        
        Args:
            llm_client: LLM client for processing conversations
            memory_dir: Directory to store memory files
            agents_dir: Directory containing agent configurations
            use_database: Whether to use database storage
            embedding_client: Embedding client for vector generation
            **db_kwargs: Database connection parameters
        """
        self.llm_client = llm_client
        self.memory_dir = Path(memory_dir)
        self.agents_dir = Path(agents_dir)
        self.use_database = use_database
        
        # Initialize thread lock for operations
        self._operation_lock = threading.Lock()
        
        # Initialize storage manager
        if use_database:
            self.storage_manager = MemoryDatabaseManager(**db_kwargs)
            
            # Setup embedding client
            if embedding_client:
                self.storage_manager.set_embedding_client(embedding_client)
            else:
                default_embedding = get_default_embedding_client()
                if default_embedding:
                    self.storage_manager.set_embedding_client(default_embedding)
                    logger.info("Using default embedding client for vector generation")
                else:
                    logger.warning("No embedding client configured - vectors will not be generated")
        else:
            self.storage_manager = MemoryFileManager(memory_dir)
        
        # Initialize agent registry
        prompts_dir = Path(__file__).parent.parent / "prompts"
        self.agent_registry = get_agent_registry(str(agents_dir), str(prompts_dir))
        
        # Initialize prompt loader
        self.prompt_loader = get_prompt_loader(str(prompts_dir))
        
        # Create default agents if they don't exist
        self.agent_registry.create_default_agents()
        
        storage_type = "database" if use_database else "file"
        logger.info(f"Meta Agent initialized with {storage_type} storage")
        logger.info(f"Agent registry loaded with {len(self.agent_registry.list_agents())} agents")
    

    
    def execute_sub_agent(
        self,
        agent_config: AgentConfig,
        character_name: str,
        conversation: str,
        session_date: str,
        existing_content: Dict[str, str] = None
    ) -> str:
        """
        Execute a single sub-agent
        
        Args:
            agent_config: Configuration for the agent to execute
            character_name: Name of the character
            conversation: Original conversation text (for ActivityAgent) or activity content (for others)
            session_date: Date of the session
            existing_content: Existing content from dependency files
            
        Returns:
            Generated content from the agent
        """
        if not self.llm_client:
            raise ValueError("No LLM client provided for agent execution")
        
        if existing_content is None:
            existing_content = {}
        
        try:
            # Load the agent's prompt
            prompt_template = self.prompt_loader.load_prompt(agent_config.prompt_file)
            
            # Prepare prompt variables
            prompt_vars = {
                "character_name": character_name,
                "session_date": session_date
            }
            
            # Handle different agent types
            if agent_config.name == "activity_agent":
                # ActivityAgent processes raw conversation
                prompt_vars["conversation"] = conversation
            else:
                # Other agents process activity summary
                if "activity" in existing_content:
                    prompt_vars["conversation"] = existing_content["activity"]
                else:
                    prompt_vars["conversation"] = ""
            
            # Add existing content based on dependencies
            for dep_file in agent_config.input_dependencies:
                if dep_file == "activity.md":
                    continue  # Already handled above
                
                dep_key = dep_file.replace(".md", "")
                if dep_key in existing_content:
                    prompt_vars[f"existing_{dep_key}"] = existing_content[dep_key]
                else:
                    prompt_vars[f"existing_{dep_key}"] = ""
            
            # Special handling for specific prompt types
            if "profile" in agent_config.prompt_file:
                # Profile agent might need events
                if "events" in existing_content:
                    prompt_vars["events"] = existing_content["events"]
                else:
                    prompt_vars["events"] = ""
            
            # Format the prompt
            formatted_prompt = prompt_template.format(**prompt_vars)
            
            # Execute the agent
            response = self.llm_client.chat_completion(
                messages=[
                    {"role": "system", "content": f"You are a specialized agent for {agent_config.description}"},
                    {"role": "user", "content": formatted_prompt}
                ]
            )
            
            generated_content = response.content.strip()
            logger.info(f"Executed agent {agent_config.name} for {character_name}")
            return generated_content
            
        except Exception as e:
            logger.error(f"Failed to execute agent {agent_config.name}: {e}")
            raise
    
    def process_conversation(
        self,
        conversation: str,
        character_name: str,
        session_date: str = None
    ) -> Dict[str, Any]:
        """
        Process a complete conversation through the meta agent pipeline
        
        Args:
            conversation: The conversation text to process
            character_name: Name of the character
            session_date: Date of the session
            
        Returns:
            Dictionary containing processing results
        """
        with self._operation_lock:
            if session_date is None:
                session_date = datetime.now().strftime("%Y-%m-%d")
            
            results = {
                "character_name": character_name,
                "session_date": session_date,
                "activity_summary": "",
                "agent_outputs": {},
                "embeddings_generated": [],
                "errors": []
            }
            
            try:
                logger.info(f"Processing conversation for {character_name} on {session_date}")
                
                # Step 1: Load existing content for agents
                existing_content = self._load_existing_content(character_name)
                
                # Step 2: Execute agents in priority order
                agents = self.agent_registry.get_agents_by_priority()
                
                for agent_config in agents:
                    try:
                        # ActivityAgent gets raw conversation, others get processed content
                        input_content = conversation if agent_config.name == "activity_agent" else conversation
                        
                        agent_output = self.execute_sub_agent(
                            agent_config,
                            character_name,
                            input_content,
                            session_date,
                            existing_content
                        )
                        
                        results["agent_outputs"][agent_config.name] = agent_output
                        
                        # Save agent output
                        self._save_content(character_name, agent_config.output_file, agent_output)
                        
                        # Update existing content for next agents
                        output_key = agent_config.output_file.replace(".md", "")
                        existing_content[output_key] = agent_output
                        
                        # Special handling for ActivityAgent output
                        if agent_config.name == "activity_agent":
                            results["activity_summary"] = agent_output
                        
                        # Generate embeddings if required
                        if agent_config.embedding_required:
                            try:
                                self._generate_embeddings(character_name, agent_config.output_file, agent_output)
                                results["embeddings_generated"].append(agent_config.output_file)
                            except Exception as e:
                                logger.warning(f"Failed to generate embeddings for {agent_config.output_file}: {e}")
                                results["errors"].append(f"Embedding generation failed for {agent_config.output_file}: {str(e)}")
                        
                    except Exception as e:
                        error_msg = f"Agent {agent_config.name} failed: {str(e)}"
                        logger.error(error_msg)
                        results["errors"].append(error_msg)
                
                logger.info(f"Successfully processed conversation for {character_name}")
                
            except Exception as e:
                error_msg = f"Failed to process conversation: {str(e)}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
            
            return results
    
    def _load_existing_content(self, character_name: str) -> Dict[str, str]:
        """Load existing content for all known files"""
        content = {}
        
        # Known file types to load (including activity.md)
        file_types = ["activity.md", "profile.md", "events.md", "reminders.md", "interests.md", "study.md", "important_events.md"]
        
        for file_type in file_types:
            try:
                if self.use_database:
                    file_content = self.storage_manager.read_memory_file(character_name, file_type)
                else:
                    file_path = self.memory_dir / character_name / file_type
                    if file_path.exists():
                        with open(file_path, 'r', encoding='utf-8') as f:
                            file_content = f.read().strip()
                    else:
                        file_content = ""
                
                content[file_type.replace(".md", "")] = file_content
                
            except Exception as e:
                logger.warning(f"Failed to load {file_type} for {character_name}: {e}")
                content[file_type.replace(".md", "")] = ""
        
        return content
    
    def _save_content(self, character_name: str, filename: str, content: str):
        """Save content to storage"""
        try:
            if self.use_database:
                self.storage_manager.write_memory_file(character_name, filename, content)
            else:
                char_dir = self.memory_dir / character_name
                char_dir.mkdir(exist_ok=True)
                
                file_path = char_dir / filename
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            logger.debug(f"Saved {filename} for {character_name}")
            
        except Exception as e:
            logger.error(f"Failed to save {filename} for {character_name}: {e}")
            raise
    
    def _generate_embeddings(self, character_name: str, filename: str, content: str):
        """Generate embeddings for content"""
        if self.use_database and hasattr(self.storage_manager, 'embedding_client'):
            try:
                # Split content into chunks for embedding
                chunks = self._split_content_for_embedding(content)
                
                for i, chunk in enumerate(chunks):
                    self.storage_manager.add_memory_with_embedding(
                        character_name=character_name,
                        content=chunk,
                        memory_type=filename.replace(".md", ""),
                        metadata={
                            "filename": filename,
                            "chunk_index": i,
                            "total_chunks": len(chunks),
                            "session_date": datetime.now().isoformat()
                        }
                    )
                
                logger.debug(f"Generated embeddings for {filename} ({len(chunks)} chunks)")
                
            except Exception as e:
                logger.error(f"Failed to generate embeddings for {filename}: {e}")
                raise
    
    def _split_content_for_embedding(self, content: str, max_chunk_size: int = 1000) -> List[str]:
        """Split content into chunks suitable for embedding"""
        if len(content) <= max_chunk_size:
            return [content]
        
        # Split by paragraphs first
        paragraphs = content.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) + 2 <= max_chunk_size:
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = paragraph
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get status of all registered agents"""
        agents = self.agent_registry.list_agents()
        missing_deps = self.agent_registry.validate_agent_dependencies()
        
        return {
            "total_agents": len(agents),
            "agents": [
                {
                    "name": agent.name,
                    "description": agent.description,
                    "prompt_file": agent.prompt_file,
                    "output_file": agent.output_file,
                    "priority": agent.priority,
                    "dependencies": agent.input_dependencies,
                    "missing_dependencies": missing_deps.get(agent.name, [])
                }
                for agent in agents
            ],
            "agents_with_issues": len(missing_deps)
        }
    
    def register_new_agent_from_prompt(
        self,
        name: str,
        prompt_content: str,
        description: str,
        output_file: str,
        input_dependencies: List[str] = None,
        priority: int = 0
    ) -> AgentConfig:
        """
        Register a new agent from prompt content
        
        Args:
            name: Unique name for the agent
            prompt_content: The prompt text content
            description: Description of what the agent does
            output_file: Output file the agent will write to
            input_dependencies: List of files this agent depends on
            priority: Execution priority
            
        Returns:
            AgentConfig object
        """
        if input_dependencies is None:
            input_dependencies = ["activity.md"]
        
        # Save prompt to file
        prompt_filename = f"agent_{name}"
        prompt_file = self.prompt_loader.prompts_dir / f"{prompt_filename}.txt"
        
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write(prompt_content)
        
        # Register the agent
        agent_config = self.agent_registry.register_agent(
            name=name,
            prompt_file=prompt_filename,
            description=description,
            output_file=output_file,
            input_dependencies=input_dependencies,
            priority=priority
        )
        
        logger.info(f"Registered new agent '{name}' from prompt content")
        return agent_config 