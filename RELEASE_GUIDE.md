# PersonaLab 发布指南

## 🚀 自动发布到PyPI

PersonaLab使用GitHub Actions和Trusted Publisher实现自动发布。

### 📦 发布流程

1. **准备发布**
   ```bash
   # 1. 更新版本号
   # 编辑 personalab/__init__.py, setup.py, pyproject.toml
   
   # 2. 更新CHANGELOG.md
   # 添加新版本的更改日志
   
   # 3. 提交更改
   git add .
   git commit -m "Bump version to 0.1.1"
   git push origin main
   ```

2. **创建GitHub Release**
   - 访问：https://github.com/NevaMind-AI/PersonaLab/releases/new
   - 创建新标签：`v0.1.1` (与版本号一致)
   - 填写Release标题：`PersonaLab v0.1.1`
   - 添加Release说明 (可以从CHANGELOG.md复制)
   - 点击 **"Publish release"**

3. **自动发布**
   - GitHub Actions会自动构建并发布到PyPI
   - 监控状态：https://github.com/NevaMind-AI/PersonaLab/actions

### ✅ 发布后验证

- [ ] 检查GitHub Actions状态 (绿色✅)
- [ ] 验证PyPI页面：https://pypi.org/project/personalab/
- [ ] 测试安装：`pip install personalab==0.1.1`
- [ ] 测试导入：`python -c "import personalab; print(personalab.__version__)"`

### 🛠️ 故障排除

**常见问题：**
- **版本冲突**: 如果版本号已存在，需要更新版本号
- **构建失败**: 检查代码质量和依赖项
- **权限错误**: 确保Trusted Publisher配置正确

**获取帮助：**
- GitHub Actions日志：https://github.com/NevaMind-AI/PersonaLab/actions
- PyPI项目页面：https://pypi.org/project/personalab/

---

**就是这么简单！** 🎉 创建Release即可自动发布到PyPI。 