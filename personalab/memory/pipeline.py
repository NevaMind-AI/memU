"""
Memory更新Pipeline

使用LLM来进行Memory分析和更新
"""

import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass

from .base import Memory, ProfileMemory, EventMemory
from ..llm import BaseLLMClient, create_llm_client


@dataclass
class ModificationResult:
    """Modification阶段的结果"""
    profile: List[str]  # update_profile 
    events: List[str]   # update_events
    raw_llm_response: str 
    metadata: Dict[str, Any] 


@dataclass
class UpdateResult:
    """Update阶段的结果"""
    profile: ProfileMemory
    events: EventMemory
    profile_updated: bool
    raw_llm_response: str
    metadata: Dict[str, Any]


@dataclass
class ToMResult:
    """Theory of Mind阶段的结果"""
    insights: Dict[str, Any]
    confidence_score: float
    raw_llm_response: str
    metadata: Dict[str, Any]


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
    Memory更新Pipeline
    
    使用LLM完成所有Memory分析和更新任务：
    1. LLM分析对话内容，提取画像更新和事件
    2. LLM更新用户画像
    3. LLM进行Theory of Mind分析
    """
    
    def __init__(self, llm_client: BaseLLMClient = None, **llm_config):
        """
        初始化Pipeline
        
        Args:
            llm_client: LLM客户端实例
            **llm_config: LLM配置参数
        """
        self.llm_client = llm_client
        
        self.llm_config = {
            'temperature': 0.3,  # 较低的temperature保证稳定性
            'max_tokens': 2000,
            **llm_config
        }
    
    def update_with_pipeline(
        self, 
        previous_memory: Memory, 
        session_conversation: List[Dict[str, str]]
    ) -> Tuple[Memory, PipelineResult]:
        """
        通过LLM Pipeline更新Memory
        
        Args:
            previous_memory: 之前的Memory对象
            session_conversation: 当前会话对话内容
            
        Returns:
            Tuple[更新后的Memory对象, Pipeline执行结果]
        """
        # 1. LLM分析阶段：分析对话并提取信息
        modification_result = self.llm_modification_stage(
            previous_memory, session_conversation
        )
        
        # 2. LLM更新阶段：更新画像和事件
        update_result = self.llm_update_stage(
            previous_memory, modification_result
        )
        
        # 3. LLM ToM阶段：深度心理分析
        tom_result = self.llm_theory_of_mind_stage(
            update_result, session_conversation
        )
        
        # 4. 创建新的Memory对象
        new_memory = self._create_updated_memory(
            previous_memory, update_result, tom_result
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
                'llm_model': getattr(self.llm_client, 'model_name', 'unknown'),
                'profile_updated': update_result.profile_updated
            }
        )
        
        return new_memory, pipeline_result
    
    def llm_modification_stage(
        self, 
        previous_memory: Memory, 
        session_conversation: List[Dict[str, str]]
    ) -> ModificationResult:
        """
        LLM分析阶段：让LLM分析对话并提取相关信息
        """
        # 构建LLM prompt
        conversation_text = self._format_conversation(session_conversation)
        current_profile = previous_memory.get_profile_content()
        current_events = previous_memory.get_event_content()
        
        prompt = f"""请分析以下对话内容，提取用户画像更新信息和重要事件。

当前用户画像：
{current_profile if current_profile else "暂无"}

当前事件记录：
{self._format_events(current_events) if current_events else "暂无"}

本次对话内容：
{conversation_text}

请分析对话并提取：
1. 需要更新到用户画像的信息（如个人背景、兴趣爱好、技能特长等）
2. 值得记录的重要事件或对话要点
3. 分析的置信度评分（0-1之间）

请以JSON格式返回结果：
{{
    "profile_updates": ["更新信息1", "更新信息2", ...],
    "events": ["事件1", "事件2", ...],
    "confidence": 0.85
}}"""

        # 调用LLM
        messages = [{"role": "user", "content": prompt}]
        
        try:
            if self.llm_client is None:
                # 没有LLM客户端时的fallback
                raise Exception("No LLM client provided")
                
            response = self.llm_client.chat_completion(
                messages=messages,
                **self.llm_config
            )
            
            if not response.success:
                raise Exception(f"LLM调用失败: {response.error}")
            
            # 解析LLM响应
            try:
                llm_result = json.loads(response.content)
                profile_updates = llm_result.get('profile_updates', [])
                events = llm_result.get('events', [])
                confidence = llm_result.get('confidence', 0.5)
            except json.JSONDecodeError:
                # 如果JSON解析失败，使用备用方案
                logging.warning("LLM响应JSON解析失败，使用备用方案")
                profile_updates = []
                events = []
                confidence = 0.3
            
            return ModificationResult(
                profile=profile_updates,
                events=events,
                raw_llm_response=response.content,
                metadata={
                    'stage': 'llm_modification',
                    'processed_at': datetime.now().isoformat(),
                    'llm_usage': response.usage
                }
            )
            
        except Exception as e:
            logging.error(f"LLM分析阶段失败: {e}")
            # 返回空结果
            return ModificationResult(
                profile=[],
                events=[],
                raw_llm_response=str(e),
                metadata={
                    'stage': 'llm_modification',
                    'processed_at': datetime.now().isoformat(),
                    'error': str(e)
                }
            )
    
    def llm_update_stage(
        self, 
        previous_memory: Memory, 
        modification_result: ModificationResult
    ) -> UpdateResult:
        """
        LLM更新阶段：让LLM更新用户画像
        """
        current_profile = previous_memory.get_profile_content()
        profile_updates = modification_result.profile
        
        # 如果没有画像更新，直接返回
        if not profile_updates:
            return UpdateResult(
                profile=ProfileMemory(current_profile),
                events=EventMemory(
                    events=previous_memory.get_event_content().copy(),
                    max_events=previous_memory.event_memory.max_events
                ),
                profile_updated=False,
                raw_llm_response="No updates needed",
                metadata={
                    'stage': 'llm_update',
                    'updated_at': datetime.now().isoformat(),
                    'profile_updated': False
                }
            )
        
        # 构建画像更新prompt
        prompt = f"""请根据新的信息更新用户画像。

当前用户画像：
{current_profile if current_profile else "暂无"}

新增信息：
{chr(10).join(f"- {update}" for update in profile_updates)}

请整合新信息到用户画像中，生成一个完整、连贯的用户画像描述。
要求：
1. 保持原有信息的准确性
2. 自然地融入新信息
3. 避免重复和冗余
4. 使用第三人称描述
5. 保持简洁明了

请直接返回更新后的完整用户画像，不需要其他格式："""

        # 调用LLM更新画像
        messages = [{"role": "user", "content": prompt}]
        
        try:
            if self.llm_client is None:
                # 没有LLM客户端时的fallback
                raise Exception("No LLM client provided")
                
            response = self.llm_client.chat_completion(
                messages=messages,
                **self.llm_config
            )
            
            if response.success:
                updated_profile_content = response.content.strip()
            else:
                # 如果LLM调用失败，使用简单拼接
                updated_profile_content = current_profile + " " + " ".join(profile_updates)
            
            # 更新事件记忆
            updated_events = EventMemory(
                events=previous_memory.get_event_content().copy(),
                max_events=previous_memory.event_memory.max_events
            )
            
            for event in modification_result.events:
                updated_events.add_event(event)
            
            return UpdateResult(
                profile=ProfileMemory(updated_profile_content),
                events=updated_events,
                profile_updated=bool(profile_updates),
                raw_llm_response=response.content if response.success else "LLM update failed",
                metadata={
                    'stage': 'llm_update',
                    'updated_at': datetime.now().isoformat(),
                    'llm_usage': response.usage if response.success else {},
                    'profile_updated': bool(profile_updates)
                }
            )
            
        except Exception as e:
            logging.error(f"LLM更新阶段失败: {e}")
            # 返回原始内容
            return UpdateResult(
                profile=ProfileMemory(current_profile),
                events=EventMemory(
                    events=previous_memory.get_event_content().copy(),
                    max_events=previous_memory.event_memory.max_events
                ),
                profile_updated=False,
                raw_llm_response=str(e),
                metadata={
                    'stage': 'llm_update',
                    'updated_at': datetime.now().isoformat(),
                    'error': str(e)
                }
            )
    
    def llm_theory_of_mind_stage(
        self, 
        update_result: UpdateResult, 
        session_conversation: List[Dict[str, str]]
    ) -> ToMResult:
        """
        LLM Theory of Mind阶段：让LLM进行深度心理分析
        """
        conversation_text = self._format_conversation(session_conversation)
        
        prompt = f"""请对以下对话进行Theory of Mind分析，深入理解用户的心理状态和行为模式。

对话内容：
{conversation_text}

请从以下维度分析用户：
1. 意图分析：用户的主要目的和动机
2. 情绪分析：用户的情绪状态和变化
3. 行为模式：用户的沟通风格和参与方式
4. 认知状态：用户的知识水平和学习倾向

请以JSON格式返回分析结果：
{{
    "intent_analysis": {{
        "primary_intent": "主要意图",
        "secondary_intents": ["次要意图1", "次要意图2"],
        "confidence": 0.8
    }},
    "emotion_analysis": {{
        "dominant_emotion": "主导情绪",
        "emotion_intensity": "情绪强度(low/medium/high)",
        "emotion_trajectory": "情绪变化趋势",
        "confidence": 0.7
    }},
    "behavior_patterns": {{
        "communication_style": "沟通风格",
        "engagement_level": "参与度",
        "information_sharing": "信息分享倾向",
        "response_pattern": "回应模式"
    }},
    "cognitive_state": {{
        "knowledge_level": "知识水平",
        "learning_style": "学习风格",
        "cognitive_load": "认知负荷",
        "curiosity_level": "好奇心水平"
    }}
}}"""

        # 调用LLM进行ToM分析
        messages = [{"role": "user", "content": prompt}]
        
        try:
            if self.llm_client is None:
                # 没有LLM客户端时的fallback
                raise Exception("No LLM client provided")
                
            response = self.llm_client.chat_completion(
                messages=messages,
                **self.llm_config
            )
            
            if not response.success:
                raise Exception(f"LLM ToM分析失败: {response.error}")
            
            # 解析LLM响应
            try:
                insights = json.loads(response.content)
                # 计算总体置信度
                confidence_scores = []
                for analysis in insights.values():
                    if isinstance(analysis, dict) and 'confidence' in analysis:
                        confidence_scores.append(analysis['confidence'])
                
                overall_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.5
                
            except json.JSONDecodeError:
                logging.warning("LLM ToM响应JSON解析失败，使用默认分析")
                insights = {
                    "intent_analysis": {"primary_intent": "conversation", "confidence": 0.5},
                    "emotion_analysis": {"dominant_emotion": "neutral", "confidence": 0.5},
                    "behavior_patterns": {"communication_style": "standard", "engagement_level": "medium"},
                    "cognitive_state": {"knowledge_level": "intermediate", "learning_style": "adaptive"}
                }
                overall_confidence = 0.5
            
            return ToMResult(
                insights=insights,
                confidence_score=overall_confidence,
                raw_llm_response=response.content,
                metadata={
                    'stage': 'llm_theory_of_mind',
                    'analyzed_at': datetime.now().isoformat(),
                    'llm_usage': response.usage
                }
            )
            
        except Exception as e:
            logging.error(f"LLM ToM分析阶段失败: {e}")
            # 返回默认分析
            return ToMResult(
                insights={
                    "intent_analysis": {"primary_intent": "unknown", "confidence": 0.3},
                    "emotion_analysis": {"dominant_emotion": "neutral", "confidence": 0.3},
                    "behavior_patterns": {"communication_style": "unknown", "engagement_level": "unknown"},
                    "cognitive_state": {"knowledge_level": "unknown", "learning_style": "unknown"}
                },
                confidence_score=0.3,
                raw_llm_response=str(e),
                metadata={
                    'stage': 'llm_theory_of_mind',
                    'analyzed_at': datetime.now().isoformat(),
                    'error': str(e)
                }
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
        new_memory.profile_memory = update_result.profile
        new_memory.event_memory = update_result.events
        
        # 设置Theory of Mind元数据
        new_memory.tom_metadata = {
            'insights': tom_result.insights,
            'confidence_score': tom_result.confidence_score,
            'analysis_metadata': tom_result.metadata,
            'raw_llm_response': tom_result.raw_llm_response
        }
        
        return new_memory
    
    def _format_conversation(self, conversation: List[Dict[str, str]]) -> str:
        """格式化对话内容"""
        formatted_lines = []
        for msg in conversation:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            formatted_lines.append(f"{role}: {content}")
        return "\n".join(formatted_lines)
    
    def _format_events(self, events: List[str]) -> str:
        """格式化事件列表"""
        if not events:
            return "暂无"
        return "\n".join(f"- {event}" for event in events[-5:])  # 只显示最近5个事件 