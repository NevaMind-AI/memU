# 宿主接入

宿主适配器将桌面或编程 Agent 连接到共享记忆后端。按宿主选择命令：

| 宿主 | 命令 |
| --- | --- |
| Codex | `memu-codex` |
| Claude Code | `memu-claude-code` |
| Cursor | `memu-cursor` |
| OpenClaw | `memu-openclaw` |
| Hermes | `memu-hermes` |
| WorkBuddy | `memu-workbuddy` |
| pi | `memu-pi` |

想让自己常用的 Coding Agent 也用上 memU？欢迎贡献新的宿主适配器，PR is welcome！开始前可以参考[贡献指南](https://github.com/XnneHangLab-Mirror/memU/blob/main/CONTRIBUTING.md)。

## 从 Cola 或 generic 升级

Cola、generic 适配器及 `memu-cola` / `memu-agent` 命令已移除。升级前，用旧版安装打印对应的 `memu-cola docs uninstall` 或 `memu-agent docs uninstall` 指南并执行。只移除确认归属该集成的调度、检索指令和技能；保留用户编辑、共享记忆、配置及其他宿主需要的工具。包升级不会自动清理这些集成，遗留任务和指令会调用已不存在的命令。如果已经升级，请先恢复之前的包版本完成清理。

## 安装与卸载

Codex、Claude Code、pi 和 Hermes 直接运行对应命令：

| 宿主 | 安装 | 卸载 |
| --- | --- | --- |
| Codex | `memu-codex install` | `memu-codex uninstall` |
| Claude Code | `memu-claude-code install` | `memu-claude-code uninstall` |
| pi | `memu-pi install` | `memu-pi uninstall` |
| Hermes | `memu-hermes install` | `memu-hermes uninstall` |

安装器处理后端配置和宿主接入；卸载保留配置和记忆。按终端提示完成操作。

其他宿主由 Agent 按指南完成安装，例如 Cursor：

```sh
memu-cursor docs install
memu-cursor docs uninstall
```

`docs install` / `docs uninstall` 只打印操作指南，不会执行安装或卸载。让 Agent 读取并执行指南中的步骤；是否需要定时任务也以指南为准。

## 检索入口清理保证 {#retrieval-cleanup}

Codex、Claude Code、pi 的卸载命令会清理当前 hook/扩展，以及宿主默认位置可确认归属的检索指令和 SKILL。pi 同时检查 `AGENTS.md` 与 `AGENTS.override.md`。请使用安装时相同的宿主 home/profile。自定义历史位置可先用 `remove-instruction --path <file> --skills-dir <dir> --dry-run` 预览，核验后再实际执行。

SKILL 安装和刷新会在 `SKILL.md` 旁写入 `.memu-owned.json`，记录宿主与已安装文本的指纹。只要文件未被修改，包或服务端模板变化后仍可清理，无需逐版本迁移。用户编辑、额外文件、链接或无效归属记录会让清理停止并给出诊断。没有记录的老 SKILL 只有在匹配包内内容时才自动删除；其他历史副本需要核验归属。不要直接删除归属不明的目录来绕过检查。

历史定时任务仍须按 `docs uninstall` 检查。单条命令不会枚举所有 OS/原生调度器，也不会发现所有项目/profile。在宣布完整卸载前，应报告未解决的入口。记忆库、共享配置和无关集成会被保留。重开会话（pi 也可 `/reload`），以卸载已经加载的指令或扩展。

## Hook 与激活

Codex 和 Claude Code 安装器配置检索与后台记忆 hook。pi 使用扩展：提交输入时异步检索，响应和待处理检索结束后执行后台记忆。pi worker 共享工作区锁和 30 分钟冷却期。长查询通过当前 provider/model 提取，12 秒超时后回退到原始前缀。

宿主可能使用模型整理记忆或提取查询。`MemoryService` 本身仍仅调用 Embedding。

安装 pi 后运行 `/reload` 或开启新会话；安装 Claude Code hook 后开启新会话。分别验证本地注册和宿主实际执行。

其他宿主按对应安装指南配置写入与检索。能力随宿主、系统和版本变化；已记录的平台限制见[仓库支持矩阵](https://github.com/XnneHangLab-Mirror/memU/blob/main/README.md#agent-support)。

## 手动检索

```sh
memu-pi retrieve "我们对这个仓库知道些什么？"
```

宿主输出最多五条自包含的 `hits`，以及独立的 `resources`。命中项组合匹配正文、来源信息和本地镜像路径或内联内容。面向 Agent 的结果省略数据库 ID 和 scope 元数据。

后端检查通过但 Agent 没有收到上下文时，参阅[故障排查](../troubleshooting/index.md)。
