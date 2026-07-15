---
name: create-memu-bridging-task
description: Register a scheduled job that bridges the agent's recent Cursor agent sessions into durable memU memory, skills, and resources. Runs the prepare → self-evolve → commit pipeline on a schedule (default: every day at midnight).
---

# Create the memU bridging scheduled task (Cursor)

Use this when the user asks to **set up (or change) the recurring memU
"bridging" task** — the job that periodically turns what the agent recently did
in its Cursor agent sessions into durable memU memory files, skills, and
resource records.

Your goal is to **register a recurring headless Cursor agent run** whose prompt
is the three-step pipeline below. You are not running the pipeline now.

Part of the full setup in `INSTALL.md` (`memu-cursor docs install`), but usable
on its own.

## What the bridging task does (context)

1. **Prepare** — `memu-cursor prepare` scans new turns under
   `~/.cursor/projects/*/agent-transcripts/` (one JSONL transcript per agent
   session), mirrors the current memU recall files to
   `~/.memu/hosts/cursor/memory` and `~/.memu/hosts/cursor/skill`, snapshots
   them by content hash, and writes numbered **job-instruction files** to
   `~/.memu/hosts/cursor/jobs/` (`1.txt`, `2.txt`, …).
2. **Self-evolve** — the agent opens each job file **in numeric order** and
   follows it: mine a session into user **memory**, mine a session into a
   **skill**, and **describe** the files the sessions touched. "Do nothing" is
   an allowed, common outcome for any job.
3. **Commit** — `memu-cursor commit` diffs the tracked directories against the
   step-1 snapshot and submits what the agent actually created or changed back
   to memU.

Only steps 1 and 3 are code. **Step 2 is real agent work**, so the scheduled
run's prompt must instruct the agent to do it, not shell out to a script.

## Prerequisites

- **memU is installed and `memu-cursor` is on `PATH`.** Verify with
  `memu-cursor doctor`; if it fails, do `INSTALL.md` Part 1 first.
- **`cursor-agent` runs headless.** The scheduled entry invokes
  `cursor-agent -p` non-interactively with permission to run `memu-cursor` and
  write under `~/.memu/`.

## Step 1 — settle the schedule

Ask the user for a schedule if the request doesn't include one. **Default: every
day at midnight**, cron `0 0 * * *` (local time). Confirm before creating.

## Step 2 — register the scheduled run

Create a system cron entry (or launchd job on macOS, if the user prefers)
running:

```
0 0 * * * cursor-agent -p 'Run the memU bridging pipeline. Do the three steps strictly in order; do not skip a step even if the previous one looks like it produced nothing.  1. PREPARE. Run this exact command with bash:  memu-cursor prepare  — it regenerates ~/.memu/hosts/cursor/jobs/. If the command exits non-zero, stop and report the error.  2. SELF-EVOLVE. List ~/.memu/hosts/cursor/jobs/*.txt and process them in ascending numeric order (1.txt, then 2.txt, …). The count changes every run — always glob and sort. If there are no job files, skip to step 3. For each job file: read it and follow its instructions to the letter. Each job is self-contained and already carries the concrete paths it needs. Emitting no files for a job is a valid outcome; do not invent content.  3. COMMIT. Run this exact command with bash:  memu-cursor commit  — it commits whatever the jobs created or changed. If it exits non-zero, report the error.  Finish with a one-line summary: how many jobs ran and what was committed.'
```

The prompt block is fixed; only the cron expression is the user's choice. Nothing
in it is machine-specific — the pipeline is invoked through `PATH` commands.

## Step 3 — confirm

Report back: where the schedule was registered, and the cron in words. Mention
that the first run only has work to do once there are new Cursor agent sessions
since the last run.

## Notes

- **Idempotent and incremental.** `prepare` tracks a per-session line cursor in
  `~/.memu/hosts/cursor/.session_manifest.cursor.json`.
- **Ordering is load-bearing.** Memory jobs before skill jobs, the
  resource-describe job last. Always ascending numeric order.
- **The working tree is host-scoped.** Everything under `~/.memu/hosts/cursor/`
  is this adapter's run-scoped working state; other memU host adapters never
  race with it. The durable store they all share is the `MEMU_DB` in
  `~/.memu/config.env`.
- **Failure handling.** Steps 1 and 3 are the only failure points that should
  abort the run. A "do nothing" job in step 2 is normal, not an error.
