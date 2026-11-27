# OpenClaw：检索与注入

## 触发与查询 {#trigger}

配置后端后，按 `memu-openclaw docs install` 操作。`memu-openclaw install-instruction` 在 `~/.openclaw/workspace/AGENTS.md` 安装指针，在 `~/.openclaw/skills/memu-retrieve/SKILL.md` 安装检索流程。OpenClaw 在会话开始时加载工作区指令，安装后开启新会话。

指令要求 Agent 回答前使用检索技能。Agent 形成查询，再以普通命令工具调用 `memu-openclaw retrieve "<query>"`。memU 不为该宿主安装自动逐输入检索 hook，可选的 hook 查询提取开关不控制此路径。

## 注入时机 {#injection}

retrieve 完成后，工具结果进入当前对话。Agent 使用相关摘要，或在需要时读取返回路径，再继续任务。返回内容见[共享结果格式](retrieval.md#results)。空结果或检索失败时应继续原任务。

常驻指针是加载的上下文；记忆结果只有在实际调用 retrieve 后才到达。配置了写入调度不代表检索技能已经执行。

## Profile 与写入 {#recording}

使用自定义 `OPENCLAW_STATE_DIR` 时，安装指令需通过 `--skills-dir` 指定其托管 skills 目录；工作区不同时，通过 `--path` 指定实际 `AGENTS.md`。安装与运行保持相同工作区/profile。

独立的 bridging 任务按安装指南配置的计划处理会话历史。它写入相同后端，但不向正在进行的回合投递结果。记忆在处理与提交完成后才可检索。

## 激活与验证 {#verify}

```sh
memu-openclaw doctor
memu-openclaw retrieve "已保存的主题"
memu-openclaw install-instruction --dry-run
```

同时检查工作区指令和技能文件。在新会话中询问已知记忆，确认真实工具调用和相关结果使用。手动后端检查不能证明 OpenClaw 加载了正确工作区或技能。

配置见[配置参考](../reference/configuration.md)，安装和调度通过 `memu-openclaw docs install` 查看。
