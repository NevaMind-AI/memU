# 检索与注入

检索搜索已有记忆；注入让返回的上下文进入宿主模型。后台记忆会在之后写入持久化内容，检索成功不代表当前对话已经保存。

## 各宿主的时机 {#timing}

以你点击发送为分界，分开看两件事：**什么时候开始搜索**，以及**搜索结果什么时候用于回答**。

- **发送前（before submit）**：先检索，再发送提示词给模型。
- **发送时（on submit）**：点击发送就启动检索，回答可以同时开始。
- **发送后（after submit）**：Agent 收到请求后，在处理任务时检索。

下表的「当轮」指这次请求的回答；「后续回合」指首轮回答后的继续处理，不一定需要你再发一条消息。

| 宿主 | 什么时候开始检索 | 当轮还是后续回合使用 |
| --- | --- | --- |
| [Codex](codex.md) | **发送时（on submit）**，后台搜索 | 后台检索，返回后注入；赶上当前回答就当轮使用，否则留到下一轮 |
| [Claude Code](claude-code.md) | **发送时（on submit）**，后台搜索 | 检索完成后唤醒 Agent；首轮已结束时，会继续回答 |
| [pi](pi.md) | **发送时（on submit）**，后台搜索 | 返回后注入；正在回答就接着用，回答结束则自动继续一轮 |
| [Hermes](hermes.md) | **发送后（after submit）**，Agent 按需搜索 | 当轮：需要记忆时先读取结果，再继续回答或任务 |
| [Cursor](cursor.md) | **发送后（after submit）**，Agent 按指令在回答前搜索 | 当轮：读取结果后回答，依赖 Agent 遵循指令 |
| [OpenClaw](openclaw.md) | **发送后（after submit）**，Agent 按指令在回答前搜索 | 当轮：读取结果后回答，依赖 Agent 遵循指令 |
| [WorkBuddy](workbuddy.md) | **发送后（after submit）**，Agent 按指令在回答前搜索 | 当轮：读取结果后回答，依赖 Agent 遵循指令 |

当前这些接入方式都不会在发送前等待检索完成。后台搜索的完成时间会影响记忆能否用于首个回答。各宿主页面进一步说明实现、激活与验证方法。

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
