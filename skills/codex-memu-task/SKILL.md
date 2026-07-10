---
name: create-memu-bridging-task
description: Create a Codex scheduled task that bridges the agent's recent Codex sessions into durable memU memory, skills, and resources. Runs the prepare → self-evolve → commit pipeline on a schedule (default: every day at midnight).
---

# Create the memU bridging scheduled task

Use this skill when the user asks to **set up (or update) the recurring memU
"bridging" task** — the job that periodically turns what the agent recently did
in its Codex sessions into durable memU memory files, skills, and resource
records.

Your goal is to **create a Codex scheduled task** whose recurring prompt runs
the three-step pipeline below. You are not running the pipeline now; you are
registering the schedule that will run it later.

## What the bridging task does (context)

Each run walks a fixed pipeline that "bridges" raw session history into memU:

1. **Prepare** — `prepare_jobs.py` scans new turns in `~/.codex/sessions`,
   mirrors the current memU recall files to `~/.memu/memory` and `~/.memu/skill`,
   snapshots them by content hash, and writes a set of numbered
   **job-instruction files** to `~/.memu/jobs/` (`1.txt`, `2.txt`, …). Each job
   is a self-contained prompt telling the agent exactly what to mine from one
   session.
2. **Self-evolve** — the agent opens each `~/.memu/jobs/*.txt` **in numeric
   order** and follows it. Jobs are of three kinds: mine a session into user
   **memory**, mine a session into a **skill**, and **describe** the files the
   sessions touched. These jobs write/patch markdown under `~/.memu/memory` and
   `~/.memu/skill`, and fill in `~/.memu/resources.md`. "Do nothing" is an
   allowed, common outcome for any job.
3. **Commit** — `commit_results.py` diffs the tracked dirs against the step-1
   snapshot, collects only the files the agent actually created or changed plus
   the described resources, and submits them back to memU via `MemoryService`.

Only steps 1 and 3 are scripts. **Step 2 is real agent work** — reading
transcripts, making judgement calls, writing markdown — so the scheduled task's
prompt must instruct the agent to do it, not shell out to a script.

## Prerequisites (resolve these on the current machine before creating the task)

The scheduled task runs with no reliable working directory, so every path in its
prompt must be **absolute** and correct for *this* machine. Do not copy the
example paths — resolve them freshly each time:

- **`<SKILL_DIR>`** — the absolute path of the directory that contains *this*
  `SKILL.md`. The scripts live in its `scripts/` subfolder, so the two you need
  are:
  - `<SKILL_DIR>/scripts/prepare_jobs.py`
  - `<SKILL_DIR>/scripts/commit_results.py`

  Resolve it however is reliable in your environment — e.g. locate the skill on
  disk and take its directory, or from the repo root run:
  `find . -path '*/codex-memu-task/scripts/prepare_jobs.py'`.

- **`<VENV_PYTHON>`** — an absolute path to a Python interpreter that can
  `import memu`. The scripts depend on the `memu` package, which normally lives
  only in the project virtualenv, so the system `python3` usually will **not**
  work. Find the venv (commonly a `.venv/bin/python` at the repo root) and
  verify it before embedding it:

  ```
  <VENV_PYTHON> -c "import memu; print('ok')"
  ```

  If that prints `ok`, use that interpreter. Otherwise locate/activate the
  correct environment first.

Substitute the resolved `<VENV_PYTHON>` and `<SKILL_DIR>` values into the prompt
block below wherever the placeholders appear.

## Step 1 — settle the schedule

Ask the user for a schedule if the request doesn't include one. **Default: every
day at midnight**, cron `0 0 * * *` (local time). Confirm the cron expression
before creating the task.

## Step 2 — create the scheduled task

Create a Codex scheduled task with the chosen cron and set its recurring prompt
to the block below, **with `<VENV_PYTHON>` and `<SKILL_DIR>` replaced by the
absolute paths you resolved in Prerequisites**. Every other line must be copied
verbatim. Give it a clear name such as `memu-bridging`.

```
Run the memU bridging pipeline. Do the three steps strictly in order; do not
skip a step even if the previous one looks like it produced nothing.

1. PREPARE. Run this exact command with bash:

     <VENV_PYTHON> <SKILL_DIR>/scripts/prepare_jobs.py

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

     <VENV_PYTHON> <SKILL_DIR>/scripts/commit_results.py

   It commits whatever the jobs created or changed. If it exits non-zero, report
   the error.

Finish with a one-line summary: how many jobs ran and what was committed (or
that there was nothing to commit).
```

## Step 3 — confirm

Report back to the user: the task name, the cron schedule (in words, e.g. "daily
at 00:00 local time"), and the resolved script paths you embedded. Mention that
the first run will only have work to do once there are new Codex sessions since
the last run.

## Notes

- **Idempotent & incremental.** `prepare_jobs.py` tracks a per-session line
  cursor in `~/.memu/.session_manifest.json`, so each run only processes session
  turns it hasn't seen. A run with no new session activity correctly does
  nothing.
- **Ordering is load-bearing.** Memory jobs are numbered before skill jobs, and
  the resource-describe job is last; some later jobs depend on files earlier
  jobs write (e.g. the resource log). Always process in ascending numeric order.
- **Failure handling.** Steps 1 and 3 are the only failure points that should
  abort the run; a single "do nothing" job in step 2 is normal, not an error.
