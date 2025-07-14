# Enhanced Memory Agent for Locomo Evaluation

## 🎯 算法概述

这是一个全新设计的增强记忆代理算法，专门为Locomo评估任务而重新构建。该算法的核心思想是为每个对话角色维护结构化的记忆文件，并在每个session结束后进行增量更新。

## 🧠 核心特性

### 1. 两类记忆文件

为每个角色维护两个独立的记忆文件（包含Theory of Mind注释）：

- **`profile.md`** - 角色画像
  - 基本信息（年龄、职业、生活状况）
  - 性格特点
  - 兴趣爱好
  - 价值观念
  - 关系网络

- **`event.md`** - 事件记录
  - 按时间顺序记录重要事件
  - 事件的影响和意义
  - 事件间的关联性
  
- **Theory of Mind注释** - 心理状态分析
  - 以HTML注释形式添加到profile.md和event.md的每一行下面
  - 每行内容都有对应的深层心理分析
  - 包含角色内心想法、情绪状态、动机意图等深层心理分析


### 2. 渐进式记忆更新

```
Session 1 → 分析对话 → 更新记忆文件
Session 2 → 分析对话 → 更新记忆文件
...
Session N → 分析对话 → 更新记忆文件
```

每个session结束后，算法会：
1. 分析对话内容
2. 提取相关信息
3. 更新对应的记忆文件
4. 保持信息的一致性和连贯性

### 3. 上下文合并

在QA测试阶段，算法会：
1. 读取所有角色的两个记忆文件（包含Theory of Mind注释）
2. 将信息合并成统一的上下文
3. 基于完整的记忆信息回答问题

## 🏗️ 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                Enhanced Memory Agent                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │  Session 1  │    │  Session 2  │    │  Session N  │     │
│  │  Processing │    │  Processing │    │  Processing │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│         │                   │                   │          │
│         ▼                   ▼                   ▼          │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              Memory File Updates                       │ │
│  ├─────────────────────────────────────────────────────────┤ │
│  │  Character A          │  Character B                   │ │
│  │  ├─ profile.md       │  ├─ profile.md                 │ │
│  │  ├─ event.md         │  ├─ event.md                   │ │
│  │  (mind分析通过注释)   │  (mind分析通过注释)           │ │
│  └─────────────────────────────────────────────────────────┘ │
│                            │                                │
│                            ▼                                │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              Context Merging                           │ │
│  │              + QA Testing                              │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 使用方法

### 1. 环境配置

```bash
# 复制环境变量模板
cp env.template.enhanced .env

# 编辑.env文件，配置Azure OpenAI参数
vim .env
```

### 2. 运行测试

```bash
# 给运行脚本添加执行权限
chmod +x run_enhanced_memory_test.sh

# 运行测试
./run_enhanced_memory_test.sh
```

### 3. 查看结果

测试完成后，会生成以下文件：

- **结果文件**: `enhanced_memory_test_results_YYYYMMDD_HHMMSS.json`
- **日志文件**: `logs/enhanced_memory_test_YYYYMMDD_HHMMSS.log`
- **记忆文件**: `memory/角色名_类型.md`（如：`caroline_profile.md`）

## 📊 输出文件说明

### 记忆文件示例

```markdown
# Caroline 的记忆信息

## 角色画像
### 基本信息
- 年龄：30岁
- 职业：自由职业者
- 生活状况：单身，独自居住

### 性格特点
- 内向敏感
- 勇敢坚强
- 富有同理心

### 兴趣爱好
- 阅读
- 绘画
- 音乐

## 重要事件
### 2023-05-07
- 参加LGBTQ支持小组
- 感受到社区的温暖和支持

### 2023-05-08
- 与Melanie深入交流
- 分享个人经历

## 心理状态
### 2023-05-07
- 紧张但充满希望
- 对身份认同更加确信
- 渴望更多支持和理解

### 2023-05-08
- 情绪稳定
- 对未来有明确规划
- 感到被理解和支持
```

### 结果文件结构

```json
{
  "test_info": {
    "test_type": "enhanced_memory_test",
    "data_file": "data/locomo10.json",
    "total_samples": 10,
    "total_time": 1234.56,
    "timestamp": "2024-01-01T12:00:00"
  },
  "overall_statistics": {
    "total_qa": 1990,
    "consistent_qa": 1592,
    "consistency_rate": 0.8,
    "avg_accuracy": 4.2,
    "avg_processing_time": 123.45
  },
  "sample_results": [...]
}
```

## 🔍 算法优势

### 1. 结构化记忆管理
- 将记忆分为三个明确的类别
- 每个类别专注于特定的信息类型
- 避免信息混乱和重复

### 2. 渐进式更新
- 每个session都会增量更新记忆
- 保持信息的时效性和准确性
- 支持长期对话的记忆累积

### 3. 全面的上下文整合
- QA时合并所有记忆信息
- 提供完整的角色背景
- 支持复杂问题的准确回答

### 4. 可追溯性
- 记忆文件以markdown格式保存
- 便于人工检查和验证
- 支持调试和优化

## 🛠️ 技术细节

### 依赖项
- `personalab.llm.AzureOpenAIClient`
- `personalab.utils.get_logger`
- Python 3.8+
- Azure OpenAI API

### 主要类和方法

#### `EnhancedMemoryAgent`
- `process_session()`: 处理单个session
- `get_merged_context()`: 获取合并的上下文
- `answer_question()`: 基于记忆回答问题

#### `EnhancedMemoryTester`
- `process_sample()`: 处理单个样本
- `run_test()`: 运行完整测试
- `_evaluate_answer()`: 评估答案质量

## 📈 性能指标

算法会自动计算以下指标：

- **一致性率**: 生成答案与标准答案的一致程度
- **准确性评分**: 1-5分的详细评分
- **处理时间**: 每个样本的平均处理时间
- **记忆文件大小**: 生成的记忆文件统计

## 🔧 自定义配置

### 调整记忆分析提示
可以在`EnhancedMemoryAgent`类中修改以下方法的提示词：
- `_analyze_session_for_profile()`
- `_analyze_session_for_events()`
- `_add_theory_of_mind_comments()`

### 修改评估标准
可以在`EnhancedMemoryTester`类的`_evaluate_answer()`方法中调整评估逻辑。

### 配置输出格式
可以修改记忆文件的markdown格式和结构。

## 🐛 故障排除

### 常见问题

1. **Azure OpenAI连接失败**
   - 检查`.env`文件中的配置
   - 确认API密钥和端点正确
   - 验证部署名称

2. **记忆文件为空**
   - 检查session数据是否正确解析
   - 确认LLM响应是否正常
   - 查看日志文件中的错误信息

3. **QA评估失败**
   - 检查问题和答案格式
   - 确认评估提示词是否合适
   - 验证LLM输出格式

### 日志级别
可以在环境变量中设置`LOG_LEVEL`来控制日志详细程度：
- `DEBUG`: 最详细的日志
- `INFO`: 一般信息（默认）
- `WARNING`: 警告信息
- `ERROR`: 只显示错误

## 📝 更新日志

### v1.0.0 (2024-01-01)
- 初始版本发布
- 实现基本的增强记忆算法
- 支持三类记忆文件管理
- 完整的测试和评估框架

---

**注意**: 这个算法是专门为Locomo评估任务设计的，但其设计思想可以应用到其他需要长期记忆管理的对话系统中。 