"""
Memory base classes for PersonaLab.

This module implements the new unified Memory architecture as described in STRUCTURE.md:
- Memory: Unified memory class containing ProfileMemory, EventMemory, and ToMMemory components
- ProfileMemory: Component for storing user/agent profile information
- EventMemory: Component for storing event-based memories
- ToMMemory: Component for storing Theory of Mind insights
"""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Dict, Any, Union


class Memory:
    """
    Complete memory system for AI agents, integrating profile memory, event memory, 
    and Theory of Mind psychological analysis components.
    
    According to the unified memory architecture design, Memory is the central memory 
    management class that internally contains:
    - ProfileMemory component: Manages profile/persona memory
    - EventMemory component: Manages event-based memories
    - ToMMemory component: Manages Theory of Mind psychological analysis memory
    """
    
    def __init__(self, agent_id: str, memory_id: Optional[str] = None):
        """
        Initialize Memory object.
        
        Args:
            agent_id: Associated Agent ID
            memory_id: Memory ID, auto-generated if not provided
        """
        self.memory_id = memory_id or str(uuid.uuid4())
        self.agent_id = agent_id
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        
        # Initialize memory components
        self.profile_memory = ProfileMemory()
        self.event_memory = EventMemory()
        self.tom_memory = ToMMemory()
    
    def get_profile_content(self) -> str:
        """Get profile memory content"""
        return self.profile_memory.get_content()
    
    def get_event_content(self) -> List[str]:
        """Get event memory content"""
        return self.event_memory.get_content()
    
    def get_tom_content(self) -> List[str]:
        """Get Theory of Mind memory content"""
        return self.tom_memory.get_content()
    
    def update_profile(self, new_profile_info: str):
        """Update profile memory"""
        self.profile_memory.update_content(new_profile_info)
        self.updated_at = datetime.now()
    
    def update_events(self, new_events: List[str]):
        """Update event memory"""
        for event in new_events:
            self.event_memory.add_event(event)
        self.updated_at = datetime.now()
    
    def update_tom(self, new_insights: List[str]):
        """Update Theory of Mind memory"""
        for insight in new_insights:
            self.tom_memory.add_insight(insight)
        self.updated_at = datetime.now()
    
    def add_tom_insight(self, insight: str):
        """Add single Theory of Mind insight"""
        self.tom_memory.add_insight(insight)
        self.updated_at = datetime.now()
    
    def to_prompt(self) -> str:
        """Convert complete memory to prompt format"""
        prompt = ""
        
        # Add profile memory
        profile_content = self.profile_memory.get_content()
        if profile_content:
            prompt += "## User Profile\n"
            prompt += f"{profile_content}\n\n"
        
        # Add event memory
        event_content = self.event_memory.get_content()
        if event_content:
            prompt += "## Related Events\n"
            for event in event_content:
                prompt += f"- {event}\n"
            prompt += "\n"
        
        # Add ToM memory
        tom_content = self.tom_memory.get_content()
        if tom_content:
            prompt += "## Psychological Analysis\n"
            for insight in tom_content:
                prompt += f"- {insight}\n"
            prompt += "\n"
        
        return prompt
    
    def get_memory_content(self) -> str:
        """Get complete memory content (for LLM processing)"""
        return self.to_prompt()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "memory_id": self.memory_id,
            "agent_id": self.agent_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "profile_memory": {
                "content": self.profile_memory.get_content(),
                "content_type": "paragraph"
            },
            "event_memory": {
                "content": self.event_memory.get_content(),
                "content_type": "list_of_paragraphs"
            },
            "tom_memory": {
                "content": self.tom_memory.get_content(),
                "content_type": "list_of_paragraphs"
            }
        }
    
    def get_memory_summary(self) -> Dict[str, Any]:
        """Get Memory summary information"""
        return {
            "memory_id": self.memory_id,
            "agent_id": self.agent_id,
            "profile_length": len(self.get_profile_content()),
            "event_count": len(self.get_event_content()),
            "tom_count": len(self.get_tom_content()),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    def clear_profile(self):
        """Clear profile memory"""
        self.profile_memory = ProfileMemory()
        self.updated_at = datetime.now()
    
    def clear_events(self):
        """Clear event memory"""
        self.event_memory = EventMemory()
        self.updated_at = datetime.now()
    
    def clear_tom(self):
        """Clear Theory of Mind memory"""
        self.tom_memory = ToMMemory()
        self.updated_at = datetime.now()
    
    def clear_all(self):
        """Clear all memories"""
        self.profile_memory = ProfileMemory()
        self.event_memory = EventMemory()
        self.tom_memory = ToMMemory()
        self.updated_at = datetime.now()

    # Backward compatibility properties
    @property
    def tom_metadata(self) -> Optional[Dict[str, Any]]:
        """Backward compatibility: Convert tom_memory to metadata format"""
        tom_content = self.tom_memory.get_content()
        if tom_content:
            return {
                "insights": "\n".join(tom_content),
                "insight_count": len(tom_content),
                "content_type": "list_of_paragraphs"
            }
        return None
    
    @tom_metadata.setter
    def tom_metadata(self, value: Optional[Dict[str, Any]]):
        """Backward compatibility: Set tom_memory from metadata format"""
        if value is None:
            self.tom_memory = ToMMemory()
        else:
            insights_text = value.get("insights", "")
            if insights_text:
                # If it's a string, split by lines
                if isinstance(insights_text, str):
                    insights = [line.strip() for line in insights_text.split("\n") if line.strip()]
                else:
                    insights = [str(insights_text)]
                
                self.tom_memory = ToMMemory(insights)


class ProfileMemory:
    """
    Profile memory component.
    
    Internal component of the Memory class for storing user or agent profile information.
    Storage format: Single paragraph form
    """
    
    def __init__(self, content: str = ""):
        """
        Initialize ProfileMemory.
        
        Args:
            content: Initial profile content
        """
        self.content = content
    
    def get_content(self) -> str:
        """Get profile content"""
        return self.content
    
    def update_content(self, new_info: str):
        """
        Update profile information with support for information merging.
        
        Args:
            new_info: New profile information
        """
        if not self.content:
            self.content = new_info
        else:
            # Intelligent merging logic, can be implemented with LLM for more complex merging
            self.content = self._merge_profile_info(self.content, new_info)
    
    def set_content(self, content: str):
        """
        Directly set profile content.
        
        Args:
            content: New profile content
        """
        self.content = content
    
    def append_content(self, additional_info: str):
        """
        Append profile information.
        
        Args:
            additional_info: Information to append
        """
        if self.content:
            self.content = f"{self.content} {additional_info}".strip()
        else:
            self.content = additional_info
    
    def _merge_profile_info(self, existing: str, new_info: str) -> str:
        """
        Logic for merging profile information.
        
        Args:
            existing: Existing profile information
            new_info: New profile information
            
        Returns:
            Merged profile information
        """
        # Simplified version: direct append, actual implementation can use LLM for intelligent merging
        return f"{existing} {new_info}".strip()
    
    def is_empty(self) -> bool:
        """Check if profile memory is empty"""
        return not self.content.strip()
    
    def get_word_count(self) -> int:
        """Get word count of profile content"""
        return len(self.content.split())


class EventMemory:
    """
    Event memory component.
    
    Internal component of the Memory class for storing important events and conversation highlights.
    Storage format: List of paragraphs form
    """
    
    def __init__(self, events: Optional[List[str]] = None, max_events: int = 50):
        """
        Initialize EventMemory.
        
        Args:
            events: Initial event list
            max_events: Maximum number of events
        """
        self.events = events or []
        self.max_events = max_events
    
    def get_content(self) -> List[str]:
        """Get event list"""
        return self.events.copy()
    
    def add_event(self, event_paragraph: str):
        """
        Add new event.
        
        Args:
            event_paragraph: Event description paragraph
        """
        if event_paragraph.strip():  # Only add non-empty events
            self.events.append(event_paragraph.strip())
            
            # If exceeds maximum, remove oldest events
            if len(self.events) > self.max_events:
                self.events = self.events[-self.max_events:]
    
    def update_recent_events(self, new_events: List[str]):
        """
        批量更新最近事件。
        
        Args:
            new_events: 新事件列表
        """
        for event in new_events:
            self.add_event(event)
    
    def get_recent_events(self, count: int = 10) -> List[str]:
        """
        获取最近的N个事件。
        
        Args:
            count: 要获取的事件数量
            
        Returns:
            最近的事件列表
        """
        return self.events[-count:] if count > 0 else []
    
    def get_oldest_events(self, count: int = 10) -> List[str]:
        """
        获取最旧的N个事件。
        
        Args:
            count: 要获取的事件数量
            
        Returns:
            最旧的事件列表
        """
        return self.events[:count] if count > 0 else []
    
    def search_events(self, keyword: str, case_sensitive: bool = False) -> List[str]:
        """
        根据关键词搜索事件。
        
        Args:
            keyword: 搜索关键词
            case_sensitive: 是否区分大小写
            
        Returns:
            包含关键词的事件列表
        """
        if not case_sensitive:
            keyword = keyword.lower()
            return [
                event for event in self.events 
                if keyword in event.lower()
            ]
        else:
            return [
                event for event in self.events 
                if keyword in event
            ]
    
    def remove_event(self, index: int) -> bool:
        """
        删除指定索引的事件。
        
        Args:
            index: 事件索引
            
        Returns:
            是否删除成功
        """
        if 0 <= index < len(self.events):
            self.events.pop(index)
            return True
        return False
    
    def clear_events(self):
        """清空所有事件"""
        self.events = []
    
    def to_prompt(self) -> str:
        """将事件转换为prompt格式"""
        if not self.events:
            return ""
        return "\n".join(f"- {event}" for event in self.events)
    
    def is_empty(self) -> bool:
        """检查事件记忆是否为空"""
        return len(self.events) == 0
    
    def get_event_count(self) -> int:
        """获取事件数量"""
        return len(self.events)
    
    def get_total_text_length(self) -> int:
        """获取所有事件文本的总长度"""
        return sum(len(event) for event in self.events)


class ToMMemory:
    """
    Theory of Mind记忆组件。
    
    作为Memory类的内部组件，用于存储心理分析洞察。
    存储格式：list of paragraphs（段落列表）形式
    """
    
    def __init__(self, insights: Optional[List[str]] = None, max_insights: int = 30):
        """
        初始化ToMMemory。
        
        Args:
            insights: 初始洞察列表
            max_insights: 最大洞察数量
        """
        self.insights = insights or []
        self.max_insights = max_insights
    
    def get_content(self) -> List[str]:
        """获取洞察列表"""
        return self.insights.copy()
    
    def add_insight(self, insight_paragraph: str):
        """
        添加新洞察。
        
        Args:
            insight_paragraph: 洞察描述段落
        """
        if insight_paragraph.strip():  # 只添加非空洞察
            self.insights.append(insight_paragraph.strip())
            
            # 如果超过最大数量，删除最旧的洞察
            if len(self.insights) > self.max_insights:
                self.insights = self.insights[-self.max_insights:]
    
    def update_insights(self, new_insights: List[str]):
        """
        批量更新洞察。
        
        Args:
            new_insights: 新洞察列表
        """
        for insight in new_insights:
            self.add_insight(insight)
    
    def get_recent_insights(self, count: int = 10) -> List[str]:
        """
        获取最近的N个洞察。
        
        Args:
            count: 要获取的洞察数量
            
        Returns:
            最近的洞察列表
        """
        return self.insights[-count:] if count > 0 else []
    
    def search_insights(self, keyword: str, case_sensitive: bool = False) -> List[str]:
        """
        根据关键词搜索洞察。
        
        Args:
            keyword: 搜索关键词
            case_sensitive: 是否区分大小写
            
        Returns:
            包含关键词的洞察列表
        """
        if not case_sensitive:
            keyword = keyword.lower()
            return [
                insight for insight in self.insights 
                if keyword in insight.lower()
            ]
        else:
            return [
                insight for insight in self.insights 
                if keyword in insight
            ]
    
    def remove_insight(self, index: int) -> bool:
        """
        删除指定索引的洞察。
        
        Args:
            index: 洞察索引
            
        Returns:
            是否删除成功
        """
        if 0 <= index < len(self.insights):
            self.insights.pop(index)
            return True
        return False
    
    def clear_insights(self):
        """清空所有洞察"""
        self.insights = []
    
    def to_prompt(self) -> str:
        """将洞察转换为prompt格式"""
        if not self.insights:
            return ""
        return "\n".join(f"- {insight}" for insight in self.insights)
    
    def is_empty(self) -> bool:
        """检查ToM记忆是否为空"""
        return len(self.insights) == 0
    
    def get_insight_count(self) -> int:
        """获取洞察数量"""
        return len(self.insights)
    
    def get_total_text_length(self) -> int:
        """获取所有洞察文本的总长度"""
        return sum(len(insight) for insight in self.insights)


# 保持向后兼容性的基础抽象类
class BaseMemory(ABC):
    """
    保持向后兼容性的抽象基类。
    
    注意：新代码应该使用上面的Memory统一类架构。
    """
    
    def __init__(self, agent_id: str, user_id: str = "0"):
        """
        Initialize base memory for a specific agent and user combination.
        
        Args:
            agent_id: Unique identifier for the agent
            user_id: Unique identifier for the user (defaults to "0" for agent-only profiles)
        """
        self.agent_id = agent_id
        self.user_id = user_id
        self.created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def _update_timestamp(self) -> None:
        """Update the last modification timestamp."""
        self.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    @abstractmethod
    def get_size(self) -> int:
        """Get the size/count of memory data."""
        pass
    
    @property
    def is_user_profile(self) -> bool:
        """Check if this is a user-specific profile."""
        return self.user_id != "0"
    
    @property
    def is_agent_profile(self) -> bool:
        """Check if this is an agent-only profile."""
        return self.user_id == "0"
    
    def get_memory_info(self) -> Dict[str, Any]:
        """Get general information about this memory instance."""
        return {
            "agent_id": self.agent_id,
            "user_id": self.user_id,
            "memory_type": self.__class__.__name__,
            "is_user_profile": self.is_user_profile,
            "is_agent_profile": self.is_agent_profile,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "size": self.get_size()
        } 