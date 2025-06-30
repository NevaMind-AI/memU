# Embedding Providers 指南

PersonaLab memo模块支持多种高质量的embedding providers用于语义搜索。

## 支持的Providers

### 1. OpenAI Embeddings (推荐)
- **模型**: text-embedding-ada-002
- **维度**: 1536
- **优势**: 
  - 最高质量的语义理解
  - 多语言支持优秀
  - 强大的跨领域性能
- **要求**: OpenAI API key
- **成本**: 按使用付费 ($0.0001/1K tokens)

```python
manager = ConversationManager(
    embedding_provider="openai"
)
```

### 2. SentenceTransformers (本地)
- **模型**: all-MiniLM-L6-v2 (默认)
- **维度**: 384
- **优势**:
  - 本地运行，无API依赖
  - 完全免费
  - 良好的语义理解
  - 支持多种模型
- **要求**: pip install sentence-transformers

```python
manager = ConversationManager(
    embedding_provider="sentence-transformers"
)
```

## 自动选择

使用 `embedding_provider="auto"` 自动选择最佳可用provider：

```python
manager = ConversationManager(
    embedding_provider="auto"  # 优先级: OpenAI -> SentenceTransformers
)
```

## 性能对比

| 特性 | SentenceTransformers | OpenAI |
|------|---------------------|--------|
| 质量 | 优秀 | 顶级 |
| 成本 | 免费 | 付费 |
| 延迟 | 低 (本地) | 中等 (API) |
| 离线使用 | ✅ | ❌ |
| 多语言 | 良好 | 优秀 |

## 安装要求

### OpenAI
```bash
pip install openai
export OPENAI_API_KEY="your-key"
```

### SentenceTransformers
```bash
pip install sentence-transformers
```

## 错误处理

如果没有可用的embedding provider，系统会抛出明确的错误信息：

```python
try:
    manager = ConversationManager(embedding_provider="auto")
except RuntimeError as e:
    print(f"请安装embedding依赖: {e}")
```

## 历史变更

- **v1.1**: 移除了Simple Embedding provider
  - 原因: 质量较低，影响用户体验
  - 替代: 使用SentenceTransformers作为免费本地选项
  - 影响: 提升了整体语义搜索质量 