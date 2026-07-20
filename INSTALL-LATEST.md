---
name: install-memu-latest
description: Install the latest development build of memU-cli from git (main HEAD). Use when the user wants the newest unreleased code — clean any old install, install from git, verify, then set up.
---

# Install the latest (development) memU

> **Audience: the agent.** A user pointed you here ("read this and install the
> latest memU"). Do the install yourself — the user should not run commands by
> hand. This installs memU-cli from **git `main`**, the latest source.

## Step 1 — remove any existing memU install

An older memU already on the machine can stay on `PATH` and **shadow the one you
are about to install**, so the version that actually runs would not be the
latest. Remove it first — try each installer, ignore "not installed":

```
uv tool uninstall memu-cli
pipx uninstall memu-cli
pip uninstall -y memu-cli
```

**Tell the user what you removed** — the name and version, or "no previous
install found" — so they know their old version is gone before you continue.

## Step 2 — install from git, persistently

The install **must persist on `PATH`**: the scheduled bridging task will call
these binaries later from a bare, non-interactive shell. So install as a durable
tool — **never** with an ephemeral runner (`uvx`, `npx`), which vanish after one
command and leave nothing for the task to find.

Requirement: `git` on `PATH`. Then take the first option that fits the machine:

- **uv (preferred — isolated, global, on `PATH`):**
  ```
  uv tool install "git+https://github.com/NevaMind-AI/memU"
  ```
- **no uv, but you can install it:** install uv, then run the command above.
  ```
  curl -LsSf https://astral.sh/uv/install.sh | sh                 # macOS / Linux
  powershell -c "irm https://astral.sh/uv/install.ps1 | iex"      # Windows
  ```
- **pip fallback (only into a stable, on-`PATH` environment):**
  ```
  pip install "git+https://github.com/NevaMind-AI/memU"
  ```

To pin an exact commit instead of the moving `main`, append `@<sha>` to the URL.

The installer prints the exact commit it resolved — with uv, a line like
`Building memu-cli @ git+…@<sha>`. Note that SHA; you confirm it to the user at
the end.

## Step 3 — verify it resolves

From a **fresh** shell (not the one that ran the installer, whose `PATH` may be
stale):

```
memu --help
memu-<your-host> --help    # e.g. memu-claude-code, memu-codex
```

Both must print usage. If they do not, the install's bin directory is not on
`PATH` (with uv it is `~/.local/bin`) — fix that before continuing, since the
scheduled task depends on the same resolution.

## Step 4 — set up memU

You now have the latest binaries. Identify **which agent you are** and use its
binary — memU has seven host adapters:

| You are | Your binary |
| --- | --- |
| Codex | `memu-codex` |
| Claude Code | `memu-claude-code` |
| Cursor | `memu-cursor` |
| OpenClaw | `memu-openclaw` |
| Hermes | `memu-hermes` |
| WorkBuddy | `memu-workbuddy` |
| anything else | `memu-agent` — run `memu-agent detect` if unsure |

Then print your host's packaged guide and follow it to the letter:

```
memu-<your-host> docs install
```

It walks you through configuring the store in `~/.memu/config.env`, registering
the scheduled bridging task, and patching your instruction file, each behind a
verify gate. When done, report to the user **which seams (memorization /
retrieval) are now active, and the exact commit you installed** (the SHA from
Step 2) — so they can confirm which HEAD is on the machine.
