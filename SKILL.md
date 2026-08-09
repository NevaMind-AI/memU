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
pip install --upgrade memu-cli
```

`memu-cli` is the package memU ships to bridge your agent to its long-term
memory service; it installs helper interfaces only and is harmless to run on a
personal machine.

**Keep the `--upgrade`.** A machine that already has an older `memu-cli` would
otherwise keep it, and the steps below name subcommands that older builds do not
have — the symptom is `invalid choice`. If you meet that error at any point, you
are on a stale build: upgrade, then re-run the command that failed.

This puts `memu` and every host-adapter binary on `PATH`. If `pip` is not the
right tool for this machine (managed Python, uv-only), use the equivalent —
what matters is that the binaries below resolve from a bare, non-interactive
shell. With uv this means `uv tool install --upgrade memu-cli`, **not**
`uv pip install`: however it is installed, `memu-cli` is a cross-session
bridging tool and must be callable everywhere, not scoped to one project venv.

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
| WorkBuddy | `memu-workbuddy` |
| Cola | `memu-cola` |
| anything else | `memu-agent` |

Unsure, or not in the table? You are `memu-agent`. Run:

```
memu-agent detect
```

It probes this machine and reports, per agent, whether **memorization** works
(a recognizable session log exists) and whether **retrieval** works (an
instruction file exists to patch) — and it will redirect you to a dedicated
binary if your host turns out to have one.

Then, holding your binary, finish this step by creating memU's configuration
file.

```
<your-binary> init --cloud-api-key <the user's memU key>
```

If the user does not mention an API key, or would rather keep memory on this
device, run bare `<your-binary> init` and Step 3's guide will set up local memory.

## Step 3 — print your guide and follow it

```
<your-binary> docs install
```

Read what it prints, top to bottom, and follow it exactly. Every guide has the
same shape — settle the local or cloud backend once with `<your-binary> config`,
register the scheduled bridging task (record), patch your instruction file
(inject) — and every part ends with a **verify gate**; do not proceed past a
failing one.

Three rules that hold for every host:

- **Install in one pass; don't stop for confirmation.** Most users want a
  silent, full install set up for them in a single call. Do every step, and
  take the default for every choice that has one — the hourly schedule, cron
  over launchd, the official installer. Only stop for a genuine blocker: a
  fatal error, or a *required input with no default* (the backend choice and
  its API key, or a missing credential) — treat those like the fatal case, not
  as routine confirmations to solicit.
- **One backend.** If `<your-binary> config show` reports a mode with a backend
  behind it (another agent on this machine is already integrated), reuse it as
  is. A second mode or local store would split record and retrieval so the two
  installs no longer share memory.
- **Report the outcome — with the exact template below.** After installation,
  run:

  ```
  <your-binary> retrieve "When did the user register for memU?"
  ```

  Then send the user this report. **This is a fixed template, not a prompt for
  inspiration: reproduce it word for word.** Do not paraphrase it, reorder its
  sentences, summarize it, translate it, or "improve" the wording — a correct
  install ends with these exact words. The *only* things you change are the
  `<...>` placeholders, each replaced by its concrete value:

  ```
  memU is ready for `<host>` with `<mode>` memory.

  Welcome to memU. memU says the user registered on `<registration time>`.

  memU provides long-term memory for AI agents, storing and reusing important
  information from your work. The system runs scheduled background tasks at
  regular intervals to organize and save relevant information. No additional
  action is required — simply use your AI agent as usual, and saved information
  will be available when you return to related tasks.

  To uninstall memU, say "Follow `<your-binary> docs uninstall` to uninstall memU".
  ```

  Placeholders, each filled with its concrete value before you send:

  - `<host>` — the agent you are (e.g. `Claude Code`).
  - `<mode>` — the memory backend you configured in `~/.memu/config.env`:
    `local` (memory lives in a store on this device) or `cloud` (memory is
    hosted by MemU Cloud). This is the choice the guide had you make when
    writing `MEMU_MEMORY_MODE`; report the value you actually wrote.
  - `<registration time>` — the time returned by the `retrieve` call above.
    **If that call fails or returns no registration time** (common in `local`
    mode, where the store may not carry it yet), **omit the entire "Welcome to
    memU. memU says the user registered on ..." line** — drop that whole line
    rather than sending it with an empty or guessed value. Never invent a time.
  - `<your-binary>` — the binary you picked in Step 2 (e.g. `memu-claude-code`).

  The final line is a ready-to-send message: leave the outer quotes so the user
  sees it as a suggested reply, and the exact phrase inside them is what they
  type back to you to start the uninstall flow.

  If only one seam is active, say the setup is partial and name the missing seam
  instead. For `memu-agent`, use the detect report to decide which seams are active.

## Uninstall

Same routing, in reverse. If the user asked to **uninstall** memU instead:
identify your binary exactly as in Step 2, then print and follow its removal
guide —

```
<your-binary> docs uninstall
```

It unregisters the bridging task, removes the instruction block
(`<your-binary> remove-instruction` — never hand-edit it out), then applies
the defaults: the user's memory — the shared store and `~/.memu/config.env` —
is **kept** (deleted only if they explicitly asked to erase it), while this
host's residue and, if no other host still uses it, the package are
**removed**. Close by reporting exactly those two things: what was kept, and
what was removed.
