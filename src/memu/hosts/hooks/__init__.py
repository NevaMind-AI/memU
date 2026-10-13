"""Hook-triggered bridging: the record seam without a scheduler (ADR 0019).

A scheduled bridging run is a host agent session, so ``prepare`` and ``commit``
run inside that agent's sandbox — and both need the network (the store mirror,
embeddings, memU Cloud). Codex's scheduled tasks deny it outright; ``claude -p``
needs it pre-authorized. Hook mode moves every network step out of the agent:

    host hook (SessionEnd / notify)  ->  memu-<host> hook          returns at once
        detached                     ->  memu-<host> hook-run      outside any sandbox
                                            prepare                network
                                            headless agent         local files only
                                            commit                 network

The agent keeps the judgement work — reading transcripts, writing markdown — and
nothing else; it no longer runs a memU command that talks to a server.
"""

from memu.hosts.hooks.installers import ClaudeSettingsHook, CodexNotifyHook, HookInstaller
from memu.hosts.hooks.runner import HeadlessAgent, HeadlessAgentError, HookSpec, codex_thread_id

__all__ = [
    "ClaudeSettingsHook",
    "CodexNotifyHook",
    "HeadlessAgent",
    "HeadlessAgentError",
    "HookInstaller",
    "HookSpec",
    "codex_thread_id",
]
