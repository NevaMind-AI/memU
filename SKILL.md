---
name: install-memu
description: Install or uninstall memU for whatever agent you are — identify your host, print its packaged guide, and follow it to wire (or unwire) both seams (record and inject). Use when the user asks to install, set up, integrate, remove, or uninstall memU.
---

# Install memU

> **Audience: the agent.** A user has pointed you at this file ("read SKILL.md
> and follow it to install memU"). This skill does not contain the install
> steps — it routes you to the right guide, which ships inside the memU package
> and is always in sync with the installed code. Do not install from memory or
> from blog posts; print the guide and follow it to the letter.

memU integrates with a host agent through two seams: **record** (a scheduled
bridging task mines your session log into durable memory) and **inject** (a
standing instruction in your instruction file makes you retrieve before
answering). Each supported host has its own adapter binary carrying its own
install guide. Your job here is three steps: install the package, pick your
binary, print and follow its guide.

## Step 1 — install the package

```
pip install memu-cli
```

This puts `memu` and every host-adapter binary on `PATH`. If `pip` is not the
right tool for this machine (managed Python, uv-only), use the equivalent —
what matters is that the binaries below resolve from a bare, non-interactive
shell.

## Step 2 — pick your host binary

Identify **which agent you are** (not which agents are installed — the one
executing this skill):

| You are | Your binary |
| --- | --- |
| Codex | `memu-codex` |
| Claude Code | `memu-claude-code` |
| Cursor (Agent/CLI) | `memu-cursor` |
| OpenClaw | `memu-openclaw` |
| Hermes Agent | `memu-hermes` |
| anything else | `memu-agent` |

Unsure, or not in the table? You are `memu-agent`. Run:

```
memu-agent detect
```

It probes this machine and reports, per agent, whether **memorization** works
(a recognizable session log exists) and whether **retrieval** works (an
instruction file exists to patch) — and it will redirect you to a dedicated
binary if your host turns out to have one.

## Step 3 — print your guide and follow it

```
<your-binary> docs install
```

Read what it prints, top to bottom, and follow it exactly. Every guide has the
same shape — configure the store once in `~/.memu/config.env`, register the
scheduled bridging task (record), patch your instruction file (inject) — and
every part ends with a **verify gate**; do not proceed past a failing one.

Two rules that hold for every host:

- **One store.** If `~/.memu/config.env` already exists (another agent on this
  machine is already integrated), reuse it as is. A second store would split
  the embedding space and both installs would silently retrieve nothing from
  each other.
- **Report the outcome.** When done, tell the user which seams are now active —
  memorization, retrieval, or both — and where (the session log being mined,
  the instruction file patched). For `memu-agent`, the detect report decides
  this; a retrieval-only integration is a valid outcome to report, not a
  failure to hide.

## Uninstall

Same routing, in reverse. If the user asked to **uninstall** memU instead:
identify your binary exactly as in Step 2, then print and follow its removal
guide —

```
<your-binary> docs uninstall
```

It unregisters the bridging task, removes the instruction block
(`<your-binary> remove-instruction` — never hand-edit it out), and — only with
the user's explicit say-so — deals with the data and the package. The store may
be shared with other agents on the machine and *is* the user's accumulated
memory: keeping it is the default, deleting it is their call.
