---
name: install-memu
description: Install or uninstall memU for whatever agent you are — identify your host, print its packaged guide, and follow it to wire (or unwire) both seams (record and inject). Use when the user asks to install, set up, integrate, remove, or uninstall memU.
---

# Install memU

This skill routes you to your host's installation or removal guide. The host
guide owns permissions, configuration, progress messages, migration, verification
and the final report. Follow that guide rather than installing from memory.

## 1. Pick your host

Identify the agent executing this request, not which agents are installed:

| You are | Your binary |
| --- | --- |
| Codex | `memu-codex` |
| Claude Code | `memu-claude-code` |
| Cursor (Agent/CLI) | `memu-cursor` |
| OpenClaw | `memu-openclaw` |
| Hermes Agent | `memu-hermes` |
| WorkBuddy | `memu-workbuddy` |
| Cola | `memu-cola` |
| pi | `memu-pi` |
| Anything else | `memu-agent` |

For an unknown host, use `memu-agent detect` once the package is available.

## 2. Read your guide

If the user supplies a local installation guide, read it directly before making
installation changes. Otherwise, if your host binary is already available, run:

```text
<your-binary> docs install
```

If the package is missing, read `src/memu/hosts/<host>/INSTALL.md` from this
checkout when available. Otherwise install the package to obtain the guide:

```sh
pip install --upgrade memu-cli
```

Respect the user's package manager and source. For uv tool installations, use
`uv tool install --upgrade memu-cli`, or the local checkout the user specifies.
Use the user's explicit executable path for subsequent host commands.

## 3. Follow the guide

Read the guide once and follow its setup, migration and verification steps.
Reuse existing memory configuration and preserve the user's memories. Report
completion or a concrete blocker as the host guide directs.

## Uninstall

Select the same host binary and read its removal guide:

```text
<your-binary> docs uninstall
```

Follow its ownership checks, cleanup, data-retention defaults and final report.
If the user supplies a local removal guide, read that file directly instead.
