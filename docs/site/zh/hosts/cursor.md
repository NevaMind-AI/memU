# Cursor：检索与注入

## 触发与查询 {#trigger}

Cursor 使用各项目根目录的 `AGENTS.md` 指令。配置后端后，按 `memu-cursor docs install` 操作；在项目根目录执行 `memu-cursor install-instruction` 安装托管块。需要记忆的每个项目都要安装，其他没有该块的 checkout 不会自动继承。

加载后的指令要求 Agent 回答前检索。Agent 根据用户请求形成聚焦查询，通过普通命令工具执行 `memu-cursor retrieve "<query>"`。memU 不会为 Cursor 注册自动逐输入检索 hook，该路径也不使用可选的 hook 查询提取器。

## 注入时机 {#injection}

retrieve 命令完成后，工具输出进入上下文。Agent 在组织或继续回答前使用相关结果，仅在摘要不足时读取返回的路径。内容遵循[共享结果格式](retrieval.md#results)，空结果时正常继续。

这一流程依赖 Cursor 加载项目 `AGENTS.md`，且 Agent 遵循其中指令。仅安装后台调度不会提供检索指令。

## 写入独立运行 {#recording}

安装指南通过 standalone `cursor-agent` CLI 配置 bridging 任务来处理会话历史。该任务按配置的计划写入记忆，不向当前对话注入上下文。新对话内容只有在处理和提交完成后才能检索。

## 激活与验证 {#verify}

```sh
memu-cursor doctor
memu-cursor retrieve "已保存的主题"
memu-cursor install-instruction --dry-run
```

在目标项目中执行。检查 `AGENTS.md` 只有一个 memU 托管块，用户内容保留完整。开启新的项目会话，询问已知记忆，确认真实 retrieve 工具调用和结果使用。手动检索只能证明后端可访问，不能证明 Cursor 已加载指令。

配置见[配置参考](../reference/configuration.md)，完整安装及调度前提通过 `memu-cursor docs install` 查看。
