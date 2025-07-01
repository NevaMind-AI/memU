"""
PersonaLab Persona Class

提供简洁的API来使用PersonaLab的Memory和Memo功能，并集成LLM对话。
"""

import json
from typing import List, Dict, Optional, Union, Any, Callable
from contextlib import contextmanager

from ..memory import Memory
from ..memo import Memo
from ..llm import OpenAIClient, AnthropicClient, CustomLLMClient
from ..config import config

class Persona:
    """PersonaLab核心接口，提供简洁的memory和对话功能
    
    默认使用OpenAI，从.env文件读取API key。
    
    Example:
        # 基础用法（默认OpenAI）
        persona = Persona(agent_id="alice")  # 从.env读取OPENAI_API_KEY
        
        # 或者明确指定LLM类型
        persona = Persona.create_openai(agent_id="alice")
        persona = Persona.create_anthropic(agent_id="bob")
        
        # 使用
        response = persona.chat("我喜欢爬山")
    """
    
    def __init__(
        self, 
        agent_id: str,
        llm_client=None,
        llm_type: str = None,
        llm_function: Callable = None,
        data_dir: str = "data",
        show_retrieval: bool = False,
        **llm_kwargs
    ):
        """初始化Persona
        
        Args:
            agent_id: 智能体ID
            llm_client: 预配置的LLM客户端
            llm_type: LLM类型 ('openai', 'anthropic', 'custom')，默认为'openai'
            llm_function: 自定义LLM函数 (llm_type='custom'时使用)
            data_dir: 数据目录
            show_retrieval: 是否显示检索过程
            **llm_kwargs: LLM客户端的额外参数
        """
        self.agent_id = agent_id
        self.show_retrieval = show_retrieval
        
        # 初始化Memory和Memo
        self.memory = Memory(agent_id=agent_id)
        self.memo = Memo(agent_id=agent_id, data_dir=data_dir)
        
        # 配置LLM客户端
        if llm_client:
            self.llm_client = llm_client
        elif llm_type:
            if llm_type == "openai":
                self.llm_client = self._create_openai_client(**llm_kwargs)
            elif llm_type == "anthropic":
                self.llm_client = self._create_anthropic_client(**llm_kwargs)
            elif llm_type == "custom":
                if not llm_function:
                    raise ValueError("llm_function is required when llm_type='custom'")
                self.llm_client = CustomLLMClient(llm_function=llm_function, **llm_kwargs)
            else:
                raise ValueError(f"Unsupported llm_type: {llm_type}")
        else:
            # 默认使用OpenAI
            self.llm_client = self._create_openai_client(**llm_kwargs)
    
    def _create_openai_client(self, **kwargs):
        """创建OpenAI客户端，从配置中读取API key"""
        openai_config = config.get_llm_config("openai")
        if not openai_config.get("api_key"):
            raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY in .env file")
        
        # 合并配置和用户参数
        client_config = {**openai_config, **kwargs}
        return OpenAIClient(**client_config)
    
    def _create_anthropic_client(self, **kwargs):
        """创建Anthropic客户端，从配置中读取API key"""
        anthropic_config = config.get_llm_config("anthropic")
        if not anthropic_config.get("api_key"):
            raise ValueError("Anthropic API key not found. Please set ANTHROPIC_API_KEY in .env file")
        
        # 合并配置和用户参数
        client_config = {**anthropic_config, **kwargs}
        return AnthropicClient(**client_config)
    

    
    @classmethod
    def create_openai(cls, agent_id: str, api_key: str = None, **kwargs) -> 'Persona':
        """创建使用OpenAI的Persona实例"""
        if api_key:
            client = OpenAIClient(api_key=api_key)
            return cls(agent_id=agent_id, llm_client=client, **kwargs)
        else:
            return cls(agent_id=agent_id, llm_type="openai", **kwargs)
    
    @classmethod  
    def create_anthropic(cls, agent_id: str, api_key: str = None, **kwargs) -> 'Persona':
        """创建使用Anthropic的Persona实例"""
        if api_key:
            client = AnthropicClient(api_key=api_key)
            return cls(agent_id=agent_id, llm_client=client, **kwargs)
        else:
            return cls(agent_id=agent_id, llm_type="anthropic", **kwargs)
    

        
    @classmethod
    def create_custom(cls, agent_id: str, llm_function: Callable, **kwargs) -> 'Persona':
        """创建使用自定义LLM函数的Persona实例"""
        client = CustomLLMClient(llm_function=llm_function)
        return cls(agent_id=agent_id, llm_client=client, **kwargs)
        
    @classmethod
    def create_mock(cls, agent_id: str, **kwargs) -> 'Persona':
        """创建使用Mock LLM的Persona实例（用于测试）"""
        from ..llm.custom_client import create_mock_response
        client = CustomLLMClient(llm_function=create_mock_response)
        return cls(agent_id=agent_id, llm_client=client, **kwargs)

    def chat(self, message: str, learn: bool = True) -> str:
        """与AI对话，自动检索相关记忆并学习"""
        # 1. 检索相关对话
        retrieved_conversations = []
        if self.memo.conversations:
            search_results = self.memo.search_similar_conversations(message, top_k=3)
            retrieved_conversations = search_results
            
            if self.show_retrieval and retrieved_conversations:
                print(f"\n🔍 检索到 {len(retrieved_conversations)} 个相关对话:")
                for i, conv in enumerate(retrieved_conversations, 1):
                    print(f"  {i}. {conv['summary'][:50]}...")
                print()
        
        # 2. 构建带检索内容的消息
        enhanced_message = message
        if retrieved_conversations:
            context = "\n".join([
                f"相关历史: {conv['summary']}" 
                for conv in retrieved_conversations
            ])
            enhanced_message = f"{message}\n\n相关背景:\n{context}"
        
        # 3. 获取memory context
        memory_context = self._get_memory_context()
        
        # 4. 构建系统提示
        system_prompt = f"""你是一个智能助手，拥有关于用户的长期记忆。

用户记忆信息:
{memory_context}

请基于你对用户的了解，提供个性化的回应。"""
        
        # 5. 调用LLM
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": enhanced_message}
        ]
        response = self.llm_client.chat_completion(messages)
        
        # 6. 学习对话（如果启用）
        if learn:
            self._learn_from_conversation(message, response.content)
        
        return response.content

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """搜索相关记忆"""
        return self.memo.search_similar_conversations(query, top_k=top_k)
    
    def add_memory(self, content: str, memory_type: str = "fact") -> None:
        """添加记忆"""
        if memory_type == "fact":
            self.memory.add_facts([content])
        elif memory_type == "preference":
            self.memory.add_preferences([content])
        elif memory_type == "event":
            self.memory.add_events([content])
        elif memory_type == "tom":
            self.memory.add_tom([content])
        else:
            raise ValueError(f"Unsupported memory_type: {memory_type}")
    
    def get_memory(self) -> Dict:
        """获取所有记忆"""
        return {
            "facts": self.memory.get_facts(),
            "preferences": self.memory.get_preferences(), 
            "events": self.memory.get_events(),
            "tom": self.memory.get_tom()
        }
    
    def close(self) -> None:
        """关闭所有资源"""
        self.memory.close()
        self.memo.close()
        if hasattr(self.llm_client, 'close'):
            self.llm_client.close()
    
    @contextmanager
    def session(self):
        """上下文管理器，自动管理资源"""
        try:
            yield self
        finally:
            self.close()
    
    # 内部方法
    def _get_memory_context(self) -> str:
        """获取memory context"""
        context_parts = []
        
        facts = self.memory.get_facts()
        if facts:
            context_parts.append(f"关于用户的事实: {', '.join(facts)}")
        
        preferences = self.memory.get_preferences()
        if preferences:
            context_parts.append(f"用户偏好: {', '.join(preferences)}")
        
        events = self.memory.get_events()
        if events:
            context_parts.append(f"重要事件: {', '.join(events)}")
        
        tom = self.memory.get_tom()
        if tom:
            context_parts.append(f"用户心理模型: {', '.join(tom)}")
        
        return "\n".join(context_parts) if context_parts else "暂无用户记忆信息"
    
    def _learn_from_conversation(self, user_message: str, ai_response: str) -> None:
        """从对话中学习"""
        # 记录对话
        self.memo.add_conversation(user_message, ai_response)
        
        # 提取并学习memory
        learning_prompt = f"""分析以下对话，提取可以学习的信息：

用户: {user_message}
助手: {ai_response}

请提取：
1. 关于用户的新事实
2. 用户的偏好
3. 重要事件
4. 用户的想法/感受

返回JSON格式：
{{"facts": [], "preferences": [], "events": [], "tom": []}}"""
        
        try:
            learning_messages = [{"role": "user", "content": learning_prompt}]
            learning_response = self.llm_client.chat_completion(learning_messages)
            learning_data = json.loads(learning_response.content)
            
            # 添加到memory
            if learning_data.get("facts"):
                self.memory.add_facts(learning_data["facts"])
            if learning_data.get("preferences"):
                self.memory.add_preferences(learning_data["preferences"])
            if learning_data.get("events"):
                self.memory.add_events(learning_data["events"])
            if learning_data.get("tom"):
                self.memory.add_tom(learning_data["tom"])
                
        except Exception as e:
            # 学习失败不影响对话
            if self.show_retrieval:
                print(f"⚠️ 学习失败: {e}") 