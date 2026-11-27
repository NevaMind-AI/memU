# WorkBuddy：检索与注入

## 触发与查询 {#trigger}

配置后端后，按 `memu-workbuddy docs install` 操作。`memu-workbuddy install-instruction` 将检索流程内联写入 `~/.workbuddy/SOUL.md` 的托管块。WorkBuddy 将这个全局行为文件加载到会话，修改后开启新会话。

指令要求 Agent 回答前检索。Agent 形成聚焦查询，通过普通命令工具执行 `memu-workbuddy retrieve "<query>"`。该流程由指令驱动：memU 不为 WorkBuddy 安装自动逐输入检索 hook，这里也不执行可选的 hook 查询提取器。

## 注入时机 {#injection}

retrieve 完成时，工具输出成为对话上下文。Agent 使用相关摘要，仅在需要时读取返回的来源路径，再继续回答。内容见[共享结果格式](retrieval.md#results)。空结果不应阻止任务。

`SOUL.md` 承载的是检索指令，不是记忆库正文。检索依赖 Agent 在当前会话中遵循指令并执行工具调用。

## 迁移与写入 {#recording}

默认路径的指令安装会先安全写入新的 `SOUL.md` 块，再从 `~/.workbuddy/MEMORY.md` 清理可识别的旧 memU 块。用户编写的记忆保持不变。`MEMORY.md` 不是当前的检索指令目标。

独立的 bridging 任务按安装指南配置的计划处理会话历史。它负责写入持久化记忆，不向当前响应注入上下文。写入与检索需共用后端和 Embedding 设置。

## 激活与验证 {#verify}

```sh
memu-workbuddy doctor
memu-workbuddy retrieve "已保存的主题"
memu-workbuddy install-instruction --dry-run
```

检查 `SOUL.md` 中只有一个托管块，`MEMORY.md` 中不再有旧 memU 块。开启新会话，使用已知记忆主题，观察真实 retrieve 调用。手动成功只能证明后端可访问，不能证明 WorkBuddy 已加载指令或使用结果。

配置见[配置参考](../reference/configuration.md)，完整安装与调度通过 `memu-workbuddy docs install` 查看。
