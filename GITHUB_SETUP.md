# PersonaLab GitHub 仓库设置指南

## 🎯 目标
将PersonaLab配置为专业的GitHub开源项目，包括logo、社交预览图等。

## 📋 设置步骤

### 1. 提交所有更改到GitHub

```bash
# 添加所有文件（包括logo）
git add .

# 提交更改
git commit -m "feat: 完成PersonaLab项目优化

- 添加Persona简洁API
- 重构项目结构  
- 添加CLI工具
- 更新README和文档
- 添加项目logo"

# 推送到GitHub
git push origin main
```

### 2. 设置GitHub仓库Logo（社交预览图）

#### 方法一：通过GitHub Web界面
1. 进入GitHub仓库页面：`https://github.com/NevaMind-AI/PersonaLab`
2. 点击仓库名称下方的 **Settings** 标签
3. 在左侧菜单中找到 **General** 
4. 向下滚动到 **Social preview** 部分
5. 点击 **Upload an image** 
6. 上传 `assets/logo.png` 文件
7. 调整裁剪区域（推荐 1200x630 像素）
8. 点击 **Save**

#### 方法二：使用GitHub REST API
```bash
# 首先将logo转换为base64（如果需要特定尺寸）
# 然后使用API上传

curl -X PATCH \
  -H "Authorization: token YOUR_GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/NevaMind-AI/PersonaLab \
  -d '{
    "name": "PersonaLab",
    "description": "AI Memory and Conversation Management Framework - Simple as mem0, Powerful as PersonaLab"
  }'
```

### 3. 设置GitHub仓库其他配置

#### 3.1 仓库描述和标签
在仓库Settings > General中设置：

**Description（描述）：**
```
AI Memory and Conversation Management Framework - Simple as mem0, Powerful as PersonaLab
```

**Website（网站）：**
```
https://personalab.ai
```

**Topics（标签）：**
```
ai, memory, conversation, llm, chatbot, persona, agent, openai, machine-learning, artificial-intelligence, python, framework
```

#### 3.2 README.md徽章验证
确保以下徽章链接正确：
- ✅ MIT License徽章
- ✅ Python版本徽章  
- ✅ Code style徽章
- 🔄 PyPI徽章（发布到PyPI后会生效）

#### 3.3 分支保护规则
在Settings > Branches中设置：
- 保护 `main` 分支
- 要求PR审查
- 要求状态检查通过

### 4. 设置GitHub Actions（可选）

创建 `.github/workflows/ci.yml`:
```yaml
name: CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, '3.10', 3.11, 3.12]

    steps:
    - uses: actions/checkout@v3
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v3
      with:
        python-version: ${{ matrix.python-version }}
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e .[dev]
    - name: Run tests
      run: |
        python -m pytest tests/ -v
    - name: Run linting
      run: |
        black --check personalab/
        flake8 personalab/
```

### 5. 创建GitHub Release

#### 5.1 创建标签
```bash
git tag -a v0.1.0 -m "PersonaLab v0.1.0 - Initial release with Persona API"
git push origin v0.1.0
```

#### 5.2 在GitHub上创建Release
1. 进入仓库的 **Releases** 页面
2. 点击 **Create a new release**
3. 选择标签 `v0.1.0`
4. 填写Release标题：`PersonaLab v0.1.0 - Simple as mem0, Powerful as Enterprise`
5. 填写Release描述：

```markdown
## 🎉 PersonaLab v0.1.0 - 首个正式版本

### ✨ 主要特性

- **超简洁API**: 3行代码实现AI记忆功能，比mem0更简单
- **功能强大**: 企业级记忆管理 + 对话检索 + 语义搜索
- **开发者友好**: pip install + CLI工具 + 清晰文档

### 🚀 快速开始

\`\`\`bash
pip install personalab[ai]
export OPENAI_API_KEY="your-key"
personalab test
\`\`\`

\`\`\`python
from personalab import Persona
persona = Persona()
response = persona.chat("Hello!", user_id="user123")
\`\`\`

### 📦 安装选项

- `pip install personalab[ai]` - 核心AI功能
- `pip install personalab[all]` - 完整功能

详细使用说明请查看 [README.md](https://github.com/NevaMind-AI/PersonaLab#readme)
```

### 6. 验证设置结果

完成上述步骤后，你的GitHub仓库应该具备：

- ✅ 专业的logo显示
- ✅ 完整的社交预览图  
- ✅ 清晰的项目描述和标签
- ✅ 美观的README展示
- ✅ 标准的开源项目结构

## 🎯 预期效果

设置完成后，PersonaLab将呈现为：
- **专业的视觉形象**：logo和品牌一致性
- **清晰的价值主张**：Simple as mem0, Powerful as PersonaLab  
- **开发者友好**：标准安装流程和文档
- **社区就绪**：完整的开源项目配置

这将大大提升项目的专业度和吸引力！ 