# Meta Agent System - Modular Architecture

MemU的Meta Agent系统采用完全模块化的设计，通过固定的工作流程确保一致性和可预测性。系统现在由独立的专业agents组成，每个agent都有明确的职责。

## 系统架构

```
Conversation → ActivityAgent → activity.md → ProfileAgent, EventAgent, etc. → Memory Files → Embeddings
```

### 固定工作流程

1. **ActivityAgent** (优先级: 10) - 处理原始对话，生成activity.md
2. **ProfileAgent** (优先级: 5) - 从activity.md提取角色信息
3. **EventAgent** (优先级: 4) - 从activity.md记录事件
4. **ReminderAgent** (优先级: 3) - 从activity.md提取提醒事项
5. **InterestAgent** (优先级: 2) - 从activity.md记录兴趣爱好
6. **StudyAgent** (优先级: 1) - 从activity.md提取学习信息
7. **Custom Agents** - 自定义agents按优先级执行

### 核心组件

1. **Meta Agent** - 纯粹的协调器，负责：
   - 管理agent执行顺序
   - 协调文件依赖关系
   - 处理错误和状态监控
   - 生成embeddings

2. **ActivityAgent** - 第一个执行的agent，负责：
   - 处理原始conversation文本
   - 生成标准化的activity.md摘要
   - 为其他agents提供统一的输入格式

3. **Specialized Agents** - 专业化agents，负责：
   - 从activity.md提取特定类型信息
   - 生成对应的内存文件
   - 维护各自的专业领域

## 快速开始

### 1. 初始化Meta Agent

```python
from memu.memory import MetaAgent
from memu.llm import OpenAIClient

# 初始化LLM客户端
llm_client = OpenAIClient()

# 初始化Meta Agent
meta_agent = MetaAgent(
    llm_client=llm_client,
    memory_dir="memory",
    agents_dir="agents",
    use_database=True  # 或 False 使用文件存储
)
```

### 2. 处理Conversation

```python
# 处理对话 - 所有agents自动按序执行
results = meta_agent.process_conversation(
    conversation="User与Character的对话内容",
    character_name="Alice",
    session_date="2024-01-15"
)

# 查看结果
print(f"Activity摘要: {results['activity_summary'][:200]}...")
print(f"生成的文件: {list(results['agent_outputs'].keys())}")
print(f"Embeddings: {results['embeddings_generated']}")
```

## 默认Agents

系统自动注册以下agents，按优先级执行：

| Agent名称 | 优先级 | 输入 | 输出文件 | 描述 |
|-----------|--------|------|----------|------|
| activity_agent | 10 | 原始conversation | activity.md | 创建活动摘要 |
| profile_agent | 5 | activity.md | profile.md | 提取角色基本信息 |
| event_agent | 4 | activity.md | events.md | 记录事件和活动 |
| reminder_agent | 3 | activity.md | reminders.md | 提取提醒和待办事项 |
| interest_agent | 2 | activity.md | interests.md | 记录兴趣爱好 |
| study_agent | 1 | activity.md | study.md | 学习目标和教育信息 |

## 创建自定义Agent

### 方法1: 通过代码注册

```python
# 定义prompt内容（注意：这里的{conversation}实际上是activity.md的内容）
custom_prompt = """Task: 从活动摘要中提取{character_name}的健康信息。

Instructions:
1. 分析活动摘要中的健康和健身相关内容
2. 提取运动、饮食、医疗等信息
3. 组织成结构化格式

Input:
- Activity Summary: {conversation}
- Character: {character_name}
- Session Date: {session_date}

Output Format:
## 运动健身
[运动活动记录]

## 饮食营养
[饮食相关信息]

健康信息:"""

# 注册agent
agent_config = meta_agent.register_new_agent_from_prompt(
    name="health_agent",
    prompt_content=custom_prompt,
    description="从活动摘要提取健康信息",
    output_file="health.md",
    input_dependencies=["activity.md"],  # 依赖于ActivityAgent的输出
    priority=6  # 设置执行优先级
)
```

### 方法2: 通过文件注册

1. 创建prompt文件 `prompts/agent_social.txt`:

```text
Task: 从活动摘要中分析{character_name}的社交互动。

Instructions:
1. 分析活动摘要中的社交活动和人际互动
2. 识别提到的人物和关系
3. 记录社交模式和变化

Input:
- Activity Summary: {conversation}
- Character: {character_name}
- Session Date: {session_date}

Output Format:
## 人际交往
[与他人的互动记录]

## 社交活动
[社交事件和聚会]

社交分析:
```

2. 注册agent:

```python
from memu.memory import get_agent_registry

registry = get_agent_registry()
registry.register_agent(
    name="social_agent",
    prompt_file="agent_social",
    description="分析社交互动和人际关系",
    output_file="social.md",
    input_dependencies=["activity.md"],
    priority=4
)
```

## Agent配置

每个agent都有以下配置属性：

```python
@dataclass
class AgentConfig:
    name: str                      # Agent唯一名称
    prompt_file: str              # Prompt文件名（不含.txt）
    description: str              # Agent描述
    output_file: str              # 输出文件名
    input_dependencies: List[str] # 依赖的输入文件（通常是["activity.md"]）
    embedding_required: bool      # 是否需要生成embedding
    priority: int                 # 执行优先级（数字越大越先执行）
```

## 执行流程详解

### 第一阶段：ActivityAgent

```python
# ActivityAgent接收原始conversation
conversation = "User: Hi! Character: Hello, I went running today..."

# ActivityAgent处理并生成activity.md
activity_summary = """
## Activity Summary for 2024-01-15

### Overview
Character went for a morning run and had several conversations...

### Detailed Activities  
- 07:00: 5-mile morning run, completed in 42 minutes
- 08:00: Healthy breakfast with oatmeal and berries
- 09:00: Work presentation about Q3 marketing strategy
...
"""
```

### 第二阶段：Specialized Agents

```python
# 所有其他agents接收activity.md作为输入
# ProfileAgent从activity.md提取角色信息
# EventAgent从activity.md记录事件
# ReminderAgent从activity.md提取待办事项
# etc.
```

### 第三阶段：Embedding生成

```python
# 为所有新生成的内容自动生成embeddings
# 存储到数据库或文件系统
```

## 工作流程监控

### 查看执行状态

```python
# 检查agent状态
status = meta_agent.get_agent_status()
print(f"总agents数: {status['total_agents']}")
print(f"有问题的agents: {status['agents_with_issues']}")

# 查看执行顺序
agents = meta_agent.agent_registry.get_agents_by_priority()
for i, agent in enumerate(agents, 1):
    print(f"{i}. {agent.name}: {agent.description}")
    print(f"   Input: {agent.input_dependencies or ['Raw conversation']}")
    print(f"   Output: {agent.output_file}")
```

### 处理结果分析

```python
results = meta_agent.process_conversation(conversation, character_name)

# 查看每个agent的输出
for agent_name, output in results['agent_outputs'].items():
    print(f"\n{agent_name}:")
    print(f"  Output length: {len(output)} characters")
    print(f"  Preview: {output[:200]}...")

# 查看错误（如果有）
if results['errors']:
    for error in results['errors']:
        print(f"Error: {error}")
```

## Prompt编写指南

### ActivityAgent Prompt结构

ActivityAgent的prompt应该：
- 接收原始conversation作为输入
- 生成结构化的活动摘要
- 为其他agents提供足够的信息

```text
Task: Create a comprehensive activity summary from the conversation session for {character_name}.

Instructions:
1. Analyze the entire conversation to capture ALL activities, interactions, and events
2. Create a detailed summary organized by topics and chronology
3. Include specific details: who, what, when, where, why
4. Preserve important quotes and exact details when relevant
5. Use clear, structured markdown format for readability

Input:
- Conversation: {conversation}
- Character: {character_name}
- Session Date: {session_date}

Output Format:
## Activity Summary for {session_date}
[详细的活动摘要]

Activity Summary:
```

### Specialized Agent Prompt结构

其他agents的prompt应该：
- 接收activity.md作为输入（通过{conversation}变量）
- 专注于特定类型的信息提取
- 避免重复已有信息

```text
Task: 从活动摘要中提取{character_name}的特定类型信息。

Instructions:
1. 分析活动摘要中与[特定领域]相关的内容
2. 只提取新的、相关的信息
3. 使用结构化格式组织输出

Input:
- Activity Summary: {conversation}  # 这里是activity.md的内容
- Character: {character_name}
- Session Date: {session_date}
- Existing [Type]: {existing_[type]}  # 现有相关信息

Output Format:
[特定的输出格式]
```

## 最佳实践

### 1. Agent设计原则

- **单一职责**: 每个agent只负责一个特定领域
- **依赖明确**: 明确声明对其他文件的依赖
- **输出标准**: 使用一致的markdown格式
- **增量更新**: 只添加新信息，避免重复

### 2. 优先级设置

- **ActivityAgent**: 优先级10（最高，必须最先执行）
- **核心agents**: 优先级5-8（profile, events等）
- **辅助agents**: 优先级1-4（interests, study等）
- **自定义agents**: 根据重要性设置

### 3. 错误处理

```python
# 系统会自动处理单个agent的失败
# 不会影响其他agents的执行
results = meta_agent.process_conversation(conversation, character_name)

# 检查错误
for error in results['errors']:
    if 'activity_agent' in error:
        print("ActivityAgent失败会影响所有后续agents")
    else:
        print(f"独立agent失败: {error}")
```

## 高级特性

### 1. 条件依赖

```python
# Agent可以依赖多个文件
registry.register_agent(
    name="summary_agent",
    prompt_file="create_comprehensive_summary",
    description="创建基于所有信息的综合摘要",
    output_file="summary.md",
    input_dependencies=["activity.md", "profile.md", "events.md"],
    priority=0  # 最后执行
)
```

### 2. 自定义workflow

```python
# 可以创建特殊的agents链
# 例如：financial_summary_agent → financial_analysis_agent
```

### 3. 动态agent加载

```python
# 在运行时动态添加agents
# 系统会自动按优先级重新排序
```

## 系统优势

### 与之前架构的对比

| 特性 | 之前 | 现在 |
|------|------|------|
| Meta Agent职责 | 生成activity + 管理agents | 纯粹协调 |
| 工作流程 | 灵活但不可预测 | 固定且可预测 |
| Agent独立性 | 部分独立 | 完全独立 |
| 输入标准化 | 各种输入源 | activity.md统一输入 |
| 错误影响 | 可能连锁失败 | 隔离失败 |

### 主要优势

1. **可预测性**: 固定的执行顺序，易于调试和维护
2. **模块化**: 每个agent完全独立，职责明确
3. **标准化**: ActivityAgent为所有其他agents提供统一输入
4. **可扩展性**: 轻松添加新agents而不影响现有流程
5. **容错性**: 单个agent失败不影响整体流程
6. **一致性**: 所有agents使用相同的输入格式

## 总结

新的Meta Agent系统通过固定的工作流程和明确的职责分工，提供了一个更加稳定、可预测和易于扩展的架构。开发者只需专注于编写高质量的prompts，系统会自动处理执行顺序、依赖管理和错误恢复。

通过ActivityAgent作为第一步，确保了所有后续agents都有标准化、高质量的输入，从而提高了整个系统的一致性和可靠性。 