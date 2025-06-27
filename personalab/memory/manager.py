"""
Memory管理器模块。

提供统一的Memory管理接口，整合Memory、Pipeline和Storage层：
- MemoryManager: 主要的Memory管理类
- 实现完整的Memory生命周期管理
- 支持与LLM的集成
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from .base import Memory
from .pipeline import MemoryUpdatePipeline, PipelineResult
from .storage import MemoryRepository


class MemoryManager:
    """
    Memory管理器。
    
    提供Memory的完整生命周期管理，包括：
    - Memory的创建、加载、更新、保存
    - Pipeline的执行和管理
    - 与数据库的交互
    """
    
    def __init__(self, db_path: str = "memory.db", llm_client=None):
        """
        初始化MemoryManager。
        
        Args:
            db_path: 数据库文件路径
            llm_client: LLM客户端，用于智能处理
        """
        self.repository = MemoryRepository(db_path)
        self.pipeline = MemoryUpdatePipeline(llm_client)
        self.llm_client = llm_client
    
    def get_or_create_memory(self, agent_id: str) -> Memory:
        """
        获取或创建Agent的Memory。
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Memory: Agent的Memory对象
        """
        # 尝试从数据库加载现有Memory
        existing_memory = self.repository.load_memory_by_agent(agent_id)
        
        if existing_memory:
            return existing_memory
        
        # 创建新的Memory
        new_memory = Memory(agent_id=agent_id)
        
        # 保存到数据库
        self.repository.save_memory(new_memory)
        
        return new_memory
    
    def update_memory_with_conversation(
        self, 
        agent_id: str, 
        conversation: List[Dict[str, str]]
    ) -> Tuple[Memory, PipelineResult]:
        """
        通过对话更新Memory。
        
        Args:
            agent_id: Agent ID
            conversation: 对话内容
            
        Returns:
            Tuple[更新后的Memory, Pipeline结果]
        """
        # 1. 获取当前Memory
        current_memory = self.get_or_create_memory(agent_id)
        
        # 2. 通过Pipeline更新Memory
        updated_memory, pipeline_result = self.pipeline.update_with_pipeline(
            current_memory, 
            conversation
        )
        
        # 3. 保存更新后的Memory
        self.repository.save_memory(updated_memory)
        
        return updated_memory, pipeline_result
    
    def get_memory_prompt(self, agent_id: str) -> str:
        """
        获取Agent的Memory prompt。
        
        Args:
            agent_id: Agent ID
            
        Returns:
            str: 格式化的Memory prompt
        """
        memory = self.get_or_create_memory(agent_id)
        return memory.to_prompt()
    
    def update_profile(self, agent_id: str, profile_info: str) -> bool:
        """
        直接更新画像信息。
        
        Args:
            agent_id: Agent ID
            profile_info: 画像信息
            
        Returns:
            bool: 更新是否成功
        """
        try:
            memory = self.get_or_create_memory(agent_id)
            memory.update_profile(profile_info)
            return self.repository.save_memory(memory)
        except Exception as e:
            print(f"Error updating profile: {e}")
            return False
    
    def add_events(self, agent_id: str, events: List[str]) -> bool:
        """
        直接添加事件。
        
        Args:
            agent_id: Agent ID
            events: 事件列表
            
        Returns:
            bool: 添加是否成功
        """
        try:
            memory = self.get_or_create_memory(agent_id)
            memory.update_events(events)
            return self.repository.save_memory(memory)
        except Exception as e:
            print(f"Error adding events: {e}")
            return False
    
    def get_memory_info(self, agent_id: str) -> Dict[str, Any]:
        """
        获取Memory信息。
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Dict: Memory信息
        """
        memory = self.get_or_create_memory(agent_id)
        
        return {
            'memory_id': memory.memory_id,
            'agent_id': memory.agent_id,
            'created_at': memory.created_at.isoformat(),
            'updated_at': memory.updated_at.isoformat(),
            'profile_content_length': len(memory.get_profile_content()),
            'event_count': len(memory.get_event_content()),
            'has_tom_metadata': memory.tom_metadata is not None,
            'confidence_score': memory.tom_metadata.get('confidence_score') if memory.tom_metadata else None
        }
    
    def export_memory(self, agent_id: str) -> Dict[str, Any]:
        """
        导出Memory数据。
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Dict: 完整的Memory数据
        """
        memory = self.get_or_create_memory(agent_id)
        return memory.to_dict()
    
    def import_memory(self, memory_data: Dict[str, Any]) -> bool:
        """
        导入Memory数据。
        
        Args:
            memory_data: Memory数据字典
            
        Returns:
            bool: 导入是否成功
        """
        try:
            # 创建Memory对象
            memory = Memory(
                agent_id=memory_data['agent_id'],
                memory_id=memory_data.get('memory_id')
            )
            
            # 设置时间戳
            if 'created_at' in memory_data:
                memory.created_at = datetime.fromisoformat(memory_data['created_at'])
            if 'updated_at' in memory_data:
                memory.updated_at = datetime.fromisoformat(memory_data['updated_at'])
            
            # 设置Profile Memory
            if 'profile_memory' in memory_data:
                profile_data = memory_data['profile_memory']
                memory.update_profile(profile_data.get('content', ''))
            
            # 设置Event Memory
            if 'event_memory' in memory_data:
                event_data = memory_data['event_memory']
                memory.update_events(event_data.get('content', []))
            
            # 设置ToM metadata
            if 'tom_metadata' in memory_data:
                memory.tom_metadata = memory_data['tom_metadata']
            
            # 保存到数据库
            return self.repository.save_memory(memory)
            
        except Exception as e:
            print(f"Error importing memory: {e}")
            return False
    
    def delete_memory(self, agent_id: str) -> bool:
        """
        删除Agent的Memory。
        
        Args:
            agent_id: Agent ID
            
        Returns:
            bool: 删除是否成功
        """
        try:
            memory = self.repository.load_memory_by_agent(agent_id)
            if memory:
                return self.repository.delete_memory(memory.memory_id)
            return True  # 如果不存在，认为删除成功
        except Exception as e:
            print(f"Error deleting memory: {e}")
            return False
    
    def get_agent_memory_list(self, agent_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取Agent的Memory列表。
        
        Args:
            agent_id: Agent ID
            limit: 返回数量限制
            
        Returns:
            List[Dict]: Memory信息列表
        """
        return self.repository.list_memories_by_agent(agent_id, limit)
    
    def get_memory_stats(self, agent_id: str) -> Dict[str, Any]:
        """
        获取Memory统计信息。
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Dict: 统计信息
        """
        return self.repository.get_memory_stats(agent_id)
    
    def cleanup_old_memories(self, agent_id: str, keep_count: int = 5) -> int:
        """
        清理旧的Memory记录。
        
        Args:
            agent_id: Agent ID
            keep_count: 保留的记录数量
            
        Returns:
            int: 清理的记录数量
        """
        try:
            # 获取所有Memory记录
            all_memories = self.repository.list_memories_by_agent(agent_id, limit=1000)
            
            if len(all_memories) <= keep_count:
                return 0
            
            # 删除多余的记录
            to_delete = all_memories[keep_count:]
            deleted_count = 0
            
            for memory_info in to_delete:
                if self.repository.delete_memory(memory_info['memory_id']):
                    deleted_count += 1
            
            return deleted_count
            
        except Exception as e:
            print(f"Error cleaning up memories: {e}")
            return 0


class ConversationMemoryInterface:
    """
    对话Memory接口。
    
    为对话系统提供简化的Memory操作接口。
    """
    
    def __init__(self, memory_manager: MemoryManager):
        """
        初始化对话Memory接口。
        
        Args:
            memory_manager: Memory管理器
        """
        self.memory_manager = memory_manager
    
    def process_conversation_turn(
        self, 
        agent_id: str, 
        user_message: str, 
        assistant_message: str
    ) -> str:
        """
        处理一轮对话。
        
        Args:
            agent_id: Agent ID
            user_message: 用户消息
            assistant_message: 助手回复
            
        Returns:
            str: 更新后的Memory prompt
        """
        # 构建对话
        conversation = [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": assistant_message}
        ]
        
        # 更新Memory
        updated_memory, pipeline_result = self.memory_manager.update_memory_with_conversation(
            agent_id, 
            conversation
        )
        
        # 返回更新后的prompt
        return updated_memory.to_prompt()
    
    def get_context_for_response(self, agent_id: str) -> str:
        """
        获取用于生成回复的上下文。
        
        Args:
            agent_id: Agent ID
            
        Returns:
            str: Memory上下文
        """
        return self.memory_manager.get_memory_prompt(agent_id)
    
    def add_user_info(self, agent_id: str, user_info: str) -> bool:
        """
        添加用户信息到画像。
        
        Args:
            agent_id: Agent ID
            user_info: 用户信息
            
        Returns:
            bool: 添加是否成功
        """
        return self.memory_manager.update_profile(agent_id, user_info)
    
    def log_conversation_event(self, agent_id: str, event_description: str) -> bool:
        """
        记录对话事件。
        
        Args:
            agent_id: Agent ID
            event_description: 事件描述
            
        Returns:
            bool: 记录是否成功
        """
        return self.memory_manager.add_events(agent_id, [event_description]) 