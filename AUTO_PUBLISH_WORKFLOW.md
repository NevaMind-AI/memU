# PersonaLab 自动发布工作流程

## 📦 自动发布触发条件

### 🧪 Test PyPI (测试环境)
**自动触发条件：**
- 推送版本标签 (如 `v0.1.0`, `v0.1.1`)
- 手动触发 (GitHub Actions页面)

**使用场景：**
- 测试发布流程
- 验证包的安装和导入
- 预发布测试

### 🚀 正式 PyPI (生产环境)
**自动触发条件：**
- 创建GitHub Release

**使用场景：**
- 正式版本发布
- 用户可以通过 `pip install personalab` 安装

## 🔄 发布流程

### 方法1：推送标签自动发布到Test PyPI

```bash
# 1. 更新版本号
# 编辑 personalab/__init__.py, setup.py, pyproject.toml

# 2. 提交更改
git add .
git commit -m "Bump version to 0.1.1"

# 3. 创建并推送标签
git tag v0.1.1
git push origin v0.1.1

# 4. 自动触发Test PyPI发布
# GitHub Actions会自动运行并发布到Test PyPI
```

### 方法2：创建Release自动发布到正式PyPI

```bash
# 1. 确保代码已推送到main分支
git push origin main

# 2. 在GitHub上创建Release
# 访问: https://github.com/NevaMind-AI/PersonaLab/releases/new
# - 选择或创建标签 (如 v0.1.1)
# - 填写Release标题和描述
# - 点击 "Publish release"

# 3. 自动触发正式PyPI发布
# GitHub Actions会自动运行并发布到PyPI
```

## 📋 发布检查清单

### 发布前检查
- [ ] 版本号已更新 (personalab/__init__.py)
- [ ] CHANGELOG.md已更新
- [ ] 所有测试通过
- [ ] 代码已格式化 (black, isort)
- [ ] 文档已更新

### 发布后验证
- [ ] 检查GitHub Actions状态
- [ ] 验证PyPI页面包信息
- [ ] 测试安装: `pip install personalab==新版本`
- [ ] 测试导入: `python -c "import personalab; print(personalab.__version__)"`

## 🛠️ 故障排除

### 常见问题
1. **版本冲突**: 如果版本号已存在，PyPI会拒绝上传
   - 解决: 更新版本号并重新发布

2. **权限错误**: Trusted Publisher配置问题
   - 解决: 检查GitHub Actions权限设置

3. **构建失败**: 包构建或测试失败
   - 解决: 检查依赖项和代码质量

### 监控发布状态
- **GitHub Actions**: https://github.com/NevaMind-AI/PersonaLab/actions
- **PyPI页面**: https://pypi.org/project/personalab/
- **Test PyPI页面**: https://test.pypi.org/project/personalab/

## 🎯 最佳实践

1. **版本管理**: 使用语义化版本控制 (semver)
2. **测试优先**: 先发布到Test PyPI验证
3. **标签管理**: 保持标签与版本号一致
4. **文档同步**: 确保文档与代码版本匹配

---

**现在PersonaLab的发布流程已完全自动化！** 🚀

只需要推送标签即可自动发布到Test PyPI，创建Release即可自动发布到正式PyPI。 