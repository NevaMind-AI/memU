# 0026：查询提取的生命周期独立于 hook 父进程

- 状态：提案
- 任务：[#790 / task-005](https://github.com/NevaMind-AI/memU/issues/790)
- 关联：[ADR 0021](0021-pi-extension-hooks.md)、[ADR 0022](0022-host-memory-hooks.md)
- [English](0026-query-extraction-lifetime.md)

## 已确认范围

hook Python 被强制终止时，也必须清理查询提取进程。普通取消和既有的 12 秒超时同样需要清理。

三个提取适配器共用 `run_extraction()`。pi 在 `asyncio.to_thread()` 工作线程中调用它，并在会话关闭时通过 `child.kill()` 结束检索 Python。工作线程不能安装 Python signal handler，被强制终止的进程也无法执行自己的 `finally`。提取任务需要由能跨越 hook 退出的机制负责清理。

取消意味着本次检索工作失效，不能触发前缀回退或交付旧上下文。真实提取错误和正常超时保留现有回退行为。保留共享提取接口的输入输出、宿主环境、pi 的非阻塞输入和基于会话代次的交付检查。

## 决策

每次提取增加一个只依赖标准库的短命 Python runner。通过启动握手，确保进程归属边界建立后才允许宿主 CLI 执行。新的命令行协议不承载完整 prompt 或环境凭据，保留原始输入输出 bytes、提取器参数、工作目录和退出分类。

POSIX runner 使用独立 session 跨越 hook 退出，监听专用父进程存活管道，并为实际提取器创建另一个独立 process group。管道写端只由 hook 持有。Windows 则由 hook 独占不可继承、关闭时终止成员的 Job handle，将等待握手的 runner 加入 Job 后才允许启动提取器；后代继承该 Job。

保留既有 12 秒提取期限，runner 启动时间计入该期限。pi 的 coroutine 取消需要显式取消本次提取，因为只取消 `to_thread()` 不会结束工作线程。保留普通超时及非零退出的异常分类，取消单独处理。

监管建立失败时，跳过宿主 CLI 并按现有策略前缀回退。成功、非零退出、超时和取消均清理本次提取所属的进程，包括在 CLI 退出后仍存活的后代。

清理保证限定在本任务的 process group 或 Job。POSIX 监管进程自身同时被强杀、主动脱离的后代及无关共享服务不在此边界内。进程清理也不能证明远端模型请求已停止。

## 验证计划

使用本地模拟提取程序及临时目录，覆盖成功、非零退出、超时、主动取消、hook 强制终止、重复清理、启动竞态、多级后代，并保留无关进程作为对照。验证 pi 的工作线程调用路径，断言取消后既不触发回退检索，也不交付旧结果。

在 macOS、Linux 和 Windows 运行真实子进程测试。真实宿主行为与进程级测试分别记录。

## 真实宿主退出验收

在 macOS 26.6.2（arm64）验证运行时代码 `89810e1`。两个真实宿主均运行 memU 的 `UserPromptSubmit` 入口，Codex 使用 `async: true`，Claude Code 使用 `asyncRewake: true` 加 `--rewake`。测试使用临时工作区、回环地址上的模型和记忆端点，并在可执行文件发现处换入模拟提取器。模拟提取器启动一个休眠后代并报告 PID 后，才触发宿主退出。测试记录记忆请求，并在 hook 和宿主输出中检查唯一的上下文标记。

| 宿主及动作 | 退出和投递观测 |
| --- | --- |
| Codex CLI `0.169.0-alpha.11.1`，`exec --ephemeral` 成功对照 | hook 记录 `context_returned`。第二次本地 `/v1/responses` 请求携带唯一上下文标记。宿主以状态 0 退出，hook、runner、提取器和后代均停止。 |
| Codex CLI `0.169.0-alpha.11.1`，提取仍在运行时正常退出 | 本地模型返回完整响应后，宿主以状态 0 退出。退出后 2 秒检查时，hook、runner、提取器和后代均已停止。未观察到记忆检索请求、上下文标记或已完成的 hook 记录。 |
| Codex CLI `0.169.0-alpha.11.1`，`exec --ephemeral` 期间收到 `SIGINT` | 宿主退出码为 1。退出后 2 秒检查时，hook、提取器和后代均已停止。模型请求已到本地端点，取消后未观察到记忆检索请求或已完成的 hook 记录。 |
| Codex CLI `0.169.0-alpha.11.1`，仅向宿主发送 `SIGKILL` | 宿主退出码为 -9，2 秒后 hook 及其提取进程树仍在运行。测试程序清理这些进程前，未观察到记忆检索请求或上下文标记。 |
| Claude Code `2.1.303`，正常结束 `-p --input-format stream-json` | 提取仍在运行时，本地模型已返回响应。stdin 收到 EOF 后 2 秒，宿主和提取进程树仍在运行。放行提取器后，hook 完成，宿主以状态 0 退出，hook、runner、提取器和后代均停止。唯一一次模型请求未携带上下文标记。 |
| Claude Code `2.1.303`，`-p` 期间收到 `SIGTERM` | 宿主退出码为 143。600 ms 后检查时，hook、runner、提取器和后代均已停止。没有记忆检索请求或上下文标记。 |
| Claude Code `2.1.303`，仅向宿主发送 `SIGKILL` | 宿主退出码为 -9，hook 及其提取进程树仍在运行。随后对该测试 hook 发送 `SIGTERM`，runner、提取器和后代均停止。此过程中没有记忆检索请求或上下文标记。 |

Claude Code 成功对照中，本地记忆端点返回了上下文标记。真实 hook 记录 `context_returned`，宿主的 `UserPromptSubmit operation blocked by hook:` 输出包含该标记。这验证了该版本 `-p` 下可观测的 hook 到宿主输出通路。

同版本 Codex 在隔离的 Linux arm64 容器中也通过了提取仍在运行时的正常退出测试。宿主退出时四个进程均已停止。测试端点仅收到一次未携带上下文标记的模型请求，未收到记忆检索请求。

进程树清理由 hook 退出触发。仅强制结束宿主且 hook 仍存活时，hook 的存活管道保持打开。
