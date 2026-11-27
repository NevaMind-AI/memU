# Claude Code：检索与注入

## 触发与查询 {#trigger}

`memu-claude-code install` 在 `~/.claude/settings.json` 中写入两个 `UserPromptSubmit` 命令。检索 hook 使用 `asyncRewake: true` 和 `prompt-hook --rewake`，另一个命令负责后台记忆准入。开启新的 Claude 会话后加载这些 hooks。

检索 hook 跳过自动事件、空输入和自身记忆处理会话。其他输入遵循[共享查询策略](retrieval.md#query)，默认关闭提取。长输入开启提取时，通过隔离的 standalone Claude 请求生成查询，禁用工具、MCP servers 和 hooks，且不保存会话。12 秒提取时限计入检索工作预算。

## 注入时机 {#injection}

安装的 `--rewake` 模式把检索上下文写入 stderr，并以状态码 2 退出，让 Claude 的异步 hook 机制携带上下文唤醒 Agent，可能发生在首轮响应之后。该退出状态是有意使用的上下文投递信号。不带 `--rewake` 调用 `prompt-hook` 时，返回结构化的 `additionalContext` JSON。

上下文预算为 9,500 个 UTF-16 单元，包含前缀和 JSON。Hook 保留完整条目，先考虑 hits，再考虑 resources，报告返回/省略数量。超大条目整条省略，不截断条目正文。检索成功但为空时仍可能返回完成状态上下文；失败时记录本地诊断，不返回检索上下文。

## 写入独立运行 {#recording}

后台记忆 hook 同样在提交时运行，分离的 worker 受准入检查、锁和冷却期约束；注册成功不代表处理已完成。写入与检索保持相同后端，并检查用户自行配置的历史定时任务是否造成重复处理。

## 激活与验证 {#verify}

```sh
memu-claude-code doctor
memu-claude-code retrieve "已保存的主题"
```

开启新 Claude 会话，发送相关消息，再检查 `~/.memu/hosts/claude-code/log/hooks/retrieve/`（或自定义 base 目录）。核对状态、`additional_context`、预算和省略数量。本地 settings 回读只能证明注册；观察上下文投递才能验证宿主执行。模型请求认证验证与安装成功分别检查。

配置见[配置参考](../reference/configuration.md)，安装细节通过 `memu-claude-code docs install` 查看。
