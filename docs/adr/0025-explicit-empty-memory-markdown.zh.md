# ADR 0025：空正文 memory Markdown 的显式确认

- 状态：提案；已实现，待审阅
- 议题：MEM-9；关联：MEM-13
- 扩展：[ADR 0024](0024-memory-clearing-through-commit.zh.md)
- [English](0025-explicit-empty-memory-markdown.md)

## 目标 {#goal}

避免意外丢失的 Markdown 正文清空已存储记忆。主动清空需要明确确认，恢复正文自动回到普通提交。

## 决策 {#decision}

host bridging commit 和开发者 `memu memorize commit` 共用的 Markdown 读取器，在 memory 正文去除空白后为空时，要求 frontmatter 中恰好有一个字面值为 `empty: true` 的字段：

```markdown
---
name: reading-preference
description: Reading preferences
empty: true
---
```

缺少标记、值为 false、带引号或重复的确认标记均在调用后端前拒绝提交。保留原有 name 和 description。普通零字节文件仍因缺少名称而校验失败。本地文件缺失不提交清空。skill 文件沿用现有行为。

只要正文非空，就恢复普通提交，即使 frontmatter 仍有 `empty` 字段。提交成功后，客户端以原子写入方式移除该字段，再更新 manifest 快照。因此确认标记被消费，之后正文再次意外为空时需要重新明确确认。后端失败会保留文件、确认标记和待提交运行状态，支持重试。

标记仅是本地 Markdown 元数据，不进入后端 payload。直接调用 `commit_results` 和 JSON `memu commit` 保留现有空正文语义。仓库 schema、后端一致性和 Cloud API 均不受影响。清空后仍保留后端记录和元数据；Markdown 提交成功后沿用 ADR 0024 移除本地空镜像。

## Agent 指引 {#guidance}

memory job 在选定模板渲染后追加提交约定，覆盖远端及缓存模板。agent 主动清空时添加确认标记并移除正文；恢复时只需写入非空正文。

## 验证 {#validation}

测试覆盖空及纯空白正文、无效确认标记、skill 隔离、标记不进入 payload、自动恢复并移除标记、后续再次意外为空、后端失败及重试，以及两个 Markdown 提交入口。检查使用合成记录和临时目录；本补丁不操作生产记忆，也不证明后端事务原子性。
