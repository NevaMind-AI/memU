# MemU配置系统（简化版本）

MemU的简化配置系统：**activity.md是唯一必须的核心文件**，记录所有内容。其他文件都是可选的，从activity中提取信息。

## 📁 目录结构

```
memu/config/
├── __init__.py                 # 配置模块初始化
├── markdown_config.py          # Markdown文件配置（核心）
├── prompts/                    # Prompt模板目录
│   ├── __init__.py
│   ├── prompt_loader.py
│   ├── agent_activity.txt
│   ├── analyze_session_for_profile.txt
│   ├── analyze_session_for_events.txt
│   ├── analyze_session_for_reminders.txt
│   ├── analyze_session_for_interests.txt
│   ├── analyze_session_for_study.txt
│   └── system_message.txt
└── README.md                   # 本文档
```

## 🎯 核心配置理念

### 简化配置原则

1. **Activity是核心** - 唯一必须的文件，记录所有对话和活动内容
2. **其他都是可选** - 从activity中提取信息，根据需要启用
3. **配置足够简单** - 不复杂的依赖关系，易于理解和使用
4. **智能自动检测** - 自动识别文件类型和内容分类

### `markdown_config.py`

这是MemU配置系统的核心文件，采用简化设计：

- **1个必须文件** - activity.md记录所有内容  
- **5个可选文件** - 从activity中提取专门信息
- **简单配置结构** - 易于理解和修改
- **智能检测功能** - 自动分类markdown文件

## 📋 文件类型配置

### 🔥 必须文件（核心）

#### Activity (activity.md) - 🔥 **必须**
- **作用**: 记录所有对话和活动内容的完整记录
- **依赖**: 无（核心文件，所有信息的源头）
- **Prompt**: `agent_activity.txt`
- **内容**: 完整记录所有对话、活动、想法和重要信息

### ⚙️ 可选文件（扩展）

以下文件都是可选的，从activity.md中提取特定类型的信息：

#### Profile (profile.md) - ⚙️ 可选
- **作用**: 从activity中提取角色基本信息
- **内容**: 角色基本信息档案

#### Events (events.md) - ⚙️ 可选  
- **作用**: 从activity中提取重要事件记录
- **内容**: 重要事件和里程碑

#### Reminders (reminders.md) - ⚙️ 可选
- **作用**: 从activity中提取待办事项和提醒
- **内容**: 任务清单和提醒事项

#### Interests (interests.md) - ⚙️ 可选
- **作用**: 从activity中提取兴趣爱好信息
- **内容**: 兴趣爱好和偏好记录

#### Study (study.md) - ⚙️ 可选
- **作用**: 从activity中提取学习相关信息
- **内容**: 学习计划和教育目标

## 🔗 简化处理流程

```
原始对话 → activity.md (必须，记录所有内容)
             ↓
          可选文件 (根据需要从activity中提取)
           ├── profile.md
           ├── events.md  
           ├── reminders.md
           ├── interests.md
           └── study.md
```

**简化流程说明**:
1. **activity.md** - 唯一必须的文件，记录所有对话和活动内容
2. **可选文件** - 都从activity.md中提取信息，没有复杂的依赖关系
3. **按需启用** - 根据实际需要选择生成哪些可选文件

## 🎯 自动检测功能

配置系统支持根据文件名和内容自动检测文件类型：

### 文件名检测关键词
- **profile**: profile, bio, character, person, about, 档案, 信息
- **event**: event, history, timeline, log, diary, 事件, 历史
- **reminder**: reminder, todo, task, note, 提醒, 任务
- **interests**: interest, hobby, like, preference, 兴趣, 爱好
- **study**: study, learn, course, education, skill, 学习, 课程
- **activity**: activity, action, summary, 日志, 记录

### 内容模式检测
- **profile**: "name:", "age:", "occupation:", "born", "lives in", "personality"
- **event**: "date:", "happened", "occurred", "milestone", "important", "achieved"
- **reminder**: "remember to", "don't forget", "deadline", "due", "urgent"
- **interests**: "likes", "enjoys", "hobby", "interested in", "passion", "favorite"
- **study**: "learning", "studying", "course", "lesson", "skill", "education"
- **activity**: "today", "yesterday", "conversation", "talked", "did", "went"

## 🔧 简化使用方式

### 1. 基本配置查询

```python
from memu.config import get_simple_summary, get_required_files, get_optional_files

# 获取简化配置摘要
summary = get_simple_summary()
print(summary['processing_principle'])  # activity文件记录所有内容

# 查看必须和可选文件
required = get_required_files()     # ['activity']
optional = get_optional_files()    # ['profile', 'event', 'reminder', 'interests', 'study']
```

### 2. 智能文件检测

```python
from memu.config import detect_file_type, is_required_file

# 自动检测文件类型
file_type = detect_file_type("activity_log.md")      # 返回 'activity'
file_type = detect_file_type("alice_profile.md")     # 返回 'profile'

# 检查是否为必须文件
is_core = is_required_file(file_type)  # activity=True, 其他=False
```

### 3. 实际使用

```python
from memu import MemoryAgent

# 最简单的使用 - 只需要activity文件
agent = MemoryAgent(llm_client, memory_dir="memory")

# 自动导入和分类
agent.import_local_document("notes.md", "Alice")  # 自动检测文件类型
```

## 📝 添加新的文件类型

要添加新的markdown文件类型，请修改 `markdown_config.py` 中的 `_load_markdown_configs()` 方法：

```python
# 添加新的文件类型配置
configs["new_type"] = MarkdownFileConfig(
    name="new_type",
    filename="new_type.md",
    description="新文件类型的描述",
    prompt_template="new_type_prompt",
    processing_priority=30,  # 设置优先级
    depends_on=["activity"],  # 设置依赖关系
    content_structure={
        "标题1": "## 标题1\n内容模板",
        "标题2": "## 标题2\n内容模板"
    },
    usage_examples=[
        "用途1",
        "用途2"
    ],
    auto_detect_keywords=["keyword1", "keyword2"],
    content_patterns=["pattern1", "pattern2"]
)
```

**同时需要**:
1. 在 `prompts/` 目录下创建对应的prompt文件
2. 更新MemoryAgent的处理逻辑（如果需要）

## 🚀 示例和演示

运行以下命令查看配置系统的完整演示：

```bash
python examples/config_demo.py
```

这将展示：
- 所有支持的文件类型和描述
- 处理顺序和依赖关系图
- 内容结构模板
- 自动检测功能演示
- 配置验证结果

## ⚙️ 高级配置

### 修改处理优先级

优先级数值越大，处理越早。当前优先级分配：
- activity: 100 (最高)
- profile: 80
- event: 70
- reminder: 60
- interests: 50
- study: 40 (最低)

### 修改依赖关系

依赖关系确保文件按正确顺序处理：
- 被依赖的文件必须先处理
- 避免循环依赖
- activity是所有其他文件的根依赖

### 自定义内容结构

可以为每种文件类型定义标准的markdown结构模板，用于：
- 生成一致的文件格式
- 提供用户指导
- 支持内容验证

## 📊 配置系统的优势

1. **集中管理** - 所有配置在一个文件中
2. **易于扩展** - 添加新类型只需修改配置
3. **智能检测** - 自动识别文件类型
4. **依赖管理** - 确保正确的处理顺序
5. **标准化** - 统一的文件结构和格式
6. **可验证** - 配置完整性检查

这个配置系统是MemU架构的核心，提供了灵活、可扩展的markdown文件管理方案。 