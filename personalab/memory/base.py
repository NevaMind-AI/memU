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
    Agent的完整记忆系统，集成画像记忆、事件记忆和心理分析记忆组件。
    
    根据STRUCTURE.md设计，Memory是统一的记忆管理类，内部包含：
    - ProfileMemory组件：管理画像记忆
    - EventMemory组件：管理事件记忆
    - ToMMemory组件：管理Theory of Mind心理分析记忆
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
        self.tom_memory = ToMMemory()
    
    def get_profile_content(self) -> str:
        """获取画像记忆内容"""
        return self.profile_memory.get_content()
    
    def get_event_content(self) -> List[str]:
        """获取事件记忆内容"""
        return self.event_memory.get_content()
    
    def get_tom_content(self) -> List[str]:
        """获取Theory of Mind记忆内容"""
        return self.tom_memory.get_content()
    
    def update_profile(self, new_profile_info: str):
        """更新画像记忆"""
        self.profile_memory.update_content(new_profile_info)
        self.updated_at = datetime.now()
    
    def update_events(self, new_events: List[str]):
        """更新事件记忆"""
        for event in new_events:
            self.event_memory.add_event(event)
        self.updated_at = datetime.now()
    
    def update_tom(self, new_insights: List[str]):
        """更新Theory of Mind记忆"""
        for insight in new_insights:
            self.tom_memory.add_insight(insight)
        self.updated_at = datetime.now()
    
    def add_tom_insight(self, insight: str):
        """添加单个Theory of Mind洞察"""
        self.tom_memory.add_insight(insight)
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
        
        # 添加ToM记忆
        tom_content = self.tom_memory.get_content()
        if tom_content:
            prompt += "## 心理分析\n"
            for insight in tom_content:
                prompt += f"- {insight}\n"
            prompt += "\n"
        
        return prompt
    
    def get_memory_content(self) -> str:
        """获取完整记忆内容（用于LLM处理）"""
        return self.to_prompt()
    
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
            "tom_memory": {
                "content": self.tom_memory.get_content(),
                "content_type": "list_of_paragraphs"
            }
        }
    
    def get_memory_summary(self) -> Dict[str, Any]:
        """获取Memory摘要信息"""
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
        """清空画像记忆"""
        self.profile_memory = ProfileMemory()
        self.updated_at = datetime.now()
    
    def clear_events(self):
        """清空事件记忆"""
        self.event_memory = EventMemory()
        self.updated_at = datetime.now()
    
    def clear_tom(self):
        """清空Theory of Mind记忆"""
        self.tom_memory = ToMMemory()
        self.updated_at = datetime.now()
    
    def clear_all(self):
        """清空所有记忆"""
        self.profile_memory = ProfileMemory()
        self.event_memory = EventMemory()
        self.tom_memory = ToMMemory()
        self.updated_at = datetime.now()

    # 向后兼容的属性
    @property
    def tom_metadata(self) -> Optional[Dict[str, Any]]:
        """向后兼容：将tom_memory转换为metadata格式"""
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
        """向后兼容：从metadata格式设置tom_memory"""
        if value is None:
            self.tom_memory = ToMMemory()
        else:
            insights_text = value.get("insights", "")
            if insights_text:
                # 如果是字符串，按行分割
                if isinstance(insights_text, str):
                    insights = [line.strip() for line in insights_text.split("\n") if line.strip()]
                else:
                    insights = [str(insights_text)]
                
                self.tom_memory = ToMMemory(insights)


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
    
    def is_empty(self) -> bool:
        """检查画像记忆是否为空"""
        return not self.content.strip()
    
    def get_word_count(self) -> int:
        """获取画像内容的字数"""
        return len(self.content.split())


class EventMemory:
    """
    事件记忆组件。
    
    作为Memory类的内部组件，用于存储重要事件和对话要点。
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
        添加新事件。
        
        Args:
            event_paragraph: 事件描述段落
        """
        if event_paragraph.strip():  # 只添加非空事件
            self.events.append(event_paragraph.strip())
            
            # 如果超过最大数量，删除最旧的事件
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