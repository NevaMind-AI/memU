"""
Specialized Agent Implementations for MemU Memory System

Each agent is a complete, independent entity with:
- Its own LLM processing capabilities
- Direct memory file/database operations
- Specific domain expertise
- Embedding generation support
"""

from typing import List
from .base_agent import BaseAgent


class ActivityAgent(BaseAgent):
    """
    Activity Agent - Processes raw conversations into comprehensive activity summaries
    
    This is the first agent in the pipeline, creating standardized activity.md files
    that serve as input for all other specialized agents.
    """
    
    def __init__(self, llm_client, **kwargs):
        super().__init__(
            agent_name="activity_agent",
            memory_type="activity",  # Special case: ActivityAgent doesn't use standard file storage
            llm_client=llm_client,
            **kwargs
        )
    
    def get_prompt_template(self) -> str:
        """Load activity agent prompt template"""
        return self.prompt_loader.load_prompt("agent_activity")
    
    def get_output_filename(self) -> str:
        return "activity.md"
    
    def get_dependencies(self) -> List[str]:
        return []  # First agent, no dependencies
    
    def get_priority(self) -> int:
        return 10  # Highest priority


class ProfileAgent(BaseAgent):
    """
    Profile Agent - Manages character profile information
    
    Extracts and maintains basic character information including personal details,
    personality traits, relationships, and life situation.
    """
    
    def __init__(self, llm_client, **kwargs):
        super().__init__(
            agent_name="profile_agent",
            memory_type="profile",
            llm_client=llm_client,
            **kwargs
        )
    
    def get_prompt_template(self) -> str:
        """Load profile agent prompt template"""
        return self.prompt_loader.load_prompt("analyze_session_for_profile")
    
    def get_output_filename(self) -> str:
        return "profile.md"
    
    def get_dependencies(self) -> List[str]:
        return ["activity.md"]
    
    def get_priority(self) -> int:
        return 5


class EventAgent(BaseAgent):
    """
    Event Agent - Records character events and activities
    
    Maintains a chronological record of events, activities, and interactions
    involving the character.
    """
    
    def __init__(self, llm_client, **kwargs):
        super().__init__(
            agent_name="event_agent",
            memory_type="event",  # Fixed: use singular form to match MemoryFileManager
            llm_client=llm_client,
            **kwargs
        )
    
    def get_prompt_template(self) -> str:
        """Load event agent prompt template"""
        return self.prompt_loader.load_prompt("analyze_session_for_events")
    
    def get_output_filename(self) -> str:
        return "events.md"
    
    def get_dependencies(self) -> List[str]:
        return ["activity.md"]
    
    def get_priority(self) -> int:
        return 4


class ReminderAgent(BaseAgent):
    """
    Reminder Agent - Manages todo items and scheduled actions
    
    Extracts and organizes reminders, todo tasks, deadlines, and scheduled
    actions from conversations.
    """
    
    def __init__(self, llm_client, **kwargs):
        super().__init__(
            agent_name="reminder_agent",
            memory_type="reminder",  # Fixed: use singular form to match MemoryFileManager
            llm_client=llm_client,
            **kwargs
        )
    
    def get_prompt_template(self) -> str:
        """Load reminder agent prompt template"""
        return self.prompt_loader.load_prompt("analyze_session_for_reminders")
    
    def get_output_filename(self) -> str:
        return "reminders.md"
    
    def get_dependencies(self) -> List[str]:
        return ["activity.md"]
    
    def get_priority(self) -> int:
        return 3


class InterestAgent(BaseAgent):
    """
    Interest Agent - Tracks hobbies, preferences, and interests
    
    Maintains records of the character's interests, hobbies, preferences,
    and recreational activities.
    """
    
    def __init__(self, llm_client, **kwargs):
        super().__init__(
            agent_name="interest_agent",
            memory_type="interests",
            llm_client=llm_client,
            **kwargs
        )
    
    def get_prompt_template(self) -> str:
        """Load interest agent prompt template"""
        return self.prompt_loader.load_prompt("analyze_session_for_interests")
    
    def get_output_filename(self) -> str:
        return "interests.md"
    
    def get_dependencies(self) -> List[str]:
        return ["activity.md"]
    
    def get_priority(self) -> int:
        return 2


class StudyAgent(BaseAgent):
    """
    Study Agent - Manages learning goals and educational activities
    
    Tracks learning goals, educational activities, courses, study schedules,
    and academic pursuits.
    """
    
    def __init__(self, llm_client, **kwargs):
        super().__init__(
            agent_name="study_agent",
            memory_type="study",
            llm_client=llm_client,
            **kwargs
        )
    
    def get_prompt_template(self) -> str:
        """Load study agent prompt template"""
        return self.prompt_loader.load_prompt("analyze_session_for_study")
    
    def get_output_filename(self) -> str:
        return "study.md"
    
    def get_dependencies(self) -> List[str]:
        return ["activity.md"]
    
    def get_priority(self) -> int:
        return 1


# Registry of all available specialized agents
SPECIALIZED_AGENTS = {
    "activity_agent": ActivityAgent,
    "profile_agent": ProfileAgent,
    "event_agent": EventAgent,
    "reminder_agent": ReminderAgent,
    "interest_agent": InterestAgent,
    "study_agent": StudyAgent,
}


def create_agent(agent_name: str, llm_client, **kwargs):
    """
    Factory function to create specialized agents
    
    Args:
        agent_name: Name of the agent to create
        llm_client: LLM client for the agent
        **kwargs: Additional parameters for the agent
        
    Returns:
        Initialized specialized agent instance
        
    Raises:
        ValueError: If agent_name is not recognized
    """
    if agent_name not in SPECIALIZED_AGENTS:
        raise ValueError(f"Unknown agent: {agent_name}. Available agents: {list(SPECIALIZED_AGENTS.keys())}")
    
    agent_class = SPECIALIZED_AGENTS[agent_name]
    return agent_class(llm_client=llm_client, **kwargs)


def get_available_agents() -> List[str]:
    """Get list of all available specialized agent names"""
    return list(SPECIALIZED_AGENTS.keys())


def get_default_agent_order() -> List[str]:
    """Get the default execution order for agents based on their priorities"""
    agents = []
    for agent_name, agent_class in SPECIALIZED_AGENTS.items():
        # Create a temporary instance to get priority
        temp_agent = type('TempAgent', (), {
            'agent_name': agent_name,
            'get_priority': lambda self: agent_class.__new__(agent_class).get_priority()
        })()
        agents.append((agent_name, temp_agent.get_priority()))
    
    # Sort by priority (higher first)
    agents.sort(key=lambda x: x[1], reverse=True)
    return [agent[0] for agent in agents] 