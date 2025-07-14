# 增强记忆代理使用说明

## 🎯 算法概述

这是一个全新的增强记忆代理算法，专门为Locomo评估重新设计。核心特点：

1. **每个session结束后更新记忆文件**
2. **维护两类结构化记忆**：`profile.md`、`event.md`（包含Theory of Mind注释）
3. **QA测试时合并所有记忆作为上下文**

## 📁 文件结构

```
locomo/
├── enhanced_memory_agent.py    # 核心算法实现
├── enhanced_memory_test.py     # 测试框架
├── run_enhanced_memory_test.sh # 运行脚本
├── quick_test.py              # 快速测试
├── env.template.enhanced      # 环境变量模板
├── README_Enhanced_Memory.md  # 详细说明
├── USAGE.md                   # 使用说明（本文件）
├── data/                      # 数据目录
│   └── locomo10.json         # 测试数据
└── memory/                    # 记忆文件目录
    ├── 角色名_profile.md      # 角色画像
    ├── 角色名_event.md        # 事件记录
```

## 🚀 快速开始

### 1. 配置环境

```bash
# 复制环境变量模板
cp env.template.enhanced .env

# 编辑配置文件
vim .env
```

配置内容：
```env
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2024-02-01
USE_ENTRA_ID=false
```

### 2. 快速测试

```bash
# 运行快速测试验证环境
./quick_test.py
```

### 3. 完整测试

```bash
# 运行完整的Locomo评估
./run_enhanced_memory_test.sh
```

## 📊 结果解读

### 记忆文件示例

**profile.md** - 角色画像：
```markdown
## 基本信息
- 年龄：30岁
- 职业：软件工程师

## 性格特点
- 内向但友善
- 逻辑思维强

## 兴趣爱好
- 编程
- 阅读
```

**event.md** - 事件记录：
```markdown
### 2024-01-01
- 开始新工作
- 感到兴奋和紧张

### 2024-01-02
- 第一天工作顺利
- 同事很友好
```

**Theory of Mind注释** - 心理状态分析：
以HTML注释形式添加到profile.md和event.md的每一行下面：
```html
Caroline在2024年1月1日开始了新工作，她对此充满期待但也有些紧张。
<!-- Theory of Mind (2024-01-01): 内心既兴奋又焦虑，期待新挑战但担心能力不足 -->

她与同事们建立了良好的关系，特别是与Melanie成为了好朋友。
<!-- Theory of Mind (2024-01-01): 渴望归属感和友谊，通过建立关系来缓解职场压力 -->
```

### 测试结果

```json
{
  "overall_statistics": {
    "total_qa": 1990,
    "consistent_qa": 1592,
    "consistency_rate": 0.8,
    "avg_accuracy": 4.2,
    "avg_processing_time": 123.45
  }
}
```

## 🔧 高级配置

### 调整模型参数

在`.env`文件中可以配置：
```env
# 使用不同的模型
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o

# 调整API版本
AZURE_OPENAI_API_VERSION=2024-02-01
```

### 自定义记忆目录

```bash
# 指定自定义记忆目录
export MEMORY_DIR=/path/to/custom/memory
```

### 调整处理样本数

在代码中修改：
```python
# 只处理前5个样本
data = data[:5]
```

## 📈 性能优化

### 并行处理

目前算法是串行处理，如需并行处理可以：
1. 修改`enhanced_memory_test.py`中的`run_test`方法
2. 使用`concurrent.futures`或`multiprocessing`

### 内存管理

对于大量数据：
1. 定期清理临时文件
2. 使用流式处理
3. 分批处理样本

## 🐛 常见问题

### 1. 环境变量未设置
```
❌ 缺少环境变量: AZURE_OPENAI_ENDPOINT
```
**解决方案**: 检查`.env`文件配置

### 2. API连接失败
```
❌ LLM客户端初始化失败
```
**解决方案**: 
- 检查网络连接
- 验证API密钥
- 确认端点URL正确

### 3. 记忆文件为空
```
📁 生成的记忆文件: (空)
```
**解决方案**:
- 检查session数据格式
- 查看日志文件错误信息
- 验证LLM响应

### 4. QA评估失败
```
❌ 评估答案失败
```
**解决方案**:
- 检查问题格式
- 确认标准答案完整性
- 调整评估提示词

## 📝 开发指南

### 修改记忆分析逻辑

在`enhanced_memory_agent.py`中：
```python
def _analyze_session_for_profile(self, character_name: str, conversation: str, existing_profile: str) -> str:
    # 修改分析提示词
    prompt = f"""
    自定义的分析提示...
    """
```

### 添加新的记忆类型

1. 在`EnhancedMemoryAgent`中添加新的分析方法
2. 在`process_session`中调用新方法
3. 在`get_merged_context`中包含新类型

### 自定义评估标准

在`enhanced_memory_test.py`中：
```python
def _evaluate_answer(self, question: str, generated_answer: str, standard_answer: str) -> Dict:
    # 修改评估逻辑
    prompt = f"""
    自定义的评估提示...
    """
```

## 🔍 调试技巧

### 启用详细日志

```bash
export LOG_LEVEL=DEBUG
```

### 查看记忆文件

```bash
# 查看生成的记忆文件
find memory -name "*.md" -exec head -20 {} \; -print
```

### 检查中间结果

```bash
# 查看中间结果文件
ls enhanced_memory_test_intermediate_*.json
```

## 📞 支持

如有问题，请：
1. 查看日志文件
2. 检查`README_Enhanced_Memory.md`详细说明
3. 运行`quick_test.py`进行诊断

---

**版本**: v1.0.0  
**更新日期**: 2024-01-01  
**作者**: PersonaLab Team 