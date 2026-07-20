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

This removes only the memU **package** (the binaries). The store and
`~/.memu/config.env` live under `~/.memu/` and are **not** touched, so the
user's memories and settings carry straight over — Step 4 reuses the existing
`config.env` instead of asking again. (If this newer build needs a config value
the old file lacks, Step 4's `doctor` gate names exactly what to add.)

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
`Building memu-cli @ git+…@<sha>`. Note that SHA; you confirm it to the user in
Step 3, before the setup.

## Step 3 — verify, then confirm the version with the user

From a **fresh** shell (not the one that ran the installer, whose `PATH` may be
stale):

```
memu --help
memu-<your-host> --help    # e.g. memu-claude-code, memu-codex
```

Both must print usage. If they do not, the install's bin directory is not on
`PATH` (with uv it is `~/.local/bin`) — fix that before continuing, since the
scheduled task depends on the same resolution.

Then confirm the version with the user — **before the setup below**, since setup
is the long part and a wrong or stale build is painful to discover afterward. A
bare SHA is hard to judge, so report what the commit actually **is**:

- the SHA (from Step 2),
- its **subject line and date**, and
- the link to inspect it: `https://github.com/NevaMind-AI/memU/commit/<sha>`.

Fetch the subject and date from the GitHub API — no clone needed:

```
curl -s https://api.github.com/repos/NevaMind-AI/memU/commits/<sha>
```

read `.commit.message` (first line) and `.commit.author.date`. Then let the user
choose:

- **Yes, use this version** → continue straight into Step 4 and run it to
  completion **yourself**; do not make the user run `docs install` or any setup
  command. Pause again only if you genuinely need them (e.g. an embedding API
  key).
- **A specific commit instead** → reinstall that one (Step 2 with `@<sha>`), then
  confirm again here.

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
verify gate. When done, report which seams (memorization / retrieval) are now
active.
