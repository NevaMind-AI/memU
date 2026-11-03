"""Installer-owned messages; child commands retain their original diagnostics."""

# Chinese source messages use Chinese punctuation.
# ruff: noqa: RUF001

from contextvars import ContextVar

LANGUAGE: ContextVar[str] = ContextVar("codex_install_language", default="en")

_EN = {
    "安装已取消": "Installation cancelled",
    "输入已结束，安装已停止。请在交互终端重新运行，或使用 --non-interactive 并提供所需参数。": "Input ended; installation stopped. Run in an interactive terminal, or use --non-interactive with the required options.",
    "   独立 Codex CLI：{path}": "   Standalone Codex CLI: {path}",
    "\n👋 欢迎安装 memU\n   为 Codex 配置自动检索和后台记忆。": "\n👋 Welcome to memU\n   Set up automatic retrieval and background memory for Codex.",
    "已完成": "Done",
    "安装暂时无法继续": "Installation needs your attention",
    "安装未完成": "Installation failed",
    "\n🎉 memU 安装完成！自动检索和后台记忆已就绪。": "\n🎉 memU is ready! Automatic retrieval and background memory are configured.",
    "   {mode} 后端连接正常": "   {mode} backend connection verified",
    "📥 正在下载官方 Codex 安装器：{url}": "📥 Downloading the official Codex installer: {url}",
    "📦 正在运行官方安装器，下载和安装可能需要几分钟……": "📦 Running the official installer; download and setup may take a few minutes…",
    "官方安装器下载失败：HTTP {code}。服务器拒绝了下载请求。": "Official installer download failed: HTTP {code}. The server refused the download request.",
    "无法连接官方安装器下载服务，请检查网络和代理设置。": "Cannot connect to the official installer download service. Check your network and proxy settings.",
    "Codex 命令等待超过 {seconds} 秒，已停止。": "The Codex command timed out after {seconds} seconds.",
    "官方安装器退出，错误码 {code}。请查看上方安装器输出。": "The official installer exited with code {code}. See its output above.",
    "可以在网络恢复后重新运行，或自行安装 Codex 后使用 --codex PATH 指定程序。": "Retry once connectivity is restored, or install Codex yourself and select it with --codex PATH.",
    "未找到 Codex CLI。添加 --install-missing 可使用官方安装器补装。": "Codex CLI was not found. Add --install-missing to use the official installer.",
    "官方安装器已退出，但仍未找到 Codex CLI。请检查安装器输出或使用 --codex PATH 指定程序。": "The official installer finished but Codex CLI was not found. Check its output or select the executable with --codex PATH.",
    "Codex CLI 启动检查失败，codex --version 未返回有效版本。请检查程序是否完整。": "Codex --version did not return a valid version. Check that the executable is intact.",
    "指定的 Codex 程序不存在，请检查 --codex 路径。": "The selected Codex executable does not exist. Check the --codex path.",
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
    "另一个安装进程正在运行，请稍后重新发起安装。": "Another installer is running; start installation again later.",
    "请检查本地诊断并重新运行安装。": "Check the local diagnostics and run the installer again.",
}


def text(message: str, **values: str) -> str:
    """Translate installer messages without altering protocol status values."""
    translated = _EN.get(message, message) if LANGUAGE.get() == "en" else message
    return translated.format(**values) if values else translated
