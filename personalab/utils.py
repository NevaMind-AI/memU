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

    # 基于用户消息类型生成响应
    user_msg_lower = user_message.lower()

    # 如果询问历史或记忆
    if any(word in user_msg_lower for word in ["记得", "还记得", "之前", "历史", "以前"]):
        if events:
            recent_events = events[-3:]  # 最近3个事件
            return f"是的，我记得我们之前讨论过：{'; '.join(recent_events)}。基于这些交流，我了解到您的需求。有什么我可以进一步帮助的吗？"
        else:
            return "这是我们第一次对话，但我很期待了解您的需求并为您提供帮助！"

    # Python学习相关
    if any(word in user_msg_lower for word in ["python", "编程", "代码", "学习"]):
        if "初学者" in user_msg_lower or any("初学者" in insight for insight in insights):
            return "对于Python初学者，我建议从基础语法开始：变量、数据类型、控制结构。然后学习函数和面向对象编程。建议使用Python官方教程和实践项目来巩固知识。"
        else:
            return "Python是一门强大的编程语言。根据您的学习目标，我可以推荐相应的学习路径：数据科学、Web开发、自动化脚本等。您更感兴趣哪个方向？"

    # 机器学习相关
    if any(word in user_msg_lower for word in ["机器学习", "ml", "ai", "人工智能", "算法"]):
        return "机器学习是一个激动人心的领域！建议从以下步骤开始：1) 掌握Python和数学基础，2) 学习NumPy、Pandas、Scikit-learn，3) 理解基本算法，4) 动手做项目。您想了解哪个具体方面？"

    # 项目相关
    if any(word in user_msg_lower for word in ["项目", "实战", "练习", "作品"]):
        skill_level = "初级" if any("初学者" in insight for insight in insights) else "中级"
        if skill_level == "初级":
            return "推荐一些适合初学者的项目：1) 计算器程序，2) 待办事项管理器，3) 简单的数据分析项目，4) 文本处理工具。这些项目能帮您练习基础概念。"
        else:
            return "对于有一定基础的开发者，推荐：1) Web应用（Flask/Django），2) 数据科学项目，3) 机器学习模型，4) API开发。选择与您兴趣相关的方向深入。"

    # 工具和库相关
    if any(word in user_msg_lower for word in ["numpy", "pandas", "tensorflow", "pytorch"]):
        if "numpy" in user_msg_lower or "pandas" in user_msg_lower:
            return "NumPy和Pandas是数据科学的基础库。NumPy提供数值计算能力，Pandas用于数据处理和分析。建议先掌握Pandas，因为它包含了NumPy的大部分功能，更适合日常数据工作。"
        elif "tensorflow" in user_msg_lower or "pytorch" in user_msg_lower:
            return "TensorFlow和PyTorch都是优秀的深度学习框架。对初学者来说，PyTorch更直观易学，TensorFlow更适合生产环境。建议从PyTorch开始学习概念，然后根据需要学习TensorFlow。"

    # 工作相关
    if any(word in user_msg_lower for word in ["工作", "就业", "职业", "面试", "求职"]):
        tech_interests = any(
            keyword in " ".join(events + insights).lower()
            for keyword in ["python", "机器学习", "编程", "技术"]
        )
        if tech_interests:
            return "根据您的技术背景，建议准备以下方面：1) 巩固Python基础和项目经验，2) 准备算法和数据结构，3) 建立GitHub作品集，4) 学习相关框架和工具，5) 练习技术面试题。专注于您感兴趣的技术方向。"
        else:
            return "找工作是个系统工程，建议：1) 明确职业目标，2) 完善简历和作品集，3) 提升相关技能，4) 网络建设和投递简历，5) 面试准备。我可以根据您的具体情况提供更详细的建议。"

    # 默认响应
    if profile:
        return "我理解您的问题。基于我对您的了解，我建议从您感兴趣的领域开始深入。有什么具体的方面需要我详细解释吗？"
    else:
        return "感谢您的问题！我很乐意帮助您。请告诉我更多背景信息，这样我能提供更有针对性的建议。"


def extract_events_from_conversation(messages: List[Dict[str, str]]) -> List[str]:
    """
    从对话消息中提取重要事件

    Args:
        messages: 对话消息列表，每个消息包含role和content

    Returns:
        List[str]: 提取的事件列表
    """
    events = []

    # 事件关键词
    event_keywords = [
        "学习",
        "问题",
        "项目",
        "工作",
        "购买",
        "计划",
        "完成",
        "开始",
        "决定",
        "使用",
        "尝试",
        "创建",
        "开发",
        "研究",
        "分析",
        "设计",
        "实现",
    ]

    # 学习相关的特殊模式
    learning_patterns = [
        r"学习.*?([A-Za-z]+|[\u4e00-\u9fa5]+)",
        r"想要.*?学习",
        r"开始.*?学习",
        r"正在.*?学习",
    ]

    for msg in messages:
        if msg["role"] == "user":
            content = msg["content"]

            # 跳过太短的消息
            if len(content) < 10:
                continue

            # 检查学习模式
            for pattern in learning_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    event = f"用户开始学习{match}"
                    if event not in events:
                        events.append(event)

            # 检查关键词事件
            for keyword in event_keywords:
                if keyword in content:
                    # 创建事件描述，截取关键部分
                    if len(content) > 50:
                        # 找到关键词前后的上下文
                        keyword_pos = content.find(keyword)
                        start = max(0, keyword_pos - 20)
                        end = min(len(content), keyword_pos + 30)
                        context = content[start:end].strip()
                        event = f"用户{keyword}相关: {context}"
                    else:
                        event = f"用户{keyword}相关: {content}"

                    if event not in events and len(event) > 10:
                        events.append(event)
                    break  # 避免一个消息产生多个事件

    return events[:5]  # 最多返回5个事件


def extract_insights_from_conversation(
    messages: List[Dict[str, str]], current_insights: List[str] = None
) -> List[str]:
    """
    从对话消息中提取用户洞察和特征

    Args:
        messages: 对话消息列表
        current_insights: 当前已有的洞察列表

    Returns:
        List[str]: 新的洞察列表
    """
    if current_insights is None:
        current_insights = []

    insights = []

    # 提取所有用户消息
    user_messages = [msg["content"] for msg in messages if msg["role"] == "user"]

    if len(user_messages) < 1:
        return insights

    # 分析文本内容
    all_user_text = " ".join(user_messages).lower()

    # 技术兴趣分析
    technical_keywords = [
        "代码",
        "编程",
        "算法",
        "api",
        "数据库",
        "机器学习",
        "ai",
        "python",
        "java",
        "javascript",
    ]
    business_keywords = ["工作", "项目", "管理", "团队", "业务", "计划", "职业", "公司"]
    learning_keywords = ["学习", "教程", "怎么", "如何", "方法", "步骤", "了解", "掌握"]
    beginner_keywords = ["初学者", "新手", "刚开始", "不会", "不懂", "基础"]
    advanced_keywords = ["高级", "深入", "优化", "架构", "设计模式", "最佳实践"]

    # 检查技术兴趣
    tech_count = sum(1 for keyword in technical_keywords if keyword in all_user_text)
    if tech_count >= 2 and "用户对技术话题感兴趣" not in current_insights:
        insights.append("用户对技术话题感兴趣")

    # 检查商业兴趣
    business_count = sum(1 for keyword in business_keywords if keyword in all_user_text)
    if business_count >= 2 and "用户关注工作和项目管理" not in current_insights:
        insights.append("用户关注工作和项目管理")

    # 检查学习态度
    learning_count = sum(1 for keyword in learning_keywords if keyword in all_user_text)
    if learning_count >= 2 and "用户积极主动学习新知识" not in current_insights:
        insights.append("用户积极主动学习新知识")

    # 检查技能水平
    beginner_count = sum(1 for keyword in beginner_keywords if keyword in all_user_text)
    advanced_count = sum(1 for keyword in advanced_keywords if keyword in all_user_text)

    if beginner_count >= 1 and "用户处于学习初期阶段" not in current_insights:
        insights.append("用户处于学习初期阶段")
    elif advanced_count >= 1 and "用户具有一定技术基础" not in current_insights:
        insights.append("用户具有一定技术基础")

    # 检查具体技术兴趣
    if "python" in all_user_text and "用户对Python编程感兴趣" not in current_insights:
        insights.append("用户对Python编程感兴趣")

    if (
        any(keyword in all_user_text for keyword in ["机器学习", "ai", "算法"])
        and "用户对机器学习领域感兴趣" not in current_insights
    ):
        insights.append("用户对机器学习领域感兴趣")

    if (
        any(keyword in all_user_text for keyword in ["web", "网站", "前端", "后端"])
        and "用户对Web开发感兴趣" not in current_insights
    ):
        insights.append("用户对Web开发感兴趣")

    return insights


def analyze_user_interest_keywords(text: str) -> Dict[str, List[str]]:
    """
    分析用户兴趣关键词

    Args:
        text: 要分析的文本

    Returns:
        Dict[str, List[str]]: 按类别分组的关键词
    """
    result = {"技术": [], "业务": [], "学习": [], "工具": []}

    # 定义关键词库
    keywords_map = {
        "技术": ["编程", "代码", "算法", "数据结构", "设计模式", "架构", "API", "数据库"],
        "业务": ["项目", "管理", "团队", "业务", "产品", "用户", "需求", "工作流"],
        "学习": ["教程", "文档", "书籍", "课程", "练习", "实践", "经验", "技能"],
        "工具": ["python", "java", "javascript", "react", "django", "mysql", "git", "docker"],
    }

    text_lower = text.lower()

    for category, keywords in keywords_map.items():
        for keyword in keywords:
            if keyword in text_lower:
                result[category].append(keyword)

    return result


def generate_learning_path_suggestions(insights: List[str], events: List[str]) -> List[str]:
    """
    基于用户洞察和事件生成学习路径建议

    Args:
        insights: 用户洞察列表
        events: 用户事件列表

    Returns:
        List[str]: 学习路径建议
    """
    suggestions = []

    # 分析用户水平
    is_beginner = any("初期" in insight or "初学者" in insight for insight in insights)
    has_tech_interest = any("技术" in insight for insight in insights)
    loves_python = any("Python" in insight for insight in insights)
    loves_ml = any("机器学习" in insight for insight in insights)

    if is_beginner and has_tech_interest:
        suggestions.extend(
            [
                "建议从Python基础语法开始学习",
                "掌握基本的数据类型和控制结构",
                "学习函数定义和使用",
                "练习简单的编程项目",
            ]
        )

    if loves_python:
        if is_beginner:
            suggestions.extend(
                ["完成Python官方教程", "学习Python标准库的常用模块", "尝试编写小工具和脚本"]
            )
        else:
            suggestions.extend(
                [
                    "深入学习Python高级特性",
                    "掌握面向对象编程和设计模式",
                    "学习Python Web框架（Flask/Django）",
                ]
            )

    if loves_ml:
        prerequisites = ["掌握Python基础", "学习NumPy和Pandas", "了解基本统计概念"]
        ml_path = ["学习Scikit-learn基础", "理解监督学习算法", "实践机器学习项目"]

        if is_beginner:
            suggestions.extend(prerequisites + ml_path)
        else:
            suggestions.extend(ml_path + ["深入学习深度学习框架", "参与开源ML项目"])

    # 去重并限制数量
    unique_suggestions = []
    for suggestion in suggestions:
        if suggestion not in unique_suggestions:
            unique_suggestions.append(suggestion)

    return unique_suggestions[:8]  # 最多8个建议


def format_conversation_summary(messages: List[Dict[str, str]], max_length: int = 100) -> str:
    """
    格式化对话摘要

    Args:
        messages: 对话消息列表
        max_length: 摘要最大长度

    Returns:
        str: 格式化的对话摘要
    """
    if not messages:
        return "Empty conversation"

    # 找到第一个用户消息作为对话主题
    first_user_msg = None
    for msg in messages:
        if msg["role"] == "user":
            first_user_msg = msg["content"]
            break

    if not first_user_msg:
        return f"Conversation with {len(messages)} turns"

    # 创建摘要
    turn_count = len([msg for msg in messages if msg["role"] == "user"])
    summary = f"Conversation with {turn_count} turns: {first_user_msg}"

    # 截断到指定长度
    if len(summary) > max_length:
        summary = summary[: max_length - 3] + "..."

    return summary


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
        context_parts.append(f"用户背景：{profile}")

    # 添加重要事件
    events = memory.get_event_content()
    if events:
        recent_events = events[-3:]  # 最近3个事件
        context_parts.append("重要事件：" + "；".join(recent_events))

    # 添加用户洞察
    insights = memory.get_mind_content()
    if insights:
        recent_insights = insights[-2:]  # 最近2个洞察
        context_parts.append("用户特征：" + "；".join(recent_insights))

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
        context = "## 相关历史对话\n"
        for i, result in enumerate(results, 1):
            context += f"{i}. {result['summary']}\n"

        context += "\n请参考以上历史对话来回答当前问题。"
        return context

    except Exception as e:
        print(f"⚠️ 检索历史失败: {e}")
        return ""


def build_system_prompt(
    memory_manager, conversation_manager, agent_id: str, user_message: str
) -> str:
    """构建包含记忆的系统提示"""
    base_prompt = "你是一个智能助手，能够记住用户的偏好和历史对话。"

    # 添加记忆上下文
    memory_context = get_memory_context(memory_manager, agent_id)
    if memory_context:
        base_prompt += f"\n\n{memory_context}"

    # 添加对话历史上下文
    conversation_context = get_conversation_context(conversation_manager, agent_id, user_message)
    if conversation_context:
        base_prompt += f"\n\n{conversation_context}"

    return base_prompt


def learn_from_conversation(
    memory_manager,
    conversation_manager,
    agent_id: str,
    user_id: str,
    messages: List[Dict[str, str]],
    session_id: Optional[str] = None,
):
    """从对话中学习并更新记忆"""
    try:
        # 1. 记录对话
        if session_id is None:
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        conversation_manager.record_conversation(
            agent_id=agent_id, user_id=user_id, messages=messages, session_id=session_id
        )

        # 2. 提取学习内容
        memory = memory_manager.get_memory_by_agent(agent_id)
        events = extract_events_from_conversation(messages)
        insights = extract_insights_from_conversation(messages, memory.get_mind_content())

        # 3. 更新记忆
        updated = False
        if events:
            memory.update_events(events)
            print(f"📝 学习到事件: {len(events)} 个")
            updated = True

        if insights:
            memory.update_mind(insights)
            print(f"🧠 获得洞察: {len(insights)} 个")
            updated = True

        # 4. 保存记忆
        if updated:
            memory_manager.database.save_memory(memory)

        return updated

    except Exception as e:
        print(f"❌ 学习失败: {e}")
        return False


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
        memory_context.append(f"用户档案: {', '.join(memory.get_profile())}")
    if memory.get_events():
        memory_context.append(f"重要事件: {', '.join(memory.get_events())}")
    if memory.get_mind():
        memory_context.append(f"心理洞察: {', '.join(memory.get_mind())}")

    system_prompt = """你是智能体 {agent_id}，正在与用户 {user_id} 对话。

记忆上下文：
{chr(10).join(memory_context) if memory_context else '暂无记忆信息'}

请基于以上记忆信息，以自然、有帮助的方式回复用户。"""

    # 发送请求
    response = llm_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message},
        ],
    )

    return response.choices[0].message.content
