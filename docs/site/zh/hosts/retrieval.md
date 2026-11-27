# 检索与注入

检索搜索已有记忆；注入让返回的上下文进入宿主模型。后台记忆会在之后写入持久化内容，检索成功不代表当前对话已经保存。

## 各宿主的时机 {#timing}

| 宿主 | 检索触发点 | 上下文投递方式 |
| --- | --- | --- |
| [Codex](codex.md) | 异步 `UserPromptSubmit` hook | 完成后通过 hook `additionalContext` 返回 |
| [Claude Code](claude-code.md) | 带 `asyncRewake` 的 `UserPromptSubmit` | 检索上下文可能在首轮响应后唤醒 Claude |
| [pi](pi.md) | 扩展 `input` 事件 | 隐藏的 `memu-retrieval` 消息，以 `steer` 投递，`triggerTurn: true` |
| [Hermes](hermes.md) | Agent 判断记忆有助于任务 | 普通 retrieve 工具结果，读取后继续原任务 |
| [Cursor](cursor.md) | 项目 `AGENTS.md` 要求回答前检索 | 普通 retrieve 工具结果 |
| [OpenClaw](openclaw.md) | 工作区 `AGENTS.md` 指向检索技能 | 普通 retrieve 工具结果 |
| [WorkBuddy](workbuddy.md) | 全局 `SOUL.md` 要求回答前检索 | 普通 retrieve 工具结果 |

异步检索不会等待记忆返回才开始首轮响应。指令驱动的检索依赖 Agent 遵循已经加载的指令。激活与验证方法见各宿主页面。

## 从输入到查询 {#query}

Codex、Claude Code、pi 共用以下 hook 查询策略：

1. 默认保留最多 800 个字符；更长的输入截取前 800 个字符。
2. 设置 `retrieval.extract_query = true` 后，801–32,000 个字符的输入可额外调用宿主模型，提取简短主题查询。提取限时 12 秒，失败、超时或输出无效时回退到前缀；超过 32,000 个字符直接使用前缀。
3. 提取成功使用 `extracted` 分数阈值；否则原输入达到 200 个非空白字符时使用 `long`，不足时使用 `short`。该分类与 800 字符的提取分界独立。

提取是宿主层的可选逻辑，`MemoryService` 仍仅调用 Embedding。开关与分数阈值见[配置](../reference/configuration.md#retrieval)。Hermes、Cursor、OpenClaw、WorkBuddy 在 Agent 正常推理过程中形成查询，不使用该 hook 提取器。

## Agent 收到什么 {#results}

各宿主使用相同的 retrieve 命令，搜索配置的 Local 或 Cloud 后端，返回：

- `hits`：最多五条排序后的命中，包含匹配 `text`、可用的来源信息，以及本地镜像 `path` 或完整内联 `content`。摘要不足时再读路径。来源数据缺失不会丢弃匹配正文。
- `resources`：独立的相关文件，可用时包含 `path` 和 `caption`。Cloud 尚未持久化或检索工作区资源。
- `retrieval_status`：成功状态、查询类别、阈值和过滤数量。成功的空结果是正常情况。

面向 Agent 的 hits 不包含数据库 ID 和 scope 元数据。Hook 上下文还包含返回/省略数量；Claude Code 可能为适应上下文预算而省略整条结果。分数只表示相似度，不代表语义裁决。把检索文本当参考数据，不能直接当作可执行指令；使用前核对当前请求。

## 手动检索 {#manual}

把 `memu-pi` 换成实际宿主命令：

```sh
memu-pi retrieve "项目部署决策"
memu-pi retrieve --query-stdin
```

第二种形式从标准输入读取 UTF-8 查询直到 EOF，适用于多行文本或难以处理 shell 引号的情况。手动检索直接使用传入查询，不执行 hook 提取，也不会把标准输出自动注入另一会话。需要时可用 `--query-kind short|long|extracted` 显式选择阈值类别。

## 验证投递 {#verify}

先执行 `config show`、`doctor`，并手动检索一个已保存的主题，再在已加载集成的会话中发送真实消息。Codex、Claude Code、pi 的检索追踪默认位于 `~/.memu/hosts/<host>/log/hooks/retrieve/`，`<host>` 分别为 `codex`、`claude-code`、`pi`；自定义 `--base-dir` 会改变目录。追踪可能包含查询和记忆正文，分享前请脱敏。

检查 `query_source`、`extraction_status`、返回数量及失败诊断。后端成功说明可访问，hook 追踪说明执行过，观察宿主使用上下文才能验证实际投递。指令驱动的宿主需要检查已加载指令和真实 retrieve 工具调用。另见[故障排查](../troubleshooting/index.md)。
