# Codex：检索与注入

## 触发与查询 {#trigger}

`memu-codex install` 在选定 Codex home 的 `hooks.json` 中注册 `UserPromptSubmit` 检索和后台记忆命令，通过 app-server 注册信任，并检查 Codex 确认了异步检索。默认 home 为 `~/.codex`，安装与运行应使用相同 home/profile。

每次提交非空输入都会启动检索，首轮回答无需等待记忆。Hook 遵循[共享查询策略](retrieval.md#query)：默认关闭提取，使用最多 800 字符的前缀；开启提取后，通过隔离、临时的 Codex 请求生成查询，禁用 hooks 和规则。该请求沿用选定的 Codex 配置，提取限时 12 秒。

## 注入时机 {#injection}

检索完成后，hook 通过 `UserPromptSubmit` 的 `hookSpecificOutput.additionalContext` 返回结果。异步上下文何时被消费由 Codex 决定，此时首轮响应可能已经开始。上下文包含查询元数据、retrieve 子进程耗时、hits、resources 和投递数量。Hook 不额外限制上下文长度（`additionalContextLimit: 0`），hits 仍最多五条。

空结果也会返回完成元数据。检索失败时记录错误，不返回记忆上下文，不阻塞用户原始请求。检索文本只作为参考数据。

## 写入独立运行 {#recording}

第二个 submit hook 启动分离的后台记忆处理，受准入检查、工作区锁和冷却期约束。它独立于检索处理会话历史，不保证正在回答的输入已经保存或立即可检索。用户自行配置的历史定时任务需检查，避免重复处理。

## 激活与验证 {#verify}

```sh
memu-codex doctor
memu-codex retrieve "已保存的主题"
```

安装后再发送一条消息，检查 `~/.memu/hosts/codex/log/hooks/retrieve/`（或自定义 base 目录）。核对查询、`extraction_status`、数量和 `additional_context`，注意追踪内容的隐私。安装器的信任检查和手动检索不能证明运行中会话已经收到结果。如果当前客户端尚未加载 hooks，开启新会话，再验证真实 submit 事件。

后端和查询选项见[配置](../reference/configuration.md)，包内安装指南通过 `memu-codex docs install` 查看。
