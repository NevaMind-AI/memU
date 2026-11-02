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
    "完成安装检查": "Completing installation checks",
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
    "旧检索指令清理失败。": "Legacy retrieval cleanup failed.",
    "旧检索 skill 含额外文件或链接，请由 Agent 确认归属后定向清理。": "The legacy retrieval skill contains extra files or links; ask an Agent to verify ownership and clean it up selectively.",
    "旧检索 skill 与内置版本不同，请由 Agent 检查编辑和归属后定向清理。": "The legacy retrieval skill differs from the packaged version; ask an Agent to inspect edits and ownership before selective cleanup.",
    "全局指令为链接，请先检查归属和目标。": "The global instruction file is a link; check its ownership and target first.",
    "旧检索 managed block 含未知编辑，请由 Agent 检查后定向清理。": "The legacy retrieval managed block has unknown edits; ask an Agent to inspect it before selective cleanup.",
    "如果你使用 Codex Desktop，且以前自行安装过 memU 定时任务，现在可以自行暂停或移除它们，避免重复处理记忆。": "If you use Codex Desktop and previously set up memU scheduled tasks yourself, you can now pause or remove them to avoid processing memory twice.",
    "是否使用官方安装器补装 Codex？[y/N] ": "Install missing Codex using the official installer? [y/N] ",
    "Codex CLI 准备失败。": "Codex CLI preparation failed.",
    "工作目录有活跃 worker 或安装进程，请等待其结束后重试。": "A worker or installer holds the state directory lock; wait for it to finish and retry.",
    "请检查本地诊断并重新运行安装。": "Check the local diagnostics and run the installer again.",
}


def text(message: str, **values: str) -> str:
    """Translate installer messages without altering protocol status values."""
    translated = _EN.get(message, message) if LANGUAGE.get() == "en" else message
    return translated.format(**values) if values else translated
