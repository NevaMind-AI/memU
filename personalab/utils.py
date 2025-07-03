#!/usr/bin/env python3
"""
PersonaLab 工具模块

包含PersonaLab项目中重复使用的通用函数和工具，提供：
1. 对话处理和分析工具
2. Memory管理工具
3. AI响应模拟和学习功能

作者: PersonaLab团队
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from .config.database import get_database_manager
from personalab.memo import ConversationManager
from personalab.memory import Memory, MemoryClient


def simulate_ai_response(
    memory: Memory, user_message: str, conversation_history: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    模拟AI响应（用于演示，实际应用中应使用真实的LLM API）

    Args:
        memory: Memory对象，包含用户档案和历史
        user_message: 用户消息
        conversation_history: 可选的对话历史

    Returns:
        str: 模拟的AI响应
    """
    # 获取用户档案信息
    profile = memory.get_profile_content()
    events = memory.get_event_content()
    insights = memory.get_mind_content()

    # Generate response based on user message type
    user_msg_lower = user_message.lower()

    # If asking about history or memory
    if any(word in user_msg_lower for word in ["remember", "still remember", "before", "history", "previously"]):
        if events:
            recent_events = events[-3:]
            return f"Yes, I remember we discussed: {'; '.join(recent_events)}. Based on these conversations, I understand your needs. How else can I help you?"
        else:
            return "This is our first conversation, but I'm looking forward to learning about your needs and helping you!"

    # Python learning related
    if any(word in user_msg_lower for word in ["python", "programming", "code", "learning"]):
        if "beginner" in user_msg_lower or any("beginner" in insight for insight in insights):
            return "For Python beginners, I recommend starting with basic syntax: variables, data types, control structures. Then learn functions and object-oriented programming. Use the official Python tutorial and practice projects to consolidate your knowledge."
        else:
            return "Python is a powerful programming language. Based on your learning goals, I can recommend relevant learning paths: data science, web development, automation scripts, etc. Which direction are you more interested in?"

    # Machine learning related
    if any(word in user_msg_lower for word in ["machine learning", "ml", "ai", "artificial intelligence", "algorithm"]):
        return "Machine learning is an exciting field! I suggest starting with: 1) mastering Python and math basics, 2) learning NumPy, Pandas, Scikit-learn, 3) understanding basic algorithms, 4) working on projects. Which specific aspect do you want to know more about?"

    # Project related
    if any(word in user_msg_lower for word in ["project", "practice", "exercise", "work"]):
        skill_level = "beginner" if any("beginner" in insight for insight in insights) else "intermediate"
        if skill_level == "beginner":
            return "Recommended projects for beginners: 1) Calculator program, 2) To-do list manager, 3) Simple data analysis project, 4) Text processing tool. These projects help you practice basic concepts."
        else:
            return "For developers with some foundation, recommended: 1) Web applications (Flask/Django), 2) Data science projects, 3) Machine learning models, 4) API development. Choose a direction related to your interests to go deeper."

    # Tools and libraries related
    if any(word in user_msg_lower for word in ["numpy", "pandas", "tensorflow", "pytorch"]):
        if "numpy" in user_msg_lower or "pandas" in user_msg_lower:
            return "NumPy and Pandas are fundamental libraries for data science. NumPy provides numerical computation capabilities, Pandas is used for data processing and analysis. It's recommended to master Pandas first, as it includes most of NumPy's features and is more suitable for daily data work."
        elif "tensorflow" in user_msg_lower or "pytorch" in user_msg_lower:
            return "TensorFlow and PyTorch are both excellent deep learning frameworks. For beginners, PyTorch is more intuitive and easier to learn, while TensorFlow is more suitable for production environments. Start with PyTorch to learn concepts, then learn TensorFlow as needed."

    # Work related
    if any(word in user_msg_lower for word in ["work", "job", "career", "interview", "job hunting"]):
        tech_interests = any(
            keyword in " ".join(events + insights).lower()
            for keyword in ["python", "machine learning", "programming", "technology"]
        )
        if tech_interests:
            return "Based on your technical background, I recommend preparing the following: 1) Strengthen your Python basics and project experience, 2) Prepare algorithms and data structures, 3) Build a GitHub portfolio, 4) Learn relevant frameworks and tools, 5) Practice technical interview questions. Focus on the technical direction you are interested in."
        else:
            return "Job hunting is a systematic project. Suggestions: 1) Clarify career goals, 2) Improve your resume and portfolio, 3) Enhance relevant skills, 4) Network and submit resumes, 5) Prepare for interviews. I can provide more detailed advice based on your specific situation."

    # Default response
    if profile:
        return "I understand your question. Based on what I know about you, I suggest delving into the areas you are interested in. Is there anything specific you need me to explain in detail?"
    else:
        return "Thank you for your question! I'm happy to help you. Please tell me more background information so I can provide more targeted advice."




def validate_conversation_data(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    验证对话数据的完整性和格式

    Args:
        messages: 对话消息列表

    Returns:
        Dict[str, Any]: 验证结果，包含is_valid和errors
    """
    result = {"is_valid": True, "errors": [], "warnings": []}

    if not messages:
        result["is_valid"] = False
        result["errors"].append("对话消息列表为空")
        return result

    for i, msg in enumerate(messages):
        # 检查必需字段
        if not isinstance(msg, dict):
            result["is_valid"] = False
            result["errors"].append(f"消息 {i}: 不是字典格式")
            continue

        if "role" not in msg:
            result["is_valid"] = False
            result["errors"].append(f"消息 {i}: 缺少role字段")

        if "content" not in msg:
            result["is_valid"] = False
            result["errors"].append(f"消息 {i}: 缺少content字段")

        # 检查role值
        if msg.get("role") not in ["user", "assistant", "system"]:
            result["warnings"].append(f"消息 {i}: role值不标准: {msg.get('role')}")

        # 检查内容长度
        content = msg.get("content", "")
        if len(content) > 10000:
            result["warnings"].append(f"消息 {i}: 内容过长 ({len(content)} 字符)")
        elif len(content.strip()) == 0:
            result["warnings"].append(f"消息 {i}: 内容为空")

    return result


# ===== Memory管理工具函数 =====


def create_memory_manager():
    """创建Memory管理器 (PostgreSQL-only)"""

    db_manager = get_database_manager()
    return MemoryClient(db_manager=db_manager)


def create_conversation_manager(enable_embeddings: bool = True):
    """创建对话管理器 (PostgreSQL-only)

    Args:
        enable_embeddings: 是否启用向量嵌入
    """

    db_manager = get_database_manager()
    return ConversationManager(db_manager=db_manager, enable_embeddings=enable_embeddings)


def setup_agent_memory(memory_manager, agent_id: str, initial_profile: str = ""):
    """设置agent的初始记忆"""
    memory = memory_manager.get_memory_by_agent(agent_id)
    if initial_profile:
        memory.update_profile(initial_profile)
        memory_manager.database.save_memory(memory)
    return memory


def get_memory_context(memory_manager, agent_id: str) -> str:
    """获取记忆上下文用于AI提示"""
    memory = memory_manager.get_memory_by_agent(agent_id)
    context_parts = []

    # 添加用户档案
    profile = memory.get_profile_content()
    if profile:
        context_parts.append(f"user background: {profile}")

    # 添加重要事件
    events = memory.get_event_content()
    if events:
        recent_events = events[-3:]  # 最近3个事件
        context_parts.append("important events: " + ";".join(recent_events))

    # 添加用户洞察
    insights = memory.get_mind_content()
    if insights:
        recent_insights = insights[-2:]  # 最近2个洞察
        context_parts.append("user characteristics: " + ";".join(recent_insights))

    return "\n\n".join(context_parts)


def get_conversation_context(
    conversation_manager, agent_id: str, query: str, limit: int = 2
) -> str:
    """获取相关的历史对话上下文"""
    try:
        # 搜索相关对话
        results = conversation_manager.search_similar_conversations(
            agent_id=agent_id, query=query, limit=limit, similarity_threshold=0.6
        )

        if not results:
            return ""

        # 构建上下文
        context = "## Related historical conversation\n"
        for i, result in enumerate(results, 1):
            context += f"{i}. {result['summary']}\n"

        context += "\nPlease refer to the above historical conversation to answer the current question."
        return context

    except Exception as e:
        print(f"⚠️ 检索历史失败: {e}")
        return ""


def build_system_prompt(
    memory_manager, conversation_manager, agent_id: str, user_message: str
) -> str:
    """构建包含记忆的系统提示"""
    base_prompt = "You are a smart assistant, able to remember user preferences and historical conversations."

    # 添加记忆上下文
    memory_context = get_memory_context(memory_manager, agent_id)
    if memory_context:
        base_prompt += f"\n\n{memory_context}"

    # 添加对话历史上下文
    conversation_context = get_conversation_context(conversation_manager, agent_id, user_message)
    if conversation_context:
        base_prompt += f"\n\n{conversation_context}"

    return base_prompt


def get_memory_summary(memory_manager, agent_id: str) -> Dict[str, Any]:
    """获取记忆摘要"""
    memory = memory_manager.get_memory_by_agent(agent_id)

    return {
        "agent_id": agent_id,
        "profile": memory.get_profile_content(),
        "events": memory.get_event_content(),
        "insights": memory.get_mind_content(),
    }


def cleanup_memory_resources(memory_manager, conversation_manager):
    """清理资源"""
    try:
        if hasattr(memory_manager, "close"):
            memory_manager.close()
        if hasattr(conversation_manager, "close"):
            conversation_manager.close()
    except Exception:
        pass


def chat_with_memory(llm_client, memory: Memory, message: str, agent_id: str, user_id: str) -> str:
    """一体化记忆聊天函数

    Args:
        llm_client: LLM客户端实例
        memory: 记忆对象
        message: 用户消息
        agent_id: 智能体ID (required)
        user_id: 用户ID (required)

    Returns:
        AI回复
    """
    # 获取记忆上下文
    # 获取记忆上下文（暂时不使用stats）

    # 构建系统提示词
    memory_context = []
    if memory.get_profile():
        memory_context.append(f"user profile: {', '.join(memory.get_profile())}")
    if memory.get_events():
        memory_context.append(f"important events: {', '.join(memory.get_events())}")
    if memory.get_mind():
        memory_context.append(f"psychological insights: {', '.join(memory.get_mind())}")

    system_prompt = """You are smart assistant {agent_id}, talking with user {user_id}.

Memory context:
{chr(10).join(memory_context) if memory_context else 'No memory information'}

Please reply to the user based on the above memory information in a natural and helpful way."""

    # 发送请求
    response = llm_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message},
        ],
    )

    return response.choices[0].message.content
