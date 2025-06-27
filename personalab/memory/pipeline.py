"""
Memory更新Pipeline模块。

根据STRUCTURE.md设计，实现Memory的三阶段更新流程：
Input → Modification → Update → Theory of Mind → Database Storage
"""

from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass

from .base import Memory, ProfileMemory, EventMemory


@dataclass
class ModificationResult:
    """Modification阶段的结果"""
    processed_conversation: List[Dict[str, str]]
    contains_profile_info: bool
    profile_relevant_info: str
    event_info: List[str]
    metadata: Dict[str, Any]


@dataclass
class UpdateResult:
    """Update阶段的结果"""
    updated_profile: ProfileMemory
    updated_events: EventMemory
    profile_updated: bool
    events_added: int
    metadata: Dict[str, Any]


@dataclass
class ToMResult:
    """Theory of Mind阶段的结果"""
    insights: Dict[str, Any]
    metadata: Dict[str, Any]
    confidence_score: float


@dataclass
class PipelineResult:
    """完整Pipeline的结果"""
    modification_result: ModificationResult
    update_result: UpdateResult
    tom_result: ToMResult
    new_memory: Memory
    pipeline_metadata: Dict[str, Any]


class MemoryUpdatePipeline:
    """
    Memory更新Pipeline处理器。
    
    实现三阶段的Memory更新流程：
    1. Modification: 预处理对话内容
    2. Update: 更新画像和事件记忆
    3. Theory of Mind: 深度分析和推理
    """
    
    def __init__(self, llm_client=None):
        """
        初始化Pipeline。
        
        Args:
            llm_client: LLM客户端，用于智能处理
        """
        self.llm_client = llm_client
    
    def update_with_pipeline(
        self, 
        previous_memory: Memory, 
        session_conversation: List[Dict[str, str]]
    ) -> Tuple[Memory, PipelineResult]:
        """
        通过完整Pipeline更新Memory。
        
        Args:
            previous_memory: 之前的Memory对象
            session_conversation: 当前会话对话内容
            
        Returns:
            Tuple[更新后的Memory对象, Pipeline执行结果]
        """
        # 1. Modification阶段：预处理对话内容
        modification_result = self.modification_stage(session_conversation)
        
        # 2. Update阶段：分别更新画像和事件记忆
        update_result = self.update_stage(previous_memory, modification_result)
        
        # 3. Theory of Mind阶段：深度分析
        tom_result = self.theory_of_mind_stage(update_result, session_conversation)
        
        # 4. 创建新的Memory对象
        new_memory = self._create_updated_memory(
            previous_memory, 
            update_result, 
            tom_result
        )
        
        # 5. 构建Pipeline结果
        pipeline_result = PipelineResult(
            modification_result=modification_result,
            update_result=update_result,
            tom_result=tom_result,
            new_memory=new_memory,
            pipeline_metadata={
                'execution_time': datetime.now().isoformat(),
                'conversation_length': len(session_conversation),
                'profile_updated': update_result.profile_updated,
                'events_added': update_result.events_added
            }
        )
        
        return new_memory, pipeline_result
    
    def modification_stage(self, session_conversation: List[Dict[str, str]]) -> ModificationResult:
        """
        Modification阶段：对对话内容进行预处理和分析。
        
        Args:
            session_conversation: 对话内容
            
        Returns:
            ModificationResult: 处理结果
        """
        # 简化版本的信息提取逻辑
        profile_relevant_info = ""
        event_info = []
        contains_profile_info = False
        
        for message in session_conversation:
            role = message.get('role', '')
            content = message.get('content', '')
            
            if role == 'user':
                # 检测是否包含用户画像信息
                if self._contains_profile_info(content):
                    contains_profile_info = True
                    profile_relevant_info += f" {content}"
                
                # 提取事件信息
                event_description = self._extract_event_description(content)
                if event_description:
                    event_info.append(event_description)
        
        return ModificationResult(
            processed_conversation=session_conversation,
            contains_profile_info=contains_profile_info,
            profile_relevant_info=profile_relevant_info.strip(),
            event_info=event_info,
            metadata={
                'stage': 'modification',
                'processed_at': datetime.now().isoformat()
            }
        )
    
    def update_stage(
        self, 
        previous_memory: Memory, 
        modification_result: ModificationResult
    ) -> UpdateResult:
        """
        Update阶段：更新画像和事件记忆。
        
        Args:
            previous_memory: 之前的Memory对象
            modification_result: Modification阶段结果
            
        Returns:
            UpdateResult: 更新结果
        """
        # 更新画像记忆
        updated_profile = ProfileMemory(previous_memory.get_profile_content())
        profile_updated = False
        
        if modification_result.contains_profile_info and modification_result.profile_relevant_info:
            updated_profile.update_content(modification_result.profile_relevant_info)
            profile_updated = True
        
        # 更新事件记忆
        updated_events = EventMemory(
            events=previous_memory.get_event_content().copy(),
            max_events=previous_memory.event_memory.max_events
        )
        
        events_added = 0
        for event in modification_result.event_info:
            updated_events.add_event(event)
            events_added += 1
        
        return UpdateResult(
            updated_profile=updated_profile,
            updated_events=updated_events,
            profile_updated=profile_updated,
            events_added=events_added,
            metadata={
                'stage': 'update',
                'updated_at': datetime.now().isoformat()
            }
        )
    
    def theory_of_mind_stage(
        self, 
        update_result: UpdateResult, 
        session_conversation: List[Dict[str, str]]
    ) -> ToMResult:
        """
        Theory of Mind阶段：深度分析和推理。
        
        Args:
            update_result: Update阶段结果
            session_conversation: 对话内容
            
        Returns:
            ToMResult: 分析结果
        """
        # 简化版本的Theory of Mind分析
        insights = {
            'intent_analysis': self._analyze_user_intent(session_conversation),
            'emotion_analysis': self._analyze_emotion(session_conversation),
            'behavior_patterns': self._analyze_behavior_patterns(update_result),
            'cognitive_state': self._analyze_cognitive_state(session_conversation)
        }
        
        confidence_score = self._calculate_confidence_score(insights)
        
        return ToMResult(
            insights=insights,
            metadata={
                'stage': 'theory_of_mind',
                'analyzed_at': datetime.now().isoformat(),
                'confidence_score': confidence_score
            },
            confidence_score=confidence_score
        )
    
    def _create_updated_memory(
        self, 
        previous_memory: Memory, 
        update_result: UpdateResult, 
        tom_result: ToMResult
    ) -> Memory:
        """创建更新后的Memory对象"""
        new_memory = Memory(
            agent_id=previous_memory.agent_id,
            memory_id=previous_memory.memory_id
        )
        
        # 设置更新后的组件
        new_memory.profile_memory = update_result.updated_profile
        new_memory.event_memory = update_result.updated_events
        
        # 设置Theory of Mind元数据
        new_memory.tom_metadata = {
            'insights': tom_result.insights,
            'confidence_score': tom_result.confidence_score,
            'analysis_metadata': tom_result.metadata
        }
        
        return new_memory
    
    # 辅助方法（简化版本实现）
    
    def _contains_profile_info(self, content: str) -> bool:
        """检测内容是否包含画像信息"""
        profile_keywords = ['我是', '我叫', '年龄', '岁', '学习', '工作', '喜欢', '兴趣']
        return any(keyword in content for keyword in profile_keywords)
    
    def _extract_event_description(self, content: str) -> Optional[str]:
        """提取事件描述"""
        if len(content.strip()) > 5:  # 简单的事件过滤
            return f"用户说：{content}"
        return None
    
    def _analyze_user_intent(self, conversation: List[Dict[str, str]]) -> Dict[str, Any]:
        """分析用户意图"""
        # 简化版本
        user_messages = [msg['content'] for msg in conversation if msg.get('role') == 'user']
        return {
            'primary_intent': 'information_seeking' if '?' in str(user_messages) else 'conversation',
            'secondary_intents': [],
            'confidence': 0.7
        }
    
    def _analyze_emotion(self, conversation: List[Dict[str, str]]) -> Dict[str, Any]:
        """分析情绪状态"""
        # 简化版本
        return {
            'dominant_emotion': 'neutral',
            'emotion_confidence': 0.6,
            'emotion_trajectory': ['neutral']
        }
    
    def _analyze_behavior_patterns(self, update_result: UpdateResult) -> Dict[str, Any]:
        """分析行为模式"""
        return {
            'communication_style': 'direct',
            'information_sharing': 'moderate',
            'engagement_level': 'active' if update_result.events_added > 0 else 'passive'
        }
    
    def _analyze_cognitive_state(self, conversation: List[Dict[str, str]]) -> Dict[str, Any]:
        """分析认知状态"""
        return {
            'knowledge_level': 'intermediate',
            'learning_style': 'interactive',
            'cognitive_load': 'manageable'
        }
    
    def _calculate_confidence_score(self, insights: Dict[str, Any]) -> float:
        """计算总体置信度分数"""
        # 简化版本：基于各项分析的平均置信度
        confidences = []
        for analysis in insights.values():
            if isinstance(analysis, dict) and 'confidence' in analysis:
                confidences.append(analysis['confidence'])
        
        return sum(confidences) / len(confidences) if confidences else 0.5 