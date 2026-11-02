"""Installer-owned messages; child commands retain their original diagnostics."""

# Chinese source messages use Chinese punctuation.
# ruff: noqa: RUF001

from contextvars import ContextVar

LANGUAGE: ContextVar[str] = ContextVar("codex_install_language", default="en")

_EN = {
    "检查安装条件": "Checking installation conditions",
    "准备 memU 与记忆后端": "Preparing memU and the memory backend",
    "准备 Codex CLI": "Preparing Codex CLI",
    "配置自动记忆与检索": "Configuring automatic memory and retrieval",
    "完成交接与安装检查": "Completing handoff and installation checks",
    "需要 Desktop Agent 提供 --migration-evidence；或确认是新装后使用 --new-install。": "A Desktop Agent must supply --migration-evidence, or confirm a new installation with --new-install.",
    "迁移证据必须是 version=1、source=desktop 的 JSON 对象。": "Migration evidence must be a JSON object with version=1 and source=desktop.",
    "Desktop 任务清单尚未确认完整。": "The Desktop task inventory has not been confirmed complete.",
    "Desktop 任务清单缺少本地回读证据。": "The Desktop task inventory needs a local read-back evidence file.",
    "迁移任务缺少 ID。": "A migration task is missing its ID.",
    "任务归属尚未确认；请由 Desktop Agent 核实清单。": "Task ownership is unconfirmed; ask a Desktop Agent to verify the inventory.",
    "Desktop 任务尚未确认 {field}：{id}": "Desktop task {id} has not been confirmed {field}.",
    "Desktop 任务缺少本地证据文件：{field}": "A Desktop task is missing its local evidence file: {field}.",
    "迁移清单包含重复任务 ID。": "The migration inventory contains duplicate task IDs.",
    "迁移任务清单已改变，请恢复原清单或使用独立工作目录重新检查。": "The migration task inventory changed; restore the original or check again in a separate state directory.",
    "迁移任务定义备份已改变，请保留原始定义。": "A saved task definition changed; preserve the original definition.",
    "后端尚未配置；使用 --backend cloud 或 --backend local 提供配置。": "The backend is not configured; supply --backend cloud or --backend local and its settings.",
    "记忆后端 [cloud/local]：": "Memory backend [cloud/local]: ",
    "请选择 cloud 或 local。": "Choose cloud or local.",
    "提供后端配置时需明确 --backend cloud 或 local。": "Specify --backend cloud or local when supplying backend settings.",
    "后端配置未通过保护检查；已有配置保留，请检查 config 诊断。": "Backend configuration was refused; existing settings are preserved. Check the config diagnostics.",
    "后端 doctor 未通过，请修复连接或配置后重跑。": "Backend doctor failed; repair connectivity or configuration and retry.",
    "Cloud 后端需要 --cloud-api-key 或已有配置。": "The Cloud backend needs --cloud-api-key or an existing configured key.",
    "memU Cloud API key：": "memU Cloud API key: ",
    "本地数据库路径 [~/.memu/memu.sqlite3]：": "Local database path [~/.memu/memu.sqlite3]: ",
    "Embedding provider [openai]：": "Embedding provider [openai]: ",
    "Embedding model [provider 默认]：": "Embedding model [provider default]: ",
    "Embedding endpoint [provider 默认]：": "Embedding endpoint [provider default]: ",
    "Embedding API key（本地服务可使用占位值）：": "Embedding API key (local services may use a placeholder): ",
    "本地后端需要 --db 指定持久化存储。": "The local backend needs --db to specify persistent storage.",
    "hook 配置为符号链接，请先检查其归属和目标。": "The hook configuration is a symlink; check its ownership and target first.",
    "~/.codex/hooks.json 格式无效；请先修复，安装器不会覆盖。": "~/.codex/hooks.json is invalid; repair it first. The installer will preserve it.",
    "发现本地自动化任务；请由 Desktop Agent 确认迁移清单。": "Local automations were found; ask a Desktop Agent to confirm the migration inventory.",
    "后端配置已改变，请重新执行第 2 和第 3 阶段。": "Backend configuration changed; repeat stages 2 and 3.",
    "Codex 程序状态发生变化，请重新运行程序准备阶段。": "The Codex executable state changed; repeat the executable preparation stage.",
    "工作目录已改变，请重新执行第 4 阶段。": "The working directory changed; repeat stage 4.",
    "请先完成第 4 阶段的双 hook 注册验证。": "Complete and verify both hook registrations in stage 4 first.",
    "hook 配置已改变，请重新执行第 4 阶段验证。": "Hook configuration changed; repeat stage 4 verification.",
    "后端配置已改变，请重新执行第 2 至 4 阶段。": "Backend configuration changed; repeat stages 2 through 4.",
    "已有工作状态发生变化；请检查 worker 和本地文件，保留现场后再继续。": "Existing processing files changed; inspect workers and local files, preserving the current state before continuing.",
    "旧检索指令清理预览失败。": "The legacy retrieval cleanup preview failed.",
    "旧检索指令清理失败。": "Legacy retrieval cleanup failed.",
    "旧检索 skill 含额外文件或链接，请由 Agent 确认归属后定向清理。": "The legacy retrieval skill contains extra files or links; ask an Agent to verify ownership and clean it up selectively.",
    "旧检索 skill 与内置版本不同，请由 Agent 检查编辑和归属后定向清理。": "The legacy retrieval skill differs from the packaged version; ask an Agent to inspect edits and ownership before selective cleanup.",
    "全局指令为链接，请先检查归属和目标。": "The global instruction file is a link; check its ownership and target first.",
    "旧检索 managed block 含未知编辑，请由 Agent 检查后定向清理。": "The legacy retrieval managed block has unknown edits; ask an Agent to inspect it before selective cleanup.",
    "Codex 返回 hook 加载诊断，请重新执行第 4 阶段。": "Codex reported hook loading diagnostics; repeat stage 4.",
    "memU hook 数量不正确，请重新执行第 4 阶段。": "The number of memU hooks is incorrect; repeat stage 4.",
    "Codex 未确认 memU hook 已加载且受信任。": "Codex did not confirm that the memU hook is loaded and trusted.",
    "Codex 未确认异步检索。": "Codex did not confirm asynchronous retrieval.",
    "请到 Codex Desktop 暂停旧 memU 定时任务，避免它与新的后台记忆同时运行；旧任务迁移交给 Desktop Agent 处理。": "Pause old memU scheduled tasks in Codex Desktop to avoid running alongside the new background memory process. A Desktop Agent can complete their migration.",
    "是否使用官方安装器补装 Codex？[y/N] ": "Install missing Codex using the official installer? [y/N] ",
    "Codex CLI 准备失败。": "Codex CLI preparation failed.",
    "安装状态文件无效，请保留现场并检查。": "The installation state file is invalid; preserve it for inspection.",
    "工作目录有活跃 worker 或安装进程，请等待其结束后重试。": "A worker or installer holds the state directory lock; wait for it to finish and retry.",
    "请先执行前置安装阶段。": "Complete the prerequisite installation stages first.",
    "请检查本地诊断并重跑当前阶段。": "Check the local diagnostics and retry the current stage.",
}


def text(message: str, **values: str) -> str:
    """Translate installer messages without altering protocol status values."""
    translated = _EN.get(message, message) if LANGUAGE.get() == "en" else message
    return translated.format(**values) if values else translated
