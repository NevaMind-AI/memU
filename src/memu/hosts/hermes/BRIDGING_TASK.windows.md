---
name: create-memu-bridging-task
description: Register a scheduled job that bridges recent Hermes sessions into memU memory, skills, and resource submissions. Runs the prepare → self-evolve → commit pipeline on a schedule (default: every hour).
---

# Create the memU bridging scheduled task (Hermes on Windows)

Use this when the user asks to set up or change the recurring memU bridging task:
the job that periodically turns recent Hermes sessions into memU memory, skills,
and resource submissions.

Your goal is to register a recurring headless Hermes run. You are not running
the pipeline now.

## Prerequisites

- **memU is installed and `memu-hermes` is on `PATH`.** Verify with
  `memu-hermes doctor`; if it fails, do `INSTALL.md` Part 1 first.
- Hermes ships its client and CLI together and uses one runtime and
  configuration; there is no separate CLI install or headless-auth step.

## Register and verify

Ask the user for a schedule if the request does not include one. The default is
every hour. Confirm before registering.

First migrate any install made by the older guide: run `hermes cron list --all`;
for every job whose name is exactly `memu-bridging-hermes`, run
`hermes cron remove <job-id>`, then list again and confirm none remain.
If listing or removal fails, stop — never add the OS task beside a native copy.

Do not hand-write a Task Scheduler entry. Run the helper instead:

```
memu-hermes schedule install     # register the hourly task
memu-hermes schedule verify      # prove a resolvable CLI
memu-hermes schedule status      # last run / next run
memu-hermes schedule uninstall   # remove it
```

`install` writes the pipeline prompt plus a small generated wrapper under
`~/.memu/hosts/hermes`, resolves the bundled `hermes` CLI to an absolute path,
and registers `\memU\memu-bridging-hermes` under an **S4U** principal. The task
runs whether or not the user is logged in, stays windowless, and catches up a
missed run. `--interval <minutes>` changes the cadence (default: 60).

After a scheduled run, confirm filesystem traces rather than trusting its
summary: `~/.memu/hosts/hermes/jobs/` timestamps and the session manifest must
advance. The first run has work only after new Hermes sessions exist.
