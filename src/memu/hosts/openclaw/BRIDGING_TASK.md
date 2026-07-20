---
name: create-memu-bridging-task
description: Create an OpenClaw cron job that bridges the agent's recent OpenClaw sessions into durable memU memory, skills, and resources. Runs the prepare → self-evolve → commit pipeline on a schedule (default: every hour).
---

# Create the memU bridging scheduled task (OpenClaw)

Use this when the user asks to **set up (or change) the recurring memU
"bridging" task** — the job that periodically turns what the agent recently did
in its OpenClaw sessions into durable memU memory files, skills, and resource
records.

Your goal is to **create an OpenClaw cron job** (OpenClaw schedules agent runs
natively) whose recurring prompt runs the three-step pipeline below. You are not
running the pipeline now; you are registering the schedule that will run it
later.

Part of the full setup in `INSTALL.md` (`memu-openclaw docs install`), but
usable on its own.

## What the bridging task does (context)

1. **Prepare** — `memu-openclaw prepare` scans new turns under
   `~/.openclaw/agents/*/sessions/` (one JSONL transcript per session, all
   agents), mirrors the current memU recall files to
   `~/.memu/hosts/openclaw/memory` and `~/.memu/hosts/openclaw/skill`, snapshots
   them by content hash, and writes numbered **job-instruction files** to
   `~/.memu/hosts/openclaw/jobs/` (`1.txt`, `2.txt`, …).
2. **Self-evolve** — the agent opens each job file **in numeric order** and
   follows it: mine a session into user **memory**, mine a session into a
   **skill**, and **describe** the files the sessions touched. "Do nothing" is
   an allowed, common outcome for any job.
3. **Commit** — `memu-openclaw commit` diffs the tracked directories against the
   step-1 snapshot and submits what the agent actually created or changed back
   to memU.

Only steps 1 and 3 are code. **Step 2 is real agent work**, so the cron job's
prompt must instruct the agent to do it, not shell out to a script.

## Prerequisites

- **memU is installed and `memu-openclaw` is on `PATH`** for the environment the
  cron job's shell tool runs in. Verify with `memu-openclaw doctor`; if it
  fails, do `INSTALL.md` Part 1 first.

## Step 1 — settle the schedule

Ask the user for a schedule if the request doesn't include one. **Default: every
hour**, cron `0 * * * *` (local time). Confirm before creating.

## Step 2 — create the cron job

Create an OpenClaw cron job (e.g. named `memu-bridging`) with the chosen
schedule, and set its recurring prompt to this block **verbatim**:

**The scheduled turn runs in the gateway's environment, not your shell.** The
gateway is a system service (launchd/systemd) with a bare `PATH` —
`memu-openclaw` (pipx installs land in `~/.local/bin`) may not resolve there
even though it resolves for you. Make it resolvable to the *gateway* before
trusting the schedule: add a `PATH` entry under `env` in `openclaw.json`
(include the directory `command -v memu-openclaw` prints), then restart the
gateway.

```
Run the memU bridging pipeline. Do the three steps strictly in order; do not
skip a step even if the previous one looks like it produced nothing.

1. PREPARE. Run this exact command with the shell tool:

     memu-openclaw prepare

   It regenerates ~/.memu/hosts/openclaw/jobs/. If the command exits non-zero,
   stop and report the error — do not continue.

2. SELF-EVOLVE. List ~/.memu/hosts/openclaw/jobs/*.txt and process them in
   ascending numeric order (1.txt, then 2.txt, …). The count changes every run —
   always glob and sort; never assume a fixed number. If there are no job
   files, skip to step 3.

   For each job file: read it and follow its instructions to the letter. Each
   job is self-contained and already carries the concrete paths it needs. Order
   matters — finish one job before starting the next. Emitting no files for a
   job is a valid outcome; do not invent content to fill a job.

3. COMMIT. After every job is done, run this exact command with the shell tool:

     memu-openclaw commit

   It commits whatever the jobs created or changed. If it exits non-zero,
   report the error.

Finish with a one-line summary: how many jobs ran and what was committed (or
that there was nothing to commit).
```

The prompt block is fixed; only the schedule is the user's choice. Nothing in it
is machine-specific — the pipeline is invoked through `PATH` commands.

## Step 3 — confirm

**Your shell's `PATH` proves nothing about the scheduler's.** Two checks that
count:

- `env -i PATH=/usr/bin:/bin /bin/sh -c 'command -v memu-openclaw'` — this
  *failing* is exactly why the entry needs its `PATH` line; with that line in
  place the command must resolve from the directories it names.
- The hard check: trigger one run now with `openclaw cron run <job>`, then
  verify **filesystem traces** — the session
  cursor and `jobs/` timestamps moved — rather than trusting the run's own
  summary. Field data, twice over: scheduled runs in bare environments have
  reported "completed successfully" on a command-not-found.

Report back: the cron job's name and the schedule in words (e.g. "hourly at :00
local time"). Mention that the first run only has work to do once there are new
OpenClaw sessions since the last run.

## Notes

- **Idempotent and incremental.** `prepare` tracks a per-session line cursor in
  `~/.memu/hosts/openclaw/.session_manifest.openclaw.json`.
- **Ordering is load-bearing.** Memory jobs before skill jobs, the
  resource-describe job last. Always ascending numeric order.
- **The working tree is host-scoped.** Everything under
  `~/.memu/hosts/openclaw/` is this adapter's run-scoped working state; other
  memU host adapters never race with it. The durable store they all share is the
  `MEMU_DB` in `~/.memu/config.env`.
- **Failure handling.** Steps 1 and 3 are the only failure points that should
  abort the run. A "do nothing" job in step 2 is normal, not an error.
