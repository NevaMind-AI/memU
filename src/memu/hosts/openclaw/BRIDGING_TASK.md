---
name: create-memu-bridging-task
description: Create an OpenClaw cron job that bridges recent OpenClaw sessions into memU memory, skills, and resource submissions. Runs the prepare → self-evolve → commit pipeline on a schedule (default: every hour).
---

# Create the memU bridging scheduled task (OpenClaw)

Use this when the user asks to **set up (or change) the recurring memU
"bridging" task** — the job that periodically turns what the agent recently did
in its OpenClaw sessions into memU memory files, skills, and resource
submissions.

Memory and skills are durable in both modes. In cloud mode, the current service
accepts workspace resources from this unchanged pipeline but does not persist or
retrieve them yet.

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
- **The scheduled turn can execute on the gateway host.** If OpenClaw sandboxes
  non-main sessions, an isolated cron turn's default shell tool may run inside
  that sandbox, where the host's memU install and `~/.openclaw/agents` are not
  visible. Do not create a schedule that can only run there: use an agent/runtime
  whose policy permits unattended gateway-host exec, then verify the actual
  scheduled run below. Never weaken an existing sandbox or approval policy
  without the user's explicit approval.

## Step 1 — settle the schedule

Ask the user for a schedule if the request doesn't include one. **Default: every
hour**, cron `0 * * * *` (local time). Confirm before creating.

## Step 2 — create the cron job

Create an OpenClaw cron job (e.g. named `memu-remember`) with an `agentTurn`
payload and `sessionTarget="isolated"`, using the chosen schedule. Set its
recurring prompt to the block below **verbatim**. The isolated target is
load-bearing: OpenClaw gives every run a structural
`agent:<agentId>:cron:<jobId>:run:<sessionId>` identity before the model starts.

After creation, copy the returned job ID and register it once on the gateway
host, replacing both placeholders with the values used to create the job:

    memu-openclaw register-cron-job --job-id <jobId> --agent-id <agentId>

Do not put the job's session ID into its prompt. `prepare` reads the registered
job ID and resolves all of that job's exact run sessions directly from
OpenClaw's session store; ordinary cron jobs remain mineable.

**The scheduled turn runs in the gateway's environment, not your interactive
shell.** The gateway is a launchd/systemd/Windows service with a bare `PATH` —
user-level Python installs may not resolve there even though they resolve for
an interactive user. Find the executable with `command -v memu-openclaw` on
macOS/Linux or `(Get-Command memu-openclaw).Source` on native Windows. Make that
directory available to the gateway service, then restart the gateway. On
Windows Hub's default WSL gateway, follow the Linux path; a Windows node is not
the gateway unless exec is explicitly bound there.

```
Run the memU bridging pipeline. Do the four steps strictly in order; do not
skip a step even if the previous one looks like it produced nothing.

1. LEFTOVERS. If ~/.memu/hosts/openclaw/jobs/ already contains job files, they are unfinished
   work from an earlier run (a crash, or the install itself). Process them
   exactly as step 3 describes, then run memu-openclaw commit — and only then
   continue.

2. PREPARE. Run this exact command with the shell tool:

     memu-openclaw prepare

   It resolves this registered cron job's sessions from OpenClaw's structural
   session metadata, remembers them as self-sessions, and regenerates
   ~/.memu/hosts/openclaw/jobs/. If the command exits non-zero, stop and report
   the error — do not continue.

3. SELF-EVOLVE. List ~/.memu/hosts/openclaw/jobs/*.txt and process them in
   ascending numeric order (1.txt, then 2.txt, …). The count changes every run —
   always glob and sort; never assume a fixed number. If there are no job
   files, skip to step 4.

   For each job file: read it and follow its instructions to the letter. Each
   job is self-contained and already carries the concrete paths it needs. Order
   matters — finish one job before starting the next. Emitting no files for a
   job is a valid outcome; do not invent content to fill a job.

4. COMMIT. After every job is done, run this exact command with the shell tool:

     memu-openclaw commit

   It commits whatever the jobs created or changed. If it exits non-zero,
   report the error.

ON FAILURE. If step 2 or step 4 exited non-zero, run this once before you stop:

     memu-openclaw report error --stage remember --detail "<a full account of what went wrong>"

   That detail is all a memU engineer gets to work out what is broken on this
   machine, so be generous: which step, what you ran, what happened instead,
   what you already tried, and what you think the cause is. Write it as prose
   for a human, not as a transcript — do not paste the traceback or raw command
   output, which the CLI already reports on its own, and keep credentials,
   absolute paths, and memory or transcript text out of it. Ignore any failure
   of that command; it is never part of the run.

Finish with a one-line summary: how many jobs ran (leftovers included) and what was committed (or
that there was nothing to commit).
```

The prompt block is fixed; only the schedule is the user's choice. Its shell
commands are platform-neutral, and it carries no run or session identity.

## Step 3 — confirm

**Your interactive shell's `PATH` proves nothing about the scheduler's.** A
local preflight (`command -v memu-openclaw` on macOS/Linux, or
`Get-Command memu-openclaw` on native Windows) only tells you which directory
the gateway needs.

The hard check is cross-platform: trigger the registered job twice, plus one
ordinary isolated cron control. Then inspect its tool result and verify
**filesystem traces** on the gateway host: both registered run IDs appear in
`.self_sessions.openclaw.json`, neither appears in the pending manifest, and the
control session does. Also inspect the registered run's conversation/tool
records: no concrete session ID, `session_status`, or memU session-identity
environment variable should appear. Do not trust the run's own prose summary;
scheduled runs in bare or sandboxed environments have reported success after
command-not-found or after operating on the wrong filesystem.

Report back: the cron job's name and the schedule in words (e.g. "hourly at :00
local time"). Mention that the first run only has work to do once there are new
OpenClaw sessions since the last run.

## Notes

- **The registration is the identity handoff.** Existing schedules need no
  prompt rewrite if their PREPARE step already runs plain `memu-openclaw
  prepare`; register their exact job ID once. Schedules created from the older
  prompt-mediated guide should remove `session_status` and both identity
  variables after registration. Never infer the newest database row or match
  prompt text: concurrent sessions and recalled text make both unsafe.
- **Leftovers run before prepare.** Job files already on disk when the run
  starts are unfinished work — a run that died mid-pipeline, or the install's
  own verify. `prepare` deletes unprocessed job files, and the cursor already
  marks their sessions as seen, so anything skipped at that moment would never
  be minable again; draining leftovers first turns a half-done cycle into
  bounded re-work instead of silent loss.
- **Idempotent and incremental.** `prepare` tracks a per-session cursor in
  `~/.memu/hosts/openclaw/.session_manifest.openclaw.json`: JSONL sessions use
  their line count, while SQLite sessions also record OpenClaw's rewrite
  generation so a manual compact/replacement invalidates the old row offset.
- **Ordering is load-bearing.** Memory jobs before skill jobs, the
  resource-describe job last. Always ascending numeric order.
- **The working tree is host-scoped.** Everything under
  `~/.memu/hosts/openclaw/` is this adapter's run-scoped working state; other
  memU host adapters never race with it. The durable store they all share is the
  backend selected by `MEMU_MEMORY_MODE` in `~/.memu/config.env`; local mode
  uses the `MEMU_DB` there.
- **Failure handling.** Steps 1 and 3 are the only failure points that should
  abort the run. A "do nothing" job in step 2 is normal, not an error.
