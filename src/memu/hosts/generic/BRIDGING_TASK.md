---
name: create-memu-bridging-task
description: Register a scheduled job that bridges an agent's recent sessions into durable memU memory, skills, and resources via the generic memu-agent adapter. Runs the prepare → self-evolve → commit pipeline on a schedule (default: every day at midnight).
---

# Create the memU bridging scheduled task (generic `memu-agent`)

Use this when the user asks to **set up (or change) the recurring memU
"bridging" task** for an agent that has no dedicated memU adapter — the job
that periodically turns what the agent recently did into durable memU memory
files, skills, and resource records.

Your goal is to **register a recurring headless run** whose prompt is the
three-step pipeline below. You are not running the pipeline now.

Part of the full setup in `INSTALL.md` (`memu-agent docs install`), but usable
on its own.

## Prerequisite: the session directory

This adapter has no built-in session location. `memu-agent detect` must
already have found one whose records it recognizes (its report says
"memorization: works"). Call it `<SESSION_DIR>` below — it is the **one**
machine-specific value in this task, fixed once at registration time.

Also verify `memu-agent doctor` passes; if not, do `INSTALL.md` Part 1 first.

## What the bridging task does (context)

1. **Prepare** — `memu-agent prepare --session-dir <SESSION_DIR>` scans new
   turns, mirrors the current memU recall files to
   `~/.memu/hosts/agent/memory` and `~/.memu/hosts/agent/skill`, snapshots
   them by content hash, and writes numbered **job-instruction files** to
   `~/.memu/hosts/agent/jobs/` (`1.txt`, `2.txt`, …).
2. **Self-evolve** — the agent opens each job file **in numeric order** and
   follows it: mine a session into user **memory**, mine a session into a
   **skill**, and **describe** the files the sessions touched. "Do nothing" is
   an allowed, common outcome for any job.
3. **Commit** — `memu-agent commit` diffs the tracked directories against the
   step-1 snapshot and submits what the agent actually created or changed back
   to memU.

Only steps 1 and 3 are code. **Step 2 is real agent work**, so the scheduled
run's prompt must instruct the agent to do it, not shell out to a script.

## Step 1 — settle the schedule

Ask the user for a schedule if the request doesn't include one. **Default:
every day at midnight**, cron `0 0 * * *` (local time). Confirm before
creating.

## Step 2 — register the scheduled run

Use the agent's own scheduler if it has one; otherwise a system cron entry
invoking the agent headless. The recurring prompt, with `<SESSION_DIR>` filled
in, **verbatim**:

```
Run the memU bridging pipeline. Do the three steps strictly in order; do not
skip a step even if the previous one looks like it produced nothing.

1. PREPARE. Run this exact command with the shell tool:

     memu-agent prepare --session-dir <SESSION_DIR>

   It regenerates ~/.memu/hosts/agent/jobs/. If the command exits non-zero,
   stop and report the error — do not continue.

2. SELF-EVOLVE. List ~/.memu/hosts/agent/jobs/*.txt and process them in
   ascending numeric order (1.txt, then 2.txt, …). The count changes every
   run — always glob and sort; never assume a fixed number. If there are no
   job files, skip to step 3.

   For each job file: read it and follow its instructions to the letter. Each
   job is self-contained and already carries the concrete paths it needs.
   Order matters — finish one job before starting the next. Emitting no files
   for a job is a valid outcome; do not invent content to fill a job.

3. COMMIT. After every job is done, run this exact command with the shell
   tool:

     memu-agent commit

   It commits whatever the jobs created or changed. If it exits non-zero,
   report the error.

Finish with a one-line summary: how many jobs ran and what was committed (or
that there was nothing to commit).
```

## Step 3 — confirm

Report back: where the schedule was registered, and the cron in words. Mention
that the first run only has work to do once there are new sessions since the
last run.

## Notes

- **Idempotent and incremental.** `prepare` tracks a per-session line cursor
  in `~/.memu/hosts/agent/.session_manifest.agent.json`.
- **Bounded per run.** Each run mines at most `--max-jobs` sessions (default
  10), newest first; sessions beyond the cap are skipped, not queued — memU
  starts accumulating memory when installed and does not retroactively mine a
  backlog. A skipped session is only picked up later if it gains new turns — a
  later run does not return for it even when it has spare capacity — so if
  more than 10 sessions regularly change between runs, schedule the task more
  frequently or raise `--max-jobs`.
- **Several generic agents on one machine** must not share a working tree: add
  `--base-dir ~/.memu/hosts/<name>` to both `prepare` and `commit` in each
  task's prompt.
- **Ordering is load-bearing.** Memory jobs before skill jobs, the
  resource-describe job last. Always ascending numeric order.
- **Failure handling.** Steps 1 and 3 are the only failure points that should
  abort the run. A "do nothing" job in step 2 is normal, not an error.
