# 文档维护

## 本地运行

在仓库根目录使用 Node.js 22.12+ 和 pnpm 11.15.1（版本见 `docs/package.json`）：

```sh
pnpm --dir docs install --frozen-lockfile
pnpm --dir docs dev
```

打开 VitePress 打印的 localhost 地址。检查生产构建时运行：

```sh
pnpm --dir docs build
pnpm --dir docs preview
```

生成的站点位于 `docs/.vitepress/dist/`。本地开发和预览无需 GitHub Pages 权限。

## Python 开发

开发源码时，在仓库根目录通过 uv 执行命令：

```sh
uv sync --python 3.13
uv run pre-commit install
uv run memu-pi --help
uv run python -m pytest tests/test_agentic.py
```

`uv sync` 准备项目的 `.venv`；`uv run` 使用该环境和当前检出的源码。快速开始中的 tool 安装用于日常使用 CLI。文档站本身仍按上文使用 pnpm。

## 改动应该写在哪里

| 内容 | 位置 |
| --- | --- |
| 项目介绍、最短上手路径、文档入口 | 根目录 `README.md` |
| 安装和日常使用 | `docs/site/guide/` |
| 宿主接入与限制 | `docs/site/hosts/` |
| CLI、配置、API 契约和存储选项 | `docs/site/reference/` |
| 诊断和可复用修复方法 | `docs/site/troubleshooting/` |
| 开发流程和当前架构 | `docs/site/development/` |
| 架构决策及其背景 | 现有 `docs/adr/` |
| 按版本汇总的变化 | 根目录现有 `CHANGELOG.md` 与 Release |
| 社区任务范围和验收条件 | 现有 `docs/community/` |

例如，新增环境变量应更新配置参考；修改 pi 检索应更新宿主指南；做出架构决策应新增 ADR，并更新当前行为说明。

## 同步两种语言

英文站点从 `docs/site/` 开始，中文在 `docs/site/zh/` 下使用相同路径。同次改动同步更新两种语言的页面，保持示例、范围和验收标准一致。翻译章节需要稳定共享锚点时，使用显式且一致的标题 ID。

站内使用指向 Markdown 源文件的相对链接。新增页面需同步加入 `docs/.vitepress/config.ts` 中对应语言的侧栏。构建会检查页面链接，请保留断链错误。本地搜索会自动索引站点内容。

## 复用现有来源

宿主安装、任务和卸载指南继续放在 `src/memu/hosts/<host>/`，供 CLI 读取包内资源。安装行为变化时更新这些源文件；网站解释入口并指向 CLI 指南，避免复制完整安装流程。

站点源目录为 `docs/site/`。现有 ADR 和社区任务保留既有路径，通过仓库链接访问，不复制进站点。ADR 记录历史决策，当前行为应对照实现确认。站点目录以外的研究笔记不会被站点构建发布。

现有 `docs/sqlite.md` 包含旧示例。受支持的构造函数与存储配置见[当前配置参考](../reference/configuration.md)和 [MemoryService](../reference/service.md)。

## 提交前

1. 更新行为所属页面及其翻译。
2. 运行 `pnpm --dir docs build`，通过 preview 检查改动页面。
3. 对照已安装 CLI 验证命令，对照实现检查代码示例。站点构建成功并不代表示例已经执行。
4. 在 PR 中列出文档更新，或说明文档不受影响的原因。版本摘要沿用现有发布流程。
