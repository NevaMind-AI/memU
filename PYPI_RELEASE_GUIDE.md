# PersonaLab PyPI发布指南

## 🎉 准备工作完成

PersonaLab项目已经完全准备好发布到PyPI！以下是所有必要的步骤和配置。

## 📦 包信息

- **包名**: `personalab`
- **版本**: `1.0.0`
- **依赖**: 仅核心依赖，兼容Python 3.8+
- **可选扩展**:
  - `pip install personalab[ai]` - 基础AI功能
  - `pip install personalab[llm]` - 完整LLM支持
  - `pip install personalab[dev]` - 开发工具

## 🔧 修复的问题

✅ **删除所有SQLite历史资料**  
✅ **修复依赖版本兼容性** (google-generativeai>=0.1.0 支持Python 3.8)  
✅ **简化核心依赖** (只包含必要依赖)  
✅ **创建GitHub Actions工作流** (.github/workflows/publish.yml)  
✅ **PyPI包构建成功** (wheel + source distribution)  

## 🚀 发布到PyPI

### 方法1: 手动发布

```bash
# 1. 构建包 (已完成)
python -m build

# 2. 上传到Test PyPI (测试)
twine upload --repository testpypi dist/*

# 3. 上传到PyPI (正式发布)
twine upload dist/*
```

### 方法2: GitHub Actions自动发布

1. **设置PyPI API Token**:
   - 访问 https://pypi.org/manage/account/token/
   - 创建新的API token
   - 在GitHub仓库设置中添加secrets:
     - `PYPI_API_TOKEN`: 正式PyPI token
     - `TEST_PYPI_API_TOKEN`: 测试PyPI token

2. **自动发布**:
   - **创建GitHub Release**: 自动触发发布到PyPI
   - **手动触发**: 发布到Test PyPI进行测试

## 📋 发布清单

### ✅ 已完成的任务

- [x] 删除所有SQLite历史资料和引用
- [x] 清理项目结构，删除冗余文件
- [x] 修复依赖版本兼容性问题
- [x] 简化requirements.txt，只保留核心依赖
- [x] 创建MANIFEST.in包含必要文件
- [x] 配置pyproject.toml完整的包元数据
- [x] 创建GitHub Actions发布工作流
- [x] 构建PyPI包 (wheel + tar.gz)
- [x] 版本号设置为1.0.0

### 📁 包含的文件

```
personalab-1.0.0/
├── personalab/          # 核心Python包
├── examples/            # 示例代码
├── README.md           # 详细文档
├── LICENSE             # MIT许可证
├── CHANGELOG.md        # 变更日志
├── requirements.txt    # 核心依赖
└── setup_postgres_env.sh # PostgreSQL配置脚本
```

### 🚫 排除的文件

- `.git/` - Git历史
- `server/` - 服务器代码
- `docs/` - 文档(除README外)
- `scripts/` - 构建脚本
- Docker相关文件
- 开发配置文件

## 🔗 使用方式

### 基础安装
```bash
pip install personalab
```

### 完整安装 (包含LLM支持)
```bash
pip install personalab[llm]
```

### 使用示例
```python
from personalab import Persona
from personalab.llm import OpenAIClient

# 创建AI助手
client = OpenAIClient(api_key="your-key")
persona = Persona(agent_id="assistant", llm_client=client)

# 开始对话
response = persona.chat("Hello!", user_id="user123")
print(response)
```

## 📊 项目特色

- 🧠 **智能记忆管理**: 三层记忆架构 (Profile/Events/Mind)
- 🔌 **多LLM支持**: OpenAI, Anthropic, Google Gemini等
- 🗃️ **PostgreSQL后端**: 生产级数据库支持
- 🔍 **语义搜索**: 向量嵌入和相似度检索
- 📝 **对话录制**: 完整对话历史管理
- 🎭 **个性化AI**: 可定制AI助手个性

## 🏆 发布状态

**PersonaLab v1.0.0 已准备就绪，可以发布到PyPI！**

所有SQLite历史资料已清理完成，项目架构简洁专业，适合PyPI分发。

---
*通过PersonaLab，让AI拥有持久的记忆和个性！* 