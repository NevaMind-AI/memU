"""
Agent Registry System for MemU

This module provides a registry system for managing and organizing agents.
Agents can be dynamically registered from prompt files and executed by the meta agent.
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from ..prompts.prompt_loader import get_prompt_loader
from ..utils import get_logger

logger = get_logger(__name__)


@dataclass
class AgentConfig:
    """Configuration for an agent"""
    name: str
    prompt_file: str
    description: str
    output_file: str
    input_dependencies: List[str]  # Files this agent needs as input
    embedding_required: bool = True
    priority: int = 0  # Execution priority (higher = earlier)


class AgentRegistry:
    """
    Registry for managing and organizing agents.
    
    Agents are configured through JSON files and prompt files.
    Each agent has:
    - A prompt file defining its behavior
    - A configuration specifying inputs/outputs
    - Dependencies on other files or agents
    """
    
    def __init__(self, agents_dir: str = "agents", prompts_dir: str = None):
        """
        Initialize Agent Registry
        
        Args:
            agents_dir: Directory containing agent configurations
            prompts_dir: Directory containing prompt files
        """
        self.agents_dir = Path(agents_dir)
        self.agents_dir.mkdir(exist_ok=True)
        
        self.prompt_loader = get_prompt_loader(prompts_dir)
        self.registered_agents: Dict[str, AgentConfig] = {}
        self._load_agents()
    
    def _load_agents(self):
        """Load all agent configurations from directory"""
        config_files = list(self.agents_dir.glob("*.json"))
        
        for config_file in config_files:
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                agent_config = AgentConfig(**config_data)
                self.registered_agents[agent_config.name] = agent_config
                logger.info(f"Registered agent: {agent_config.name}")
                
            except Exception as e:
                logger.error(f"Failed to load agent config {config_file}: {e}")
    
    def register_agent(
        self, 
        name: str,
        prompt_file: str,
        description: str,
        output_file: str,
        input_dependencies: List[str] = None,
        embedding_required: bool = True,
        priority: int = 0,
        save_config: bool = True
    ) -> AgentConfig:
        """
        Register a new agent
        
        Args:
            name: Unique name for the agent
            prompt_file: Name of the prompt file (without .txt extension)
            description: Description of what the agent does
            output_file: Output file the agent will write to
            input_dependencies: List of files this agent depends on
            embedding_required: Whether embeddings are required for output
            priority: Execution priority (higher = earlier)
            save_config: Whether to save configuration to file
            
        Returns:
            AgentConfig object
        """
        if input_dependencies is None:
            input_dependencies = []
        
        agent_config = AgentConfig(
            name=name,
            prompt_file=prompt_file,
            description=description,
            output_file=output_file,
            input_dependencies=input_dependencies,
            embedding_required=embedding_required,
            priority=priority
        )
        
        self.registered_agents[name] = agent_config
        
        if save_config:
            self._save_agent_config(agent_config)
        
        logger.info(f"Registered agent: {name}")
        return agent_config
    
    def _save_agent_config(self, agent_config: AgentConfig):
        """Save agent configuration to file"""
        config_file = self.agents_dir / f"{agent_config.name}.json"
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(agent_config), f, indent=2, ensure_ascii=False)
    
    def get_agent(self, name: str) -> Optional[AgentConfig]:
        """Get agent configuration by name"""
        return self.registered_agents.get(name)
    
    def list_agents(self) -> List[AgentConfig]:
        """List all registered agents"""
        return list(self.registered_agents.values())
    
    def get_agents_by_priority(self) -> List[AgentConfig]:
        """Get agents sorted by execution priority (highest first)"""
        return sorted(self.registered_agents.values(), key=lambda x: x.priority, reverse=True)
    
    def get_agents_for_input(self, input_file: str) -> List[AgentConfig]:
        """Get all agents that depend on a specific input file"""
        return [
            agent for agent in self.registered_agents.values()
            if input_file in agent.input_dependencies
        ]
    
    def unregister_agent(self, name: str) -> bool:
        """
        Unregister an agent
        
        Args:
            name: Name of the agent to unregister
            
        Returns:
            True if agent was found and removed, False otherwise
        """
        if name in self.registered_agents:
            del self.registered_agents[name]
            
            # Remove config file if it exists
            config_file = self.agents_dir / f"{name}.json"
            if config_file.exists():
                config_file.unlink()
            
            logger.info(f"Unregistered agent: {name}")
            return True
        
        return False
    
    def validate_agent_dependencies(self) -> Dict[str, List[str]]:
        """
        Validate that all agent dependencies are available
        
        Returns:
            Dictionary of agent names and their missing dependencies
        """
        missing_deps = {}
        
        for agent_name, agent_config in self.registered_agents.items():
            missing = []
            
            # Check if prompt file exists
            try:
                self.prompt_loader.load_prompt(agent_config.prompt_file)
            except FileNotFoundError:
                missing.append(f"prompt:{agent_config.prompt_file}")
            
            if missing:
                missing_deps[agent_name] = missing
        
        return missing_deps
    
    def create_default_agents(self):
        """Create default agents for common memory operations with ActivityAgent as the first step"""
        default_agents = [
            {
                "name": "activity_agent",
                "prompt_file": "agent_activity",
                "description": "Create comprehensive activity summary from conversation",
                "output_file": "activity.md",
                "input_dependencies": [],  # First agent, processes raw conversation
                "priority": 10,  # Highest priority - runs first
                "embedding_required": True
            },
            {
                "name": "profile_agent",
                "prompt_file": "analyze_session_for_profile",
                "description": "Extract and update character profile information",
                "output_file": "profile.md",
                "input_dependencies": ["activity.md"],
                "priority": 5,
                "embedding_required": True
            },
            {
                "name": "event_agent", 
                "prompt_file": "analyze_session_for_events",
                "description": "Extract and record character events",
                "output_file": "events.md",
                "input_dependencies": ["activity.md"],
                "priority": 4,
                "embedding_required": True
            },
            {
                "name": "reminder_agent",
                "prompt_file": "analyze_session_for_reminders", 
                "description": "Extract reminders and todo items",
                "output_file": "reminders.md",
                "input_dependencies": ["activity.md"],
                "priority": 3,
                "embedding_required": True
            },
            {
                "name": "interest_agent",
                "prompt_file": "analyze_session_for_interests",
                "description": "Extract interests and hobbies",
                "output_file": "interests.md", 
                "input_dependencies": ["activity.md"],
                "priority": 2,
                "embedding_required": True
            },
            {
                "name": "study_agent",
                "prompt_file": "analyze_session_for_study",
                "description": "Extract learning goals and study information",
                "output_file": "study.md",
                "input_dependencies": ["activity.md"],
                "priority": 1,
                "embedding_required": True
            }
        ]
        
        for agent_data in default_agents:
            if agent_data["name"] not in self.registered_agents:
                self.register_agent(**agent_data)


# Global registry instance
_agent_registry = None


def get_agent_registry(agents_dir: str = "agents", prompts_dir: str = None) -> AgentRegistry:
    """
    Get the global agent registry instance
    
    Args:
        agents_dir: Directory containing agent configurations
        prompts_dir: Directory containing prompt files
        
    Returns:
        AgentRegistry instance
    """
    global _agent_registry
    if _agent_registry is None:
        _agent_registry = AgentRegistry(agents_dir, prompts_dir)
    return _agent_registry 