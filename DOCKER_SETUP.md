# MemU Docker Setup Guide

## 🐳 Docker的作用 (What Docker Does)

Docker在MemU项目中的作用是**自动化启动后端服务和数据库**，大大简化了启动流程：

- **数据库服务**: 自动启动PostgreSQL with pgvector
- **后端服务**: 自动启动FastAPI服务器 (端口8000)
- **前端服务**: 手动启动 (由于依赖兼容性问题)

## 📋 系统要求 (Requirements)

- Docker Desktop 
- Docker Compose (通常包含在Docker Desktop中)
- Node.js 18+ (用于前端)

## 🚀 一键启动 (Quick Startup)

### 步骤1: 启动后端和数据库

```bash
# 在项目根目录运行
./start-docker.sh
```

这个脚本会：
- ✅ 检查Docker环境
- ✅ 自动构建和启动后端和数据库服务
- ✅ 显示服务状态和访问地址
- ✅ 提供前端启动指令

### 步骤2: 启动前端 (在新终端窗口中)

```bash
cd server/frontend
npm install
npm run dev
```

## 🌐 服务访问地址

启动成功后，可以访问以下地址：

- **🔧 后端API**: http://localhost:8000 ✅ 正常工作
- **📚 API文档**: http://localhost:8000/docs ✅ 正常工作
- **🗄️ 数据库**: localhost:5432 ✅ 正常工作
- **🎨 前端界面**: http://localhost:5173 (需要手动启动)

## 🛠️ 常用命令

### Docker服务管理

```bash
# 查看服务状态
docker-compose ps

# 查看后端日志
docker-compose logs -f backend

# 重启服务
docker-compose restart

# 停止所有服务
docker-compose down

# 强制重新构建
docker-compose up -d --build --force-recreate
```

### 前端开发

```bash
# 进入前端目录
cd server/frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build
```

## 🔧 环境变量配置

### OpenAI API Key (可选)

```bash
# 设置环境变量
export OPENAI_API_KEY="your-api-key-here"

# 然后启动服务
./start-docker.sh
```

或者创建 `.env` 文件：

```bash
# .env
OPENAI_API_KEY=your-api-key-here
```

## 🔄 当前的工作方案

| 组件 | 运行方式 | 端口 | 状态 |
|------|----------|------|------|
| **数据库** | Docker | 5432 | ✅ 正常工作 |
| **后端API** | Docker | 8000 | ✅ 正常工作 |
| **前端** | 手动启动 | 5173 | ✅ 正常工作 |

### 为什么前端需要手动启动？

前端在Docker容器中遇到了Vite/esbuild版本兼容性问题：
- Vite 7.0.0与Node.js的crypto模块有冲突
- esbuild版本不匹配问题
- 容器环境下的文件监听问题

手动启动前端能够：
- 使用本地Node.js环境，避免容器兼容性问题
- 热重载功能正常工作
- 开发体验更流畅

## 🚨 常见问题解决

### 1. 后端启动失败
```bash
# 查看详细错误信息
docker-compose logs backend

# 重新构建并启动
docker-compose down
docker-compose up -d --build
```

### 2. 前端无法连接后端
确保：
- 后端在 http://localhost:8000 正常运行
- 前端API配置指向正确的地址
- 没有端口冲突

### 3. 数据库连接问题
```bash
# 检查数据库服务状态
docker-compose ps postgres

# 查看数据库日志
docker-compose logs postgres
```

### 4. 端口占用
```bash
# 查看端口占用
lsof -i :8000
lsof -i :5173
lsof -i :5432

# 停止占用端口的服务
docker-compose down
```

## 🔄 从完全手动启动迁移

如果你之前使用完全手动启动：

1. **停止手动服务**:
   ```bash
   # 停止任何正在运行的Python进程
   pkill -f "python.*start.py"
   pkill -f "uvicorn"
   pkill -f "npm.*dev"
   ```

2. **使用Docker启动后端**:
   ```bash
   ./start-docker.sh
   ```

3. **手动启动前端**:
   ```bash
   cd server/frontend
   npm install
   npm run dev
   ```

## 📝 开发建议

- **日常开发**: 
  1. 使用 `./start-docker.sh` 启动后端和数据库
  2. 在新终端中手动启动前端
  
- **调试模式**: 使用 `docker-compose logs -f backend` 查看后端日志

- **代码修改**: 
  - 后端代码修改：Docker容器内自动重载
  - 前端代码修改：本地开发服务器热重载

- **数据持久化**: 数据库数据存储在Docker volume中，重启不会丢失

## 🎯 总结

**当前方案的优势**:
1. **后端零配置** - Docker自动处理数据库和API服务
2. **环境隔离** - 后端运行在隔离的容器环境中
3. **前端开发友好** - 使用本地Node.js环境，避免容器问题
4. **数据安全** - PostgreSQL数据持久化存储

**使用步骤**:
1. 运行 `./start-docker.sh` 启动后端和数据库
2. 在新终端运行前端：`cd server/frontend && npm run dev`
3. 访问 http://localhost:5173 使用应用

现在Docker正确地发挥了作用：**自动化后端服务启动，无需手动打开 `backend/main.py` 文件**！ 