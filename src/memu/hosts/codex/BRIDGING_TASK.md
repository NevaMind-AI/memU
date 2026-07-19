---
name: create-memu-bridging-task
description: Create a Codex scheduled task that bridges the agent's recent Codex sessions into durable memU memory, skills, and resources. Runs the prepare → self-evolve → commit pipeline on a schedule (default: every hour).
---

# Create the memU bridging scheduled task

Use this when the user asks to **set up (or change) the recurring memU "bridging"
task** — the job that periodically turns what the agent recently did in its Codex
sessions into durable memU memory files, skills, and resource records.

Your goal is to **create a Codex scheduled task** whose recurring prompt runs the
three-step pipeline below. You are not running the pipeline now; you are
registering the schedule that will run it later.

Part of the full setup in `INSTALL.md` (`memu-codex docs install`), but usable on
its own to add or re-schedule the task on a machine where memU is already
installed.

## What the bridging task does (context)

Each run walks a fixed pipeline that bridges raw session history into memU:

1. **Prepare** — `memu-codex prepare` scans new turns under `~/.codex/sessions`,
   mirrors the current memU recall files to `~/.memu/memory` and `~/.memu/skill`,
   snapshots them by content hash, and writes a set of numbered **job-instruction
   files** to `~/.memu/jobs/` (`1.txt`, `2.txt`, …). Each job is a self-contained
   prompt telling the agent exactly what to mine from one session.
2. **Self-evolve** — the agent opens each `~/.memu/jobs/*.txt` **in numeric
   order** and follows it. Jobs come in three kinds: mine a session into user
   **memory**, mine a session into a **skill**, and **describe** the files the
   sessions touched. They write and patch markdown under `~/.memu/memory` and
   `~/.memu/skill`, and fill in `~/.memu/resources.md`. "Do nothing" is an
   allowed, common outcome for any job.
3. **Commit** — `memu-codex commit` diffs the tracked directories against the
   step-1 snapshot, collects only the files the agent actually created or changed
   plus the described resources, and submits them back to memU.

Only steps 1 and 3 are code. **Step 2 is real agent work** — reading transcripts,
making judgement calls, writing markdown — so the scheduled task's prompt must
instruct the agent to do it, not shell out to a script.

## Prerequisites

- **memU is installed and `memu-codex` is on `PATH`.** Verify:

  ```
  memu-codex doctor
  ```

  It prints the store and provider in use and runs a smoke-test retrieval. If it
  fails, stop — do `INSTALL.md` Part 1 first. Do not proceed with a broken store:
  the task would happily run and write nowhere useful.

There are no paths to resolve. The pipeline is invoked through `PATH` commands, so
nothing in the task prompt is specific to this machine's directory layout.

## Step 1 — settle the schedule

Ask the user for a schedule if the request doesn't include one. **Default: every
hour**, cron `0 * * * *` (local time). Confirm the cron expression
before creating the task.

## Step 2 — create the scheduled task

Create a Codex scheduled task with the chosen cron, named e.g. `memu-bridging`,
and set its recurring prompt to this block **verbatim**:

```
Run the memU bridging pipeline. Do the three steps strictly in order; do not
skip a step even if the previous one looks like it produced nothing.

1. PREPARE. Run this exact command with bash:

     memu-codex prepare

   It regenerates ~/.memu/jobs/. If the command exits non-zero, stop and report
   the error — do not continue.

2. SELF-EVOLVE. List ~/.memu/jobs/*.txt and process them in ascending numeric
   order (1.txt, then 2.txt, …). There may be anywhere from 0 to ~21 files, and
   the count changes every run — always glob and sort; never assume a fixed
   number. If there are no job files, skip to step 3.

   For each job file: read it with `cat` and follow its instructions to the
   letter. Each job is self-contained and already carries the concrete paths it
   needs. Order matters — finish one job before starting the next. Emitting no
   files for a job is a valid outcome; do not invent content to fill a job.

3. COMMIT. After every job is done, run this exact command with bash:

     memu-codex commit

   It commits whatever the jobs created or changed. If it exits non-zero, report
   the error.

Finish with a one-line summary: how many jobs ran and what was committed (or
that there was nothing to commit).
```

## Step 3 — confirm

Report back to the user: the task name and the cron schedule in words (e.g. "hourly
at :00 local time"). Mention that the first run only has work to do once there
are new Codex sessions since the last run.

## Notes

- **Idempotent and incremental.** `prepare` tracks a per-session line cursor in
  `~/.memu/.session_manifest.codex.json`, so each run only processes turns it
  hasn't seen. A run with no new session activity correctly does nothing.
- **Ordering is load-bearing.** Memory jobs are numbered before skill jobs, and
  the resource-describe job is last — later jobs depend on files earlier ones
  write (the skill jobs are what populate the touched-file log the resource job
  reads). Always process in ascending numeric order.
- **Failure handling.** Steps 1 and 3 are the only failure points that should
  abort the run. A single "do nothing" job in step 2 is normal, not an error.
