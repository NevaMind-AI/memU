"""Hook-triggered Codex record runs (ADR 0020).

The detached runner owns prepare and commit; the headless agent processes local
job instructions between them. The agent's permissions are declared by the host.
"""

from memu.hosts.hooks.installers import CodexNotifyHook, HookInstaller
from memu.hosts.hooks.runner import HeadlessAgent, HeadlessAgentError, HookSpec, codex_thread_id

__all__ = [
    "CodexNotifyHook",
    "HeadlessAgent",
    "HeadlessAgentError",
    "HookInstaller",
    "HookSpec",
    "codex_thread_id",
]
