# MemU Server 快速启动指南

## 🚀 修复后的启动步骤

### 📋 准备工作

1. **安装依赖**
```bash
cd server/backend
pip install fastapi uvicorn python-multipart
```

2. **设置环境变量**
```bash
# 必需：内存文件目录
export MEMORY_DIR="./memory"

# 可选：LLM API密钥（用于对话分析）
export OPENAI_API_KEY="sk-your-openai-key"
# 或者
export AZURE_OPENAI_API_KEY="your-azure-key"
```

### 🔧 启动Backend

**选项1：使用修复版本（推荐）**
```bash
cd server/backend
python start_fixed.py
```

**选项2：直接运行**
```bash
cd server/backend
python main_fixed.py
```

### 🎨 启动Frontend

```bash
cd server/frontend
npm install
npm run dev
```

## 📡 API端点

### 🏠 基础端点
- `GET /` - 健康检查
- `GET /api/health` - 详细健康状态
- `GET /api/stats` - 系统统计
- `GET /api/storage/modes` - 存储模式信息

### 📁 文件内存管理
- `GET /api/file-memory/characters` - 角色列表
- `GET /api/file-memory/characters/{name}/summary` - 角色详情
- `GET /api/file-memory/characters/{name}/files/{type}` - 读取文件
- `PUT /api/file-memory/characters/{name}/files/{type}` - 更新文件
- `POST /api/file-memory/analyze-conversation` - 分析对话

### 📝 支持的文件类型
- `profile` - 角色档案
- `event` - 事件记录
- `reminder` - 提醒事项
- `important_event` - 重要事件
- `interests` - 兴趣爱好
- `study` - 学习信息

## 🔧 故障排除

### ❌ ModuleNotFoundError

如果遇到模块导入错误，请使用修复版本：
```bash
# 使用修复版本
python start_fixed.py

# 而不是
python start.py  # 可能有导入错误
```

### 📁 文件目录权限

确保内存目录可写：
```bash
mkdir -p memory
chmod 755 memory
```

### 🤖 LLM功能不可用

如果对话分析功能不可用：
1. 检查API密钥是否设置
2. 检查网络连接
3. 查看后端日志

## 🎯 测试功能

### 1. 基础健康检查
```bash
curl http://localhost:8000/api/health
```

### 2. 获取角色列表
```bash
curl http://localhost:8000/api/file-memory/characters
```

### 3. 分析对话（需要LLM配置）
```bash
curl -X POST http://localhost:8000/api/file-memory/analyze-conversation \
  -H "Content-Type: application/json" \
  -d '{
    "character_name": "Alice",
    "conversation": "Hello! I love hiking and just finished reading a book about machine learning.",
    "session_date": "2024-01-15"
  }'
```

## 📊 访问界面

- **API文档**: http://localhost:8000/docs
- **前端界面**: http://localhost:5173
- **健康检查**: http://localhost:8000/api/health

## 🆕 新功能

✅ **修复版本特点**：
- 移除了不存在的模块依赖
- 简化的对话存储（文件形式）
- 完整的文件内存管理
- 健康检查和监控
- 错误处理和日志

✅ **6种文件类型支持**：
- 智能分类存储
- 人类可读的Markdown格式
- 版本控制友好
- 便携和可备份

✅ **现代化界面**：
- React + Material-UI
- 响应式设计
- 实时编辑功能
- 文件下载和管理 