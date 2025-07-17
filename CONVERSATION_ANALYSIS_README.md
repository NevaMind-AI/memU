# Enhanced Conversation Analysis for MemU

MemU现在支持从对话中自动提取和组织**6种类型**的内存信息到独立的 `.md` 文件中。

## 🎯 支持的内存类型

### 1. **Profile** (`profile.md`)
- 角色基本信息和档案
- 个人特征和背景
- 从对话中更新角色信息

### 2. **Events** (`event.md`) 
- 日常活动和互动记录
- 具体的对话和事件
- 时间序列的活动记录

### 3. **Reminders** (`reminder.md`) ✨ 新增
- 待办事项和任务
- 预约和时间安排
- 截止日期和重要提醒

### 4. **Important Events** (`important_event.md`) ✨ 新增
- 重要人生事件和里程碑
- 职业成就和重大变化
- 有意义的个人时刻

### 5. **Interests** (`interests.md`) ✨ 新增
- 兴趣爱好和偏好
- 娱乐活动和创意追求
- 技术学习和社交活动

### 6. **Study** (`study.md`) ✨ 新增
- 学习目标和教育活动
- 课程和认证进度
- 书籍和学习资源

## 🚀 如何使用

### 基本用法

```python
from memu import MemoryAgent
from memu.llm import AzureOpenAIClient

# 初始化带LLM的MemoryAgent
llm_client = AzureOpenAIClient()
agent = MemoryAgent(llm_client=llm_client, memory_dir="memory")

# 分析对话并更新所有内存类型
result = agent.update_character_memory(
    character_name="Alice",
    conversation="今天我获得了晋升，需要学习新的管理技能...",
    session_date="2024-03-20"
)

# 查看更新结果
if result["success"]:
    print("✅ 对话分析成功!")
    print(f"Profile更新: {result['profile_updated']}")
    print(f"Events更新: {result['events_updated']}")
    print(f"Reminders更新: {result['reminders_updated']}")
    print(f"Important Events更新: {result['important_events_updated']}")
    print(f"Interests更新: {result['interests_updated']}")
    print(f"Study更新: {result['study_updated']}")
```

### 手动更新特定文件

```python
from memu import MemoryFileManager

file_manager = MemoryFileManager("memory")

# 直接写入特定类型的内存文件
file_manager.write_reminders("Alice", "- 下周一参加会议\n- 完成项目报告")
file_manager.write_interests("Alice", "## 技术学习\n- Python编程\n- 机器学习")
file_manager.write_study("Alice", "## 当前课程\n- AWS认证准备")

# 追加内容
file_manager.append_important_events("Alice", "2024-03-20: 获得高级工程师晋升")
```

## 📝 提示词模板

每种内存类型都有专门的提示词模板用于从对话中提取相关信息：

- `memu/prompts/analyze_session_for_reminders.txt`
- `memu/prompts/analyze_session_for_important_events.txt` 
- `memu/prompts/analyze_session_for_interests.txt`
- `memu/prompts/analyze_session_for_study.txt`

这些模板确保了一致性和高质量的信息提取。

## 🔧 工具函数

新增的MemoryAgent工具函数：

```python
# 读取特定类型的内存
agent.read_character_reminders("Alice")
agent.read_character_important_events("Alice")
agent.read_character_interests("Alice")
agent.read_character_study("Alice")

# 通用读取方法
agent.read_memory_file("Alice", "reminder")
agent.read_memory_file("Alice", "interests")

# 更新特定类型的内存
agent.update_memory_file("Alice", "reminder", "新的提醒内容", append=True)
```

## 📊 运行示例

### 1. 文件类型演示
```bash
cd examples
python memory_file_types_example.py
```

### 2. 对话分析演示 (需要LLM API密钥)
```bash
cd examples
export OPENAI_API_KEY="your_api_key"  # 或 AZURE_OPENAI_API_KEY
python conversation_analysis_example.py
```

## 🔍 文件组织

每个角色会生成6个独立的 `.md` 文件：

```
memory/
├── alice_profile.md          # 角色档案
├── alice_event.md           # 事件记录
├── alice_reminder.md        # 提醒事项
├── alice_important_event.md # 重要事件
├── alice_interests.md       # 兴趣爱好
└── alice_study.md          # 学习信息
```

## 💡 智能分析特性

- **上下文感知**: 只提取新的、未重复的信息
- **自动分类**: 智能识别信息类型并归档到正确文件
- **时间感知**: 自动添加日期和时间戳
- **结构化输出**: 使用统一的Markdown格式组织信息
- **增量更新**: 新信息追加到现有内容，不覆盖历史记录

## 🔄 向后兼容性

- ✅ 原有的 `profile.md` 和 `event.md` 功能完全保留
- ✅ 所有现有API接口继续工作
- ✅ 新功能是渐进式增强，不影响现有代码
- ✅ 支持文件存储和数据库存储两种模式

## 🎉 使用效果

使用新的conversation分析功能后，MemU能够：

1. **智能分类信息** - 自动识别对话中的不同信息类型
2. **结构化存储** - 将信息有序地组织到相应文件中
3. **避免重复** - 只提取新的、未记录的信息
4. **保持历史** - 所有更新都是增量的，保留完整记录
5. **提供洞察** - 通过分类存储，更容易理解角色的完整画像

这大大提升了MemU在个人助手、客服系统、角色对话等场景中的实用性！ 