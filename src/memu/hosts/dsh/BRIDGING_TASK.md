---
name: {{task_doc_name}}
description: 注册一个定时 DSH 运行，把最近的会话桥接进 memU。
---

# 创建 memU 桥接任务（DSH）

## 任务身份

- 当前任务名：`{{task_name}}`
- 历史任务名：{{former_task_names}}
- 迁移与移除时会被识别的名字：{{all_task_names}}

DSH 适配器的 `schedule_backend` 是 `external`：它**不注册**任何操作系统级计划任务，
`memu-dsh schedule` 也不存在。桥接由外部调度器驱动，调度器只负责把下面这段提示词
交给一个 DSH 会话。默认节奏按小时一次，用户要求改再改。

## 桥接提示词

把下面这段文本**逐字**写入 `<memU 基目录>/bridge-prompt.txt`：

```text
运行 memU 桥接流水线。严格按顺序做四步，即使上一步看起来没产出也不要跳过。

1. 残留物：如果 <memU 基目录>/jobs/ 里已经有 job 文件，它们是上一次运行（崩溃或安装
   过程本身）留下的未完成工作——按第 3 步处理它们，然后运行 memu-dsh commit，
   之后才继续。
2. 准备：用 bash 运行 memu-dsh prepare——它会重新生成 <memU 基目录>/jobs/。
   命令以非零码退出就停下并报告错误。
3. 自我演化：列出 <memU 基目录>/jobs/*.txt，按数字升序逐个处理（1.txt、2.txt……）。
   每次运行的数量都不同，一律先 glob 再排序；没有 job 文件就跳到第 4 步。
   每个 job 文件都自成一体、自带它需要的具体路径，按它的指令逐字执行；
   某个 job 没有产出文件是合法结果，不要编造内容。
4. 提交：用 bash 运行 memu-dsh commit——它提交 job 新建或修改的内容。
   以非零码退出就报告错误。

失败处理：如果第 2 步或第 4 步以非零码退出，在停下之前运行一次
memu-dsh report error --stage remember --detail "<完整交代出了什么问题>"——
这段说明是 memU 工程师判断本机故障的唯一线索，请写足：哪一步、跑了什么、
实际发生了什么、已经试过什么、怀疑原因是什么。写给人看的散文，不要粘贴
traceback 或原始命令输出 (command output)（CLI 自己会报），也不要带
凭据 (credential)、绝对路径 (absolute path)、记忆或转录文本。
忽略该命令自身的失败，它永远不属于本次运行。

最后用一行总结：跑了几个 job（含残留物）、提交了什么。
```

`<memU 基目录>` 对 DSH 宿主是 `~/.memu/hosts/dsh`。

## 注册调度

两种方式，按用户环境选一种，不要同时装两套：

**A. 用 DSH 自己的定时器（推荐）** —— 让一个 DSH 会话按节奏执行上面的提示词。
DSH 装了 schedule 相关的 bundle 时用它的 `schedule_create` 工具（`every_seconds` 或
`cron`），提示词内容就是上面那段文本，任务名用 `{{task_name}}`。

**B. 操作系统级调度** —— 让调度器启动一个无头 DSH 会话：

```sh
dsh headless "$(cat ~/.memu/hosts/dsh/bridge-prompt.txt)"
```

Windows 用任务计划程序，任务名 `{{task_name}}`；macOS/Linux 用 launchd 或 crontab，
条目注释里带上 `{{task_name}}`，并把 `dsh` 与 `memu-dsh` 所在目录写进 `PATH` 行。

## 验证

先确认注册存在，再触发一次真实运行，并检查文件系统证据：`~/.dsh/memu/transcripts/`
下出现新的会话文件、`~/.memu/hosts/dsh/jobs/` 里出现 job、以及
`~/.memu/hosts/dsh/.session_manifest.dsh.json` 的时间戳前进。只信 agent 自己的总结
不算验证。

另外注意：由无人值守运行发起的 `prepare` 只有在环境里带了 `DSH_SESSION_ID` 时才能
把自己那次会话标记为 bridge 所有（否则下一轮会把它也挖进记忆）。需要这个语义时，
在调度器里把当前会话 id 导成 `DSH_SESSION_ID` 再调用 `memu-dsh prepare`。
