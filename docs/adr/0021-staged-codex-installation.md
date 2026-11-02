ADR 0021: Codex 安装由 Python 分阶段执行，Desktop Agent 负责旧任务交接

- 状态：提议中
- 基于：ADR 0009、0010、0013、0017
- 范围：Codex 安装编排、阶段进度与旧 Desktop 自动化任务交接。

## 背景

Agent 按 Markdown 自行完成配置、程序准备和注册，难以复现中途失败、重复执行及迁移顺序。
终端用户需要同一套确定性安装逻辑。Desktop 自动化管理依赖宿主工具，独立 Codex CLI
当前调查到的命令和 app-server 协议不能承担完整任务管理。

## 决定

在 Codex 适配层提供 `memu-codex install`，复用配置命令、doctor、程序准备和双 hook 注册。
五阶段覆盖条件检查、后端、Codex CLI、注册和最终检查；支持连续执行、JSONL 进度与
`--stage` 单阶段调用，允许 Agent 在同步工具返回后及时汇报。状态文件保存通过阶段和检查哈希。

安装使用默认 `~/.codex` 共享配置及认证。新注册的后台 handler 也固定使用该目录。
Agent 调用前确认 Full access；CLI 检查操作是否实际成功。

直接终端安装提示用户到 Desktop 暂停旧 memU 任务，完成时标明 `desktop_deferred`。
`--agent` 路径要求完整交接：确认任务归属、保存定义、暂停并等待空闲，然后注册和验证替代入口，
最后删除旧任务并回读。Desktop Agent 提供包含本地证据文件的报告；CLI 检查格式与交接连续性，
远端真实性和清单完整性仍由 Desktop Agent 负责。

复用现有 workspace lock，与记忆 worker 互斥；保留游标、self-session、待处理任务、可恢复结果、
日志、用户配置和第三方集成。未知编辑的旧检索入口由 Agent 检查后定向清理。

## 结果与验收

安装行为可以在临时目录中通过操作顺序、退出码和磁盘状态测试。普通 CI 替代外部宿主进程；
真实安装器、Desktop 任务迁移、用户提交后的检索与记忆另行验收。
Codex 首先实现这套边界；其他宿主继续沿用现有流程，后续复用以实际需求为准。

完整命令与证据契约见 [Codex CLI 安装契约](../codex-cli-installation.md)。
