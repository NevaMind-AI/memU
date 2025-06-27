"""
Memory base classes for PersonaLab.

This module implements the new unified Memory architecture as described in STRUCTURE.md:
- Memory: Unified memory class containing ProfileMemory and EventMemory components
- ProfileMemory: Component for storing user/agent profile information
- EventMemory: Component for storing event-based memories
"""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Dict, Any, Union


class Memory:
    """
    Agent的完整记忆系统，集成画像记忆和事件记忆组件。
    
    根据STRUCTURE.md设计，Memory是统一的记忆管理类，内部包含：
    - ProfileMemory组件：管理画像记忆
    - EventMemory组件：管理事件记忆
    """
    
    def __init__(self, agent_id: str, memory_id: Optional[str] = None):
        """
        初始化Memory对象。
        
        Args:
            agent_id: 关联的Agent ID
            memory_id: 记忆ID，如果不提供则自动生成
        """
        self.memory_id = memory_id or str(uuid.uuid4())
        self.agent_id = agent_id
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        
        # 初始化记忆组件
        self.profile_memory = ProfileMemory()
        self.event_memory = EventMemory()
        
        # Theory of Mind元数据
        self.tom_metadata: Optional[Dict[str, Any]] = None
    
    def get_profile_content(self) -> str:
        """获取画像记忆内容"""
        return self.profile_memory.get_content()
    
    def get_event_content(self) -> List[str]:
        """获取事件记忆内容"""
        return self.event_memory.get_content()
    
    def update_profile(self, new_profile_info: str):
        """更新画像记忆"""
        self.profile_memory.update_content(new_profile_info)
        self.updated_at = datetime.now()
    
    def update_events(self, new_events: List[str]):
        """更新事件记忆"""
        for event in new_events:
            self.event_memory.add_event(event)
        self.updated_at = datetime.now()
    
    def to_prompt(self) -> str:
        """将完整记忆转换为prompt格式"""
        prompt = ""
        
        # 添加画像记忆
        profile_content = self.profile_memory.get_content()
        if profile_content:
            prompt += "## 用户画像\n"
            prompt += f"{profile_content}\n\n"
        
        # 添加事件记忆
        event_content = self.event_memory.get_content()
        if event_content:
            prompt += "## 相关事件\n"
            for event in event_content:
                prompt += f"- {event}\n"
            prompt += "\n"
        
        return prompt
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
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
            "tom_metadata": self.tom_metadata
        }
    
    def get_memory_summary(self) -> Dict[str, Any]:
        """获取Memory摘要信息"""
        return {
            "memory_id": self.memory_id,
            "agent_id": self.agent_id,
            "profile_length": len(self.get_profile_content()),
            "event_count": len(self.get_event_content()),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "has_tom_metadata": self.tom_metadata is not None
        }
    
    def clear_profile(self):
        """清空画像记忆"""
        self.profile_memory = ProfileMemory()
        self.updated_at = datetime.now()
    
    def clear_events(self):
        """清空事件记忆"""
        self.event_memory = EventMemory()
        self.updated_at = datetime.now()
    
    def clear_all(self):
        """清空所有记忆"""
        self.profile_memory = ProfileMemory()
        self.event_memory = EventMemory()
        self.tom_metadata = None
        self.updated_at = datetime.now()


class ProfileMemory:
    """
    画像记忆组件。
    
    作为Memory类的内部组件，用于存储用户或Agent的画像信息。
    存储格式：单个paragraph（段落）形式
    """
    
    def __init__(self, content: str = ""):
        """
        初始化ProfileMemory。
        
        Args:
            content: 初始画像内容
        """
        self.content = content
    
    def get_content(self) -> str:
        """获取画像内容"""
        return self.content
    
    def update_content(self, new_info: str):
        """
        更新画像信息，支持信息合并。
        
        Args:
            new_info: 新的画像信息
        """
        if not self.content:
            self.content = new_info
        else:
            # 智能合并逻辑，这里可以通过LLM实现更复杂的合并
            self.content = self._merge_profile_info(self.content, new_info)
    
    def set_content(self, content: str):
        """
        直接设置画像内容。
        
        Args:
            content: 新的画像内容
        """
        self.content = content
    
    def append_content(self, additional_info: str):
        """
        追加画像信息。
        
        Args:
            additional_info: 要追加的信息
        """
        if self.content:
            self.content = f"{self.content} {additional_info}".strip()
        else:
            self.content = additional_info
    
    def _merge_profile_info(self, existing: str, new_info: str) -> str:
        """
        合并画像信息的逻辑。
        
        Args:
            existing: 现有画像信息
            new_info: 新的画像信息
            
        Returns:
            合并后的画像信息
        """
        # 简化版本：直接追加，实际实现可以通过LLM进行智能合并
        return f"{existing} {new_info}".strip()
    
    def to_prompt(self) -> str:
        """转换为prompt格式"""
        if not self.content:
            return ""
        return f"## 用户画像\n{self.content}\n\n"
    
    def is_empty(self) -> bool:
        """检查画像是否为空"""
        return not self.content.strip()
    
    def get_word_count(self) -> int:
        """获取画像词数"""
        return len(self.content.split()) if self.content else 0


class EventMemory:
    """
    事件记忆组件。
    
    作为Memory类的内部组件，用于存储具体的事件或对话记录。
    存储格式：list of paragraphs（段落列表）形式
    """
    
    def __init__(self, events: Optional[List[str]] = None, max_events: int = 50):
        """
        初始化EventMemory。
        
        Args:
            events: 初始事件列表
            max_events: 最大事件数量
        """
        self.events = events or []
        self.max_events = max_events
    
    def get_content(self) -> List[str]:
        """获取事件列表"""
        return self.events.copy()
    
    def add_event(self, event_paragraph: str):
        """
        添加新事件，自动管理容量。
        
        Args:
            event_paragraph: 事件段落描述
        """
        if event_paragraph.strip():  # 只添加非空事件
            self.events.append(event_paragraph.strip())
            
            # 如果超过最大容量，移除最旧的事件
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
        获取最近的事件。
        
        Args:
            count: 要获取的事件数量
            
        Returns:
            最近的事件列表
        """
        return self.events[-count:] if count > 0 else []
    
    def get_oldest_events(self, count: int = 10) -> List[str]:
        """
        获取最早的事件。
        
        Args:
            count: 要获取的事件数量
            
        Returns:
            最早的事件列表
        """
        return self.events[:count] if count > 0 else []
    
    def search_events(self, keyword: str, case_sensitive: bool = False) -> List[str]:
        """
        搜索包含关键词的事件。
        
        Args:
            keyword: 搜索关键词
            case_sensitive: 是否区分大小写
            
        Returns:
            匹配的事件列表
        """
        if not case_sensitive:
            keyword = keyword.lower()
        
        matched_events = []
        for event in self.events:
            search_text = event if case_sensitive else event.lower()
            if keyword in search_text:
                matched_events.append(event)
        
        return matched_events
    
    def remove_event(self, index: int) -> bool:
        """
        移除指定索引的事件。
        
        Args:
            index: 事件索引
            
        Returns:
            是否成功移除
        """
        try:
            if 0 <= index < len(self.events):
                self.events.pop(index)
                return True
        except (IndexError, ValueError):
            pass
        return False
    
    def clear_events(self):
        """清空所有事件"""
        self.events.clear()
    
    def to_prompt(self) -> str:
        """转换为prompt格式"""
        if not self.events:
            return ""
        
        prompt = "## 相关事件\n"
        for event in self.events:
            prompt += f"- {event}\n"
        return prompt + "\n"
    
    def is_empty(self) -> bool:
        """检查事件列表是否为空"""
        return len(self.events) == 0
    
    def get_event_count(self) -> int:
        """获取事件总数"""
        return len(self.events)
    
    def get_total_text_length(self) -> int:
        """获取所有事件文本的总长度"""
        return sum(len(event) for event in self.events)


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