---
name: create-memu-bridging-task
description: Register a scheduled job that bridges recent Claude Code sessions into memU memory, skills, and resource submissions. Runs the prepare → self-evolve → commit pipeline on a schedule (default: every hour).
---

# Create the memU bridging scheduled task (Claude Code on Windows)

Use this when the user asks to set up or change the recurring memU bridging task:
the job that periodically turns recent Claude Code sessions into memU memory,
skills, and resource submissions.

Your goal is to register a recurring headless Claude Code run. You are not
running the pipeline now.

## Prerequisites

- **memU is installed and `memu-claude-code` is on `PATH`.** Verify with
  `memu-claude-code doctor`; if it fails, do `INSTALL.md` Part 1 first.
- **A standalone, headless-authenticated `claude` is on `PATH`.** The Desktop
  app cannot serve a scheduled run — its binary is off-`PATH` and its login is
  invisible to the CLI. `INSTALL.md` Part 2.0 is the install and
  bare-environment verify procedure; `schedule install` runs the same gate and
  refuses with guidance if it fails.
- **A headless run can execute the pipeline.** The scheduled run invokes
  `claude -p` non-interactively, so the commands and paths the pipeline touches
  must be pre-authorized in `~/.claude/settings.json` permissions with exactly
  these two rules: `Bash(memu-claude-code *)` and `Edit(~/.memu/**)`. The file
  rule must be `Edit(...)` — a `Write(~/.memu/**)` rule is silently ignored.
  Do not use a blanket permission-skip flag.

## Register and verify

Ask the user for a schedule if the request does not include one. The default is
every hour. Confirm before registering.

Do not hand-write a Task Scheduler entry. Run the helper instead:

```
memu-claude-code schedule install     # register the hourly task
memu-claude-code schedule verify      # prove it resolves + authenticates
memu-claude-code schedule status      # last run / next run
memu-claude-code schedule uninstall   # remove it
```

`install` writes the pipeline prompt to a file plus a small generated wrapper
that reads it, bakes in the absolute path to `claude`, and registers
`\memU\memu-bridging-claude-code` under an **S4U** principal. The task runs
whether or not the user is logged in, stays windowless, and catches up a missed
run. `--interval <minutes>` changes the cadence (default: 60).

Because the scheduled run needs a standalone, headless-authenticated `claude`,
`install` refuses with guidance if `claude` is not on `PATH` or cannot
authenticate without a browser. It is better to fail at install than register a
task that never runs.

> **The credential must be persistent.** The task runs headless under an S4U
> principal and inherits only persistent user or machine environment and the
> user profile — not a session-only `$env:` export. Either option from
> `INSTALL.md` Part 2.0 works: **Web auth** (recommended; `claude setup-token`,
> subscription) or an **Anthropic API key** persisted with `setx`. A token
> exported only in the install-time shell leaves the task stuck on "Not logged
> in".

After a scheduled run, confirm filesystem traces rather than trusting its
summary: `~/.memu/hosts/claude-code/jobs/` timestamps and the session cursor
must advance. The first run has work only after new Claude Code sessions exist.
