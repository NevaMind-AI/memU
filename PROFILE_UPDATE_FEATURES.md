# PersonaLab Profile Update 功能

## 概述

PersonaLab现在支持基于对话内容智能更新agent和user的profile信息。系统使用LLM分析对话内容，提取相关信息，并智能地更新profile，使其能够随着交互逐步完善和丰富。

## 核心功能

### 1. Agent Profile 更新

使用 `update_agent_profile_memory(conversation)` 来更新agent的profile：

```python
from personalab.main import Memory

# 创建memory实例
memory = Memory("my_agent", enable_llm_judgment=True)

# 设置初始profile
memory.agent_memory.profile.set_profile("I am a helpful AI assistant.")

# 基于对话更新profile
conversation = """
User: Can you help me with machine learning?
Agent: Yes! I have experience with PyTorch, scikit-learn, and neural networks.
User: What about data visualization?
Agent: Absolutely! I work with matplotlib, seaborn, and plotly regularly.
"""

updated_profile = memory.update_agent_profile_memory(conversation)
print(f"Updated profile: {updated_profile}")
```

### 2. User Profile 更新

使用 `update_user_profile_memory(user_id, conversation)` 来更新特定用户的profile：

```python
# 获取或创建用户memory
user_id = "data_scientist_alice"
user_memory = memory.get_user_memory(user_id)
user_memory.profile.set_profile("Data scientist working in tech.")

# 基于对话更新用户profile
conversation = """
User: Hi, I'm Alice. I work at Google as a senior data scientist.
Agent: Nice to meet you, Alice!
User: I specialize in recommendation systems and have 8 years of experience.
Agent: That's impressive! Recommendation systems are fascinating.
"""

updated_profile = memory.update_user_profile_memory(user_id, conversation)
print(f"Updated user profile: {updated_profile}")
```

## 技术实现

### LLM驱动的智能更新

系统使用LLM来分析对话内容并智能更新profile：

```python
def _update_profile_with_llm(self, current_profile: str, conversation: str, profile_type: str) -> str:
    """
    使用LLM智能分析对话内容并更新profile
    
    LLM会：
    1. 分析对话中的新信息
    2. 更新已有信息（如果有变化）
    3. 添加新的技能、兴趣或特征
    4. 保持整体结构和语调
    5. 移除过时或矛盾的信息
    """
```

### 更新策略

LLM按照以下规则更新profile：

#### ✅ 会更新的内容
- **新技能和专业知识**: "I have experience with PyTorch"
- **工作背景和经验**: "I work at Google as a data scientist" 
- **教育背景**: "I have a PhD from Stanford"
- **兴趣爱好**: "I enjoy rock climbing and photography"
- **专业领域**: "I specialize in computer vision"

#### ⚪ 不会更新的内容
- **临时状态**: "I'm tired today"
- **具体事件**: "Yesterday I had a meeting"
- **无关信息**: "What's the weather like?"
- **系统消息**: Technical error messages

#### 🔄 会修正的内容
- **矛盾信息**: 如果新信息与现有profile冲突，LLM会进行合理整合
- **过时信息**: 更新职位、技能水平等可能变化的信息

### 回退机制

当LLM不可用时，系统使用基于规则的简单更新方法：

```python
def _simple_profile_update(self, current_profile: str, conversation: str) -> str:
    """
    LLM不可用时的回退方法
    
    查找对话中的关键模式：
    - "I am", "I'm", "My name is"
    - "I work", "I study", "I like"
    - "I specialize", "I focus on"
    等等...
    """
```

## 使用场景

### 1. 渐进式Profile构建

从简单profile开始，通过多次对话逐步丰富：

```python
# 初始profile
memory.agent_memory.profile.set_profile("AI assistant")

# 第一次对话 - 添加编程技能
conversation1 = "User: Can you code? Agent: Yes, I program in Python and JavaScript."
memory.update_agent_profile_memory(conversation1)

# 第二次对话 - 添加机器学习知识
conversation2 = "User: Know ML? Agent: Yes, I work with PyTorch and scikit-learn."
memory.update_agent_profile_memory(conversation2)

# 第三次对话 - 添加专业领域
conversation3 = "User: Any specialization? Agent: I focus on NLP and computer vision."
memory.update_agent_profile_memory(conversation3)
```

### 2. 用户画像构建

逐步了解用户背景和需求：

```python
user_id = "researcher_bob"

# 初始信息
memory.get_user_memory(user_id).profile.set_profile("Research scientist")

# 通过对话了解更多
conversations = [
    "User: I work in biotech. Agent: Interesting field!",
    "User: I have a PhD in Biology. Agent: That's impressive!",
    "User: I use Python for data analysis. Agent: Great tool choice!"
]

for conv in conversations:
    memory.update_user_profile_memory(user_id, conv)
```

### 3. 知识积累和学习

Agent通过对话学习和发现新能力：

```python
# Agent发现自己有新的能力
conversation = """
User: Can you help with quantum computing?
Agent: Actually, yes! I have knowledge about quantum algorithms, Qiskit, and quantum machine learning.
"""

memory.update_agent_profile_memory(conversation)
# Profile现在会包含量子计算相关的技能
```

## 配置和选项

### 启用/禁用LLM更新

```python
# 启用LLM驱动的profile更新（推荐）
memory = Memory("agent_id", enable_llm_judgment=True)

# 禁用LLM，使用基础规则更新
memory = Memory("agent_id", enable_llm_judgment=False)
```

### 自定义LLM实例

```python
from personalab.llm import LLMManager

# 使用自定义LLM
custom_llm = LLMManager.create_quick_setup()
memory = Memory("agent_id", llm_instance=custom_llm)
```

## API 参考

### `update_agent_profile_memory(conversation: str) -> str`

**参数:**
- `conversation`: 包含新信息的对话内容

**返回:**
- 更新后的agent profile字符串

**副作用:**
- 自动更新agent memory中的profile

### `update_user_profile_memory(user_id: str, conversation: str) -> str`

**参数:**
- `user_id`: 用户标识符
- `conversation`: 包含新信息的对话内容

**返回:**
- 更新后的user profile字符串

**副作用:**
- 自动更新指定用户memory中的profile

## 最佳实践

### 1. 定期更新
在重要对话后及时更新profile，保持信息的时效性。

### 2. 验证更新
检查更新后的profile是否合理，必要时可以手动调整。

### 3. 批量处理
对于大量历史对话，可以分批处理避免过载。

### 4. 备份重要Profile
在大规模更新前备份重要的profile信息。

## 示例代码

完整的使用示例请参考：
- `examples/profile_update_demo.py` - 详细演示
- `examples/simple_profile_update_example.py` - 简单示例

## 注意事项

1. **LLM依赖**: 最佳效果需要LLM支持，无LLM时功能有限
2. **内容质量**: 更新质量取决于对话内容的信息密度
3. **隐私考虑**: 敏感信息应谨慎处理
4. **性能影响**: LLM调用会增加延迟，适合异步处理

## 未来扩展

可能的功能扩展：
- Profile版本管理和历史记录
- 自动profile质量评估
- 多模态信息集成（图片、语音等）
- Profile模板和结构化字段
- 智能profile合并和去重 