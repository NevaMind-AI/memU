# memU 社区贡献任务

[English](tasks.en.md) | [简体中文](tasks.md)

👋 欢迎从感兴趣的小任务开始！在 [社区入口 #790](https://github.com/NevaMind-AI/memU/issues/790) 留言认领，说明任务编号、实现思路及准备验证的平台，等待维护者确认范围后开始。

本页维护任务背景、实现范围和验收标准；**认领人、最新进展及关联 PR 以 #790 中维护者确认的记录为准**。复杂任务先讨论方案，必要时再开独立 RFC Issue。PR 请关联 #790，注明任务编号并链接本页对应章节。

## 📋 任务目录

编号用于长期引用，完成后保留记录，不重新分配。下表的 ⭐ 表示难度，按编号排列。

| 编号 | 任务／方向 | 类型 | 难度 | 开放状态 |
| --- | --- | --- | --- | --- |
| 001 | [统一 Codex 检索日志格式](#task-001) | 🛠️ 工程改进 | ⭐ | 🙋 开放认领 |
| 002 | [pi 的 hook 接入](#task-002) | 🔌 Host 集成 | ⭐⭐～⭐⭐⭐，按阶段拆分 | ✅ 已完成：#796 |
| 003 | [Claude Code 遗留系统定时任务的检查与移除](#task-003) | 🛠️ 工程改进 | ⭐⭐／平台 | 🙋 三个平台可分别认领 |
| 004 | [Codex / Claude skill 移除的文件归属保护](#task-004) | 🛠️ 工程改进 | ⭐⭐ | 🙋 开放认领 |
| 005 | [query-extract 取消与父进程退出时的进程树清理](#task-005) | 🛠️ 工程改进 | ⭐⭐⭐ | 💬 开放认领，先讨论方案 |
| 006 | [独立用户文档网站 memU-docs](#task-006) | 📚 文档建设 | ⭐⭐ | 📝 待拆分，暂未开放认领 |
| 007 | [已安装 host 的统一检查与 hook 更新](#task-007) | 🛠️ 工程改进 | ⭐⭐⭐ | 📝 待拆分，暂未开放认领 |

## 🤝 参与方式

1. 阅读任务范围、验收标准和历史讨论，在 #790 评论区认领；任务 003 请注明平台。
2. 维护者确认后开始。涉及生命周期、认证、并发或跨平台设计的任务，先讨论方案并拆成可独立审查的小改动。
3. 提交 PR，关联 #790 和任务编号，说明改动并提供必要的测试或实际验证记录。开发环境和提交要求见 [CONTRIBUTING.md](../../CONTRIBUTING.md)。
4. 根据 review 完善；需要扩展范围、暂停或退出时，在认领记录下沟通。任务完成并验收后，由维护者同步更新两种语言的任务文档及 #790。

认领示例：

```text
认领：task-003 / Windows
实现思路：复用已有 scheduler helper，先核对历史任务名称和动作。
验证环境：Windows，注明版本及使用权限。
```

### ⭐ 难度说明

- **⭐ 入门**：范围明确、改动局部，有现成实现和测试可参考。
- **⭐⭐ 进阶**：需要理解完整流程，涉及宿主适配、异常处理或集成验证。
- **⭐⭐⭐ 及以上**：涉及生命周期、认证、并发或跨平台行为，先讨论方案，再拆分实现。

欢迎使用 Coding Agent 辅助开发。提交前请阅读改动、运行必要测试，并能解释关键实现；清楚的分析和验证记录有助于审查顺利推进 🌱

<a id="task-001"></a>

## 001 · 统一 Codex 检索日志格式

类型：🛠️ 工程改进｜难度：⭐｜开放认领

**背景与范围**

Codex 检索日志位于 `~/.memu/hosts/codex/log/hooks/retrieve/<时间戳>-<pid>.log`，一个文件包含开始记录和最终记录，每条 JSON 都挤在一行里。Claude Code 使用 `<uuid>.json`，每次检索一个缩进 JSON 文件，更方便阅读查询、命中正文和投递上下文。

将 Codex 改成每次检索一个带缩进的 `.json` 文件。日志目录保持不变，旧 `.log` 文件保留。

**验收标准**

- 成功、空结果和失败都能留下单次检索的 JSON 日志。
- 保留已有字段，包括查询、提取状态、耗时、`retrieve_result`、`additional_context`、`returned_counts` 和 `omitted_counts`（对应阶段执行成功时）。
- 并发调用不覆盖彼此的日志；日志写入失败保持现有 hook 的容错行为。
- 更新日志相关测试，不改变检索或上下文投递行为。

**参考**：[Codex prompt_hook.py](../../src/memu/hosts/codex/prompt_hook.py)、[Claude Code prompt_hook.py](../../src/memu/hosts/claude_code/prompt_hook.py)。历史记录：[#791](https://github.com/NevaMind-AI/memU/issues/791)。

<a id="task-002"></a>

## 002 · pi 的 hook 接入

类型：🔌 Host 集成｜难度：⭐⭐～⭐⭐⭐，按阶段拆分｜✅ 已完成

[#796](https://github.com/NevaMind-AI/memU/pull/796) 已合入：pi 扩展在用户输入时异步检索，在响应及检索续轮结束后启动后台记忆，复用共享工作区锁和 30 分钟冷却期。长输入通过当前 provider/model 提取查询，支持超时回退；CLI 提供扩展安装、验证和卸载入口。

已完成 Windows 真实宿主的检索投递、空闲续轮及记忆提交／回读验收。Linux/macOS 运行验收及最低支持的 pi 版本仍待确认；需要继续推进时，先在 #790 明确范围和验收要求。共享提取进程的取消问题单列为 [任务 005](#task-005)。

**参考**：[pi 适配器](../../src/memu/hosts/pi)、[ADR 0021](../adr/0021-pi-extension-hooks.md)。历史方案讨论：[#792](https://github.com/NevaMind-AI/memU/issues/792)。

<a id="task-003"></a>

## 003 · Claude Code 遗留系统定时任务的检查与移除

类型：🛠️ 工程改进｜难度：⭐⭐／平台｜三个平台可分别认领、分别提交 PR

**背景与范围**

Claude Code 已接入自动检索和后台记忆 hook，但旧版安装可能仍保留操作系统中的定时 bridge。需要通过 `memu-cli` 提供的 Claude Code 命令入口，检查并移除旧注册，避免重复处理记忆。先核实历史注册方式和当前命令覆盖情况，再做各平台可独立验收的改动。

| 子任务 | 难度 | 开放状态 |
| --- | --- | --- |
| [003 / Windows](#task-003-windows) | ⭐⭐ | 🙋 开放认领 |
| [003 / Linux](#task-003-linux) | ⭐⭐ | 🙋 开放认领 |
| [003 / macOS](#task-003-macos) | ⭐⭐ | 🙋 开放认领 |

<a id="task-003-windows"></a>

### 🪟 Windows

- 核对 `\memU\` 下的已知任务与历史名称，读取任务动作、执行账户和注册位置。
- 验证普通用户任务，以及需要额外权限才能查看或移除的系统级任务；权限不足时给出准确诊断。
- 复用已有 Windows scheduler helper，补齐 Claude Code 命令入口，并在真实 Windows 环境完成检查、移除和回读验证。

<a id="task-003-linux"></a>

### 🐧 Linux

- 核对当前用户 crontab，以及历史安装实际使用的系统级 cron 位置。
- 调查是否存在 memU 的 systemd timer/service 注册；若存在，分别验证 user 和 system 范围。先确认历史注册方式，再补齐实际需要支持的位置。
- 在真实 Linux 环境完成检查、移除和回读验证，记录权限边界。

<a id="task-003-macos"></a>

### 🍎 macOS

- 核对用户 LaunchAgents、系统级 LaunchAgents / LaunchDaemons，以及历史安装实际使用的 crontab。
- 读取 plist 的 label、程序参数和所属 launchd domain，确认登记是否属于 Claude Code 的 memU bridge。
- 在真实 macOS 环境验证正确 domain 下的卸载与配置移除；权限不足时给出准确诊断。

### 待验证的现有 CLI 缺口

`memu-claude-code schedule uninstall` 当前委托旧的共享 Windows helper。
模拟注销报错时仍返回成功，并删除本地 wrapper、prompt 和注册记录；
检查流程也会把查询失败视作任务不存在。需要改为明确失败，保留重试所需文件，
核对任务动作归属，并在删除后验证不存在。
PR #802 的 Hermes Windows 清理提供独立的已验证路径；Claude Code 接入该路径，
并验证自己的历史注册，属于本任务范围。Linux/macOS 的检查与移除仍按平台分别推进。

当前验收状态仅针对旧调度注册的 CLI 检查、移除与读回验证：

| Host | Windows | Linux | macOS |
| --- | --- | --- | --- |
| Claude Code | 已复现上述缺陷，尚未修复并通过验收 | 未验收 | 未验收 |
| Hermes | 已验收 Windows Task Scheduler 清理，包括历史注册、归属核对、删除读回和失败传播 | 未验收 | 未验收 |

Hermes native cron 的自动迁移清理也尚未验收，不属于 Windows Task Scheduler
的已验收范围。Hermes 的记录仅作对照，不扩展本任务的 Claude Code 实现范围。

### 每个平台的验收标准

- 提供可执行的检查与定向移除命令，优先沿用现有 `memu-claude-code schedule` 接缝，具体命令形式可在认领时讨论。
- 区分未注册、已注册、无法检查和移除失败；不能把权限错误报告成“没有任务”或“已移除”。
- 核对名称、动作或注册配置，只移除确认属于 Claude Code memU bridge 的注册；归属不明确时保留并提示。
- 移除后重新检查确认结果；重复移除是安全的。
- 保留其他软件及其他 host 的定时任务、现有 hook、共享配置和记忆数据。
- 测试覆盖历史名称、并存注册、无关任务保留及权限不足；提供真实平台的验证记录，注明系统版本、注册范围和使用权限。
- 更新相应 CLI 帮助与安装／卸载说明。

**历史记录**：[#793](https://github.com/NevaMind-AI/memU/issues/793)。

<a id="task-004"></a>

## 004 · Codex / Claude skill 移除的文件归属保护

类型：🛠️ 工程改进／文件保护｜难度：⭐⭐｜开放认领

**背景与范围**

两者的 `remove-instruction` 命令共用 [instruction.py](../../src/memu/hosts/instruction.py)。当前 `remove_skill()` 只检查 `skills/memu-retrieve/SKILL.md` 是否存在，就用 `shutil.rmtree()` 删除整个目录；用户编辑过的 skill 和额外文件也会一起删除。

正式 `install` 已通过 `installation.check_cleanup()` 检查 skill 内容、额外文件和链接，但直接运行 `remove-instruction` 会绕过检查。全局指令文件的标记块移除与 skill 目录删除需要分别审查。

- 梳理共享 skill 删除函数的全部调用入口，复用已有归属检查，在实际删除前统一验证。
- 对用户修改过的 `SKILL.md`、额外文件或子目录，以及符号链接等情况保留原文件并给出诊断；不能只凭路径、文件存在或命令字符串判断整个目录归属。
- 保持确认归属的完整 memU skill 可移除，重复执行及目标不存在时安全，`--dry-run` 只读。
- 审查指令块与 skill 的操作顺序，避免检查失败前先移除部分内容；保留无关指令、配置和记忆。

**隔离复现**

在临时目录创建以下文件，两个 host 每次使用独立目录；请勿用真实用户目录复现：

```text
sandbox/
  rules.md                         # 用户自己的指令
  skills/memu-retrieve/
    SKILL.md                       # 完全由用户编写的内容
    notes.txt                      # 用户的额外文件
```

将 `<sandbox>` 替换为临时目录的绝对路径，分别执行：

```sh
memu-codex remove-instruction --path <sandbox>/rules.md --skills-dir <sandbox>/skills
memu-claude-code remove-instruction --path <sandbox>/rules.md --skills-dir <sandbox>/skills
```

已复现两个命令均返回成功，`rules.md` 保留，但 `memu-retrieve/` 及其中两个用户文件被删除。

**验收标准**

- 两个直接命令入口都能保护用户编辑的 skill 和额外文件。
- 覆盖确认归属的正常删除、目标不存在、重复删除、用户编辑、额外文件／子目录、链接和 `--dry-run`；链接测试注明平台权限条件。
- 保护检查失败时返回明确诊断，且指令文件和 skill 保持原样。
- 回归验证 Codex / Claude 安装中的迁移清理，更新必要的 CLI 帮助或说明。

**历史记录**：[#799](https://github.com/NevaMind-AI/memU/issues/799)。

<a id="task-005"></a>

## 005 · query-extract 取消与父进程退出时的进程树清理

类型：🛠️ 工程改进／子进程生命周期｜难度：⭐⭐⭐｜开放认领，先讨论方案

**背景与范围**

三个 host 共用 [query_extraction.py](../../src/memu/hosts/query_extraction.py) 的 `run_extraction()`。正常运行时，它在 12 秒超时后清理提取进程树并回退检索。若 hook 的 Python 父进程被外部终止，负责超时和清理的代码也退出，提取子进程可能继续运行。

POSIX 下提取进程使用独立 session/process group；Windows 下也需要验证启动脚本及后代的清理范围。残留请求可能继续消耗模型资源，挂起进程可能长期存活。

- 梳理启动、取消和终止的完整进程关系，区分正常提取超时、会话切换、关闭、reload，以及父进程异常退出。
- 设计可复用的清理机制，覆盖当前任务所属的子进程及后代；说明正常终止与强制终止各自的保证范围，避免误杀其他会话或用户进程。
- 保留共享提取策略、12 秒超时、失败回退和非阻塞输入；确保取消不会触发回退检索、投递旧结果或重新启动工作。
- 实现前在 #790 简述 Windows 与 POSIX 的处理方案；必要时开独立 RFC，并拆成可独立审查的小改动。

**已有证据与待验证项**

- **pi 已确认有触发路径**：`retrieval-extension.ts` 的 `session_shutdown` 对检索 Python 调用 `child.kill()`，未覆盖共享执行器启动的提取进程。
- **Windows 隔离复现成功**：Python 父进程调用 `run_extraction()` 启动写入 PID 后休眠的模拟提取程序；终止父进程后，提取子进程仍存活。复现后已定向清理测试进程。
- **Codex / Claude 的真实退出行为待测**：两者使用相同执行器，但 hook 由宿主管理；需要核实宿主是否清理整个进程树，不能仅凭共享代码声称正常切换或退出一定残留。

**验收标准**

- 使用本地模拟程序完成可重复测试，无需模型凭据或写入真实记忆；覆盖直接子进程和多级后代。
- 覆盖提取成功、提取超时、提取进行中取消／父进程退出，以及重复取消；目标进程最终退出，无关进程继续存活。
- pi 的关闭、切换会话和 reload 有验证记录；Codex / Claude 分别记录实际宿主行为及版本。
- Windows 与 POSIX 各有运行验证，注明信号、权限及无法覆盖的强制终止边界；缺少某平台验证时明确记录。
- 取消后无旧会话结果注入，正常超时回退仍通过现有回归测试。

**历史记录**：[#800](https://github.com/NevaMind-AI/memU/issues/800)。相关实现：[#796](https://github.com/NevaMind-AI/memU/pull/796)。

<a id="task-006"></a>

## 006 · 独立用户文档网站 memU-docs

类型：📚 文档建设｜难度：⭐⭐｜📝 待拆分，暂未开放认领

方向是建设独立的用户文档网站，便于用户找到安装、使用及问题排查说明。具体仓库、发布方式、内容范围和验收标准需要先在 #790 讨论，再开放可独立完成的子任务。

<a id="task-007"></a>

## 007 · 已安装 host 的统一检查与 hook 更新

类型：🛠️ 工程改进｜难度：⭐⭐⭐｜📝 待拆分，暂未开放认领

方向是为已安装 host 提供统一检查和 hook 更新流程。先在 #790 讨论各 host 的检测能力、更新边界和保护要求，形成明确验收标准后再拆分开放认领。
