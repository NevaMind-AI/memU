---
name: create-memu-bridging-task
description: Register a scheduled job that bridges recent Cursor agent sessions into memU memory, skills, and resource submissions. Runs the prepare → self-evolve → commit pipeline on a schedule (default: every hour).
---

# Create the memU bridging scheduled task (Cursor on Windows)

Use this when the user asks to set up or change the recurring memU bridging task:
the job that periodically turns recent Cursor agent sessions into memU memory,
skills, and resource submissions.

Your goal is to register a recurring headless Cursor Agent run. You are not
running the pipeline now.

## Prerequisites

- **memU is installed and `memu-cursor` is on `PATH`.** Verify with
  `memu-cursor doctor`; if it fails, do `INSTALL.md` Part 1 first.
- **`cursor-agent` runs headless.** The scheduled entry invokes
  `cursor-agent -p` non-interactively with permission to run `memu-cursor` and
  write under `~/.memu/`. The Cursor IDE does not provide this binary — it is a
  separate install; `INSTALL.md` Part 2.0 is the install and bare-environment
  verify procedure to pass first.

## Register and verify

Ask the user for a schedule if the request does not include one. The default is
every hour. Confirm before registering.

Do not hand-write a Task Scheduler entry. Run the helper instead:

```
memu-cursor schedule install     # register the hourly task
memu-cursor schedule verify      # prove it resolves + authenticates
memu-cursor schedule status      # last run / next run
memu-cursor schedule uninstall   # remove it
```

`install` writes the pipeline prompt to a file plus a small generated wrapper
that reads it, bakes in the absolute path to `cursor-agent`, and registers
`\memU\memu-bridging-cursor` under an **S4U** principal. The task runs whether
or not the user is logged in, stays windowless, and catches up a missed run.
`--interval <minutes>` changes the cadence (default: 60).

Cursor-specific facts, field-verified on Windows 11:

- **Run `schedule install` from a terminal opened after installing
  `cursor-agent`.** The installer updates the registry user `PATH`; a shell or
  IDE started earlier keeps its launch-time environment and the helper will
  refuse with "not on PATH".
- **The invocation carries `--trust`.** `cursor-agent` refuses headless runs in
  an untrusted directory. The helper bakes `--trust` into both the install-time
  auth probe and the scheduled run, and sets the task working directory to
  `~/.memu/hosts/cursor`, so trust lands on memU's own working tree — never on
  `System32` or wherever install was run. Do not substitute `--yolo`; that is a
  blanket permission skip.
- **The credential is the Cursor account session.** With the IDE signed in on
  this machine, the CLI reuses that session and it survives into the S4U run.
  Custom-provider (BYOK) models do not work in the CLI: scheduled runs bill the
  Cursor account plan, and a free plan can exhaust quota even though `schedule
  verify` passes.

After a scheduled run, confirm filesystem traces rather than trusting its
summary: `~/.memu/hosts/cursor/jobs/` timestamps and the session manifest must
advance. The first run has work only after new Cursor agent sessions exist.
