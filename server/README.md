# PersonaLab 后台管理系统 (React + Vite + FastAPI)

现代化的PersonaLab后台管理系统，采用前后端分离架构，提供完整的数据库管理功能。

## 🏗️ 架构说明

- **前端**: React 18 + Vite + Material-UI
- **后端**: FastAPI + PostgreSQL + pgvector
- **数据库**: PostgreSQL with pgvector extension
- **API文档**: 自动生成的OpenAPI/Swagger文档

## 📁 项目结构

```
server/
├── backend/                 # FastAPI后端
│   ├── main.py             # FastAPI主应用
│   ├── start.py            # 启动脚本
│   └── requirements.txt    # Python依赖
└── frontend/               # React前端
    ├── src/
    │   ├── api/           # API客户端
    │   ├── components/    # React组件
    │   ├── pages/         # 页面组件
    │   └── App.jsx        # 主应用
    ├── package.json       # Node依赖
    └── vite.config.js     # Vite配置
```

## ✨ 功能特性

### 📊 系统概览
- 实时统计信息展示
- 对话、记忆、Agent、用户数据统计
- 今日和本周活跃度指标

### 💬 对话管理
- 对话列表浏览和搜索
- 按Agent和用户筛选
- 对话详情查看（包含完整消息历史）
- 对话删除功能

### 🧠 记忆管理
- 记忆列表展示和过滤
- 记忆详情查看（Profile、Event、Mind内容）
- 记忆内容的可折叠展示
- 记忆删除功能

### 📝 操作记录
- 记忆操作历史跟踪
- 创建/更新操作记录
- 操作时间和详情展示

### 🔍 高级功能
- 响应式设计，支持移动设备
- 实时数据加载
- 分页浏览
- 错误处理和用户反馈
- 现代化UI设计

## 🚀 快速开始

### 环境要求

- Python 3.8+
- Node.js 16+
- PostgreSQL 12+ with pgvector extension
- PersonaLab项目环境

### 1. 安装后端依赖

```bash
cd server/backend
pip install -r requirements.txt
```

### 2. 安装前端依赖

```bash
cd server/frontend
npm install
```

### 3. 环境配置

确保设置了以下环境变量（或在PersonaLab根目录的`.env`文件中）：

```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=personalab
POSTGRES_USER=chenhong
POSTGRES_PASSWORD=
```

### 4. 启动服务

#### 启动后端API服务器

```bash
cd server/backend
python start.py
```

后端将运行在 `http://localhost:8080`

- API接口: http://localhost:8080
- API文档: http://localhost:8080/docs
- 交互式API文档: http://localhost:8080/redoc

#### 启动前端开发服务器

```bash
cd server/frontend
npm run dev
```

前端将运行在 `http://localhost:5173`

### 5. 访问应用

打开浏览器访问 `http://localhost:5173` 即可使用管理系统。

## 📚 API文档

### 主要API端点

- `GET /api/stats` - 获取系统统计信息
- `GET /api/conversations` - 获取对话列表
- `GET /api/conversations/{id}` - 获取对话详情
- `DELETE /api/conversations/{id}` - 删除对话
- `GET /api/memories` - 获取记忆列表
- `GET /api/memories/{id}` - 获取记忆详情
- `DELETE /api/memories/{id}` - 删除记忆
- `GET /api/memory-operations` - 获取记忆操作记录
- `GET /api/agents` - 获取Agent列表
- `GET /api/users` - 获取用户列表

所有API都支持分页和过滤参数。详细的API文档可以通过访问 `http://localhost:8080/docs` 查看。

## 🛠️ 开发说明

### 前端开发

- 使用React Hooks进行状态管理
- Material-UI组件库提供一致的设计语言
- Axios用于HTTP请求
- React Router用于路由管理
- 响应式设计适配各种屏幕尺寸

### 后端开发

- FastAPI提供高性能异步API
- Pydantic进行数据验证
- PostgreSQL数据库集成
- 自动生成的API文档
- CORS支持前后端分离

### 数据库

- 兼容现有PersonaLab数据库结构
- 支持pgvector向量搜索功能
- 直接SQL查询提供最佳性能

## 🔧 配置说明

### 后端配置

后端会自动设置PostgreSQL环境变量，默认配置：
- 主机: localhost
- 端口: 5432
- 数据库: personalab
- 用户: chenhong
- 密码: 空

### 前端配置

前端API客户端配置在 `src/api/client.js` 中，默认连接到 `http://localhost:8080`。

## 🐛 故障排除

### 常见问题

1. **数据库连接失败**
   - 确认PostgreSQL服务正在运行
   - 检查数据库配置是否正确
   - 确认pgvector扩展已安装

2. **前端无法连接后端**
   - 确认后端服务器正在运行
   - 检查CORS配置
   - 确认端口没有被占用

3. **依赖安装问题**
   - 确认Python和Node.js版本满足要求
   - 尝试清除缓存后重新安装
   - 检查网络连接

## 📈 性能优化

- 前端使用虚拟化技术处理大量数据
- 后端使用数据库索引优化查询
- 分页加载减少内存占用
- 懒加载组件提升加载速度

## 🤝 贡献指南

1. Fork项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request

## 📄 许可证

本项目遵循PersonaLab项目的许可证。

## 🆚 与旧版本对比

### 优势

- **现代化技术栈**: React + FastAPI
- **更好的用户体验**: Material-UI + 响应式设计
- **更高的性能**: FastAPI异步处理 + Vite快速构建
- **更好的维护性**: 前后端分离 + TypeScript支持
- **自动化API文档**: OpenAPI/Swagger
- **移动端友好**: 响应式设计

### 迁移指南

从旧的Flask版本迁移：
1. 数据库结构保持不变
2. API接口重新设计但功能兼容
3. 前端完全重写，提供更好的用户体验
4. 配置文件格式略有调整

---

🎉 享受使用PersonaLab后台管理系统！如有问题请提交Issue。 