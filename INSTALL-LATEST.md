---
name: install-memu-latest
description: Install the latest development build of memU-cli from git (main HEAD) instead of the published PyPI release. Use when the user needs a merged-but-unpublished fix, then continue the normal setup in SKILL.md.
---

# Install the latest (development) memU

> **Audience: the agent.** A user pointed you here ("read this and install the
> latest memU"). Do the install yourself — the user should not run commands by
> hand. This installs memU-cli from **git `main` (the latest source)**, not the
> published PyPI release. For a normal install, use the PyPI path in
> [SKILL.md](SKILL.md) instead.

memU-cli has two install sources. This doc is the second one:

| | PyPI release (default) | Latest HEAD (this doc) |
| --- | --- | --- |
| Source | published `memu-cli` on PyPI | git `main` |
| You get | the last published version | everything merged, incl. unreleased fixes |
| Stability | released | development — may change under you |
| Use when | normal setup ([SKILL.md](SKILL.md)) | you need a merged-but-unpublished fix |

## Step 1 — install from git, persistently

Two rules decide the method:

- **It must be from git `main`,** not PyPI — that is the whole point of this doc.
- **It must persist on `PATH`.** The scheduled bridging task calls these
  binaries later from a bare, non-interactive shell. So install as a durable
  tool — **never** with an ephemeral runner (`uvx`, `npx`): those vanish after
  one command and the scheduled run would find nothing.

Requirement: `git` must be on `PATH` (git installs need it). Then pick the first
option that fits the machine:

- **uv present (preferred — isolated, global, on `PATH`):**
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
  Do not install into a throwaway virtualenv — the binaries must still resolve
  at task time.

To pin an exact commit instead of the moving `main`, append `@<sha>` (or
`@main`) to the URL.

## Step 2 — verify it resolves

From a **fresh** shell (not the one that ran the installer, whose `PATH` may be
stale):

```
memu --help
memu-<your-host> --help    # e.g. memu-claude-code, memu-codex
```

Both must print usage. If they do not, the install's bin directory is not on
`PATH` (with uv it is `~/.local/bin`). Fix that before continuing — the
scheduled task depends on the same resolution.

## Step 3 — continue the normal setup

You now have the latest binaries on `PATH`. Continue with the standard install
from **Step 2 of [SKILL.md](SKILL.md)** — identify your host binary, run
`<binary> docs install`, and follow that guide (configure the store, register
the bridging task, patch the instruction file, each behind its verify gate).
**Skip SKILL.md's Step 1** — you have already installed, and reinstalling from
PyPI there would overwrite this build with the older release.
