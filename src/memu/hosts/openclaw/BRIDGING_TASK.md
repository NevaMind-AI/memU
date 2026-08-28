---
name: {{task_doc_name}}
description: Create an OpenClaw cron job that bridges recent OpenClaw sessions into memU memory, skills, and resource submissions. Runs the prepare → self-evolve → commit pipeline on a schedule (default: every hour).
---

# Create the memU bridging scheduled task (OpenClaw)

## Task identity

- Current task name: `{{task_name}}`
- Former task names: {{former_task_names}}
- Names recognized during migration and removal: {{all_task_names}}

Use this when the user asks to set up or change the recurring memU bridging task.
It creates an OpenClaw-native cron job; it does not run the pipeline now. This is
also Part 2 of `memu-openclaw docs install`.

The task has one pipeline on every supported OpenClaw release:

1. `memu-openclaw prepare` slices new transcripts into numbered job files.
2. The agent follows every job file in ascending numeric order. This is real
   agent work; do not replace it with a shell script. A job may validly produce
   nothing.
3. `memu-openclaw commit` submits the memory, skill, and resource changes that
   the jobs actually made.

## Prerequisites

- `memu-openclaw doctor` succeeds in the gateway service environment.
- The isolated scheduled turn can execute on the gateway host and access both
  the memU install and OpenClaw session data. Do not weaken sandbox or approval
  policy without the user's explicit approval.
- The gateway service can resolve `memu-openclaw`. Locate it with
  `command -v memu-openclaw` on macOS/Linux or
  `(Get-Command memu-openclaw).Source` on native Windows, expose that directory
  to the gateway service if needed, then prove it through the scheduled run's
  shell-tool result; the interactive lookup alone is not verification.

## Compatibility behavior

Registration is required for every installation. Do not branch on the OpenClaw
version string. Do not block legacy installation. Do not add session identity
to the recurring prompt.

v2026.7.2-beta.4 is the first verified release with the required structural
schema. Runtime behavior is selected by schema capability, not version
comparison:

```text
Always
  create isolated cron
  -> register its stable job ID once
  -> run plain memu-openclaw prepare

prepare detects
  session_windows has session_id + session_key
    -> resolve this registered job's run sessions
    -> remember them as self-sessions
    -> exclude only their transcripts

  required schema unavailable
    -> warn once, non-blocking
    -> do not exclude the bridging transcript
    -> continue PREPARE -> SELF-EVOLVE -> COMMIT unchanged
```

Upgrading to a prerelease is optional. A legacy registration remains useful: it
starts filtering automatically after a later OpenClaw upgrade exposes the
required schema.

## Step 0 — identify and remove an existing job

Inspect existing automations before creating anything, including disabled jobs,
using the first-class automation list/get surface. For each `agentTurn` job,
inspect its complete prompt and classify it:

- **candidate:** the prompt contains all three signals: `memu-openclaw prepare`,
  `memu-openclaw commit`, and `~/.memu/hosts/openclaw/jobs/`;
- **near match:** the prompt contains one or two signals, uses an equivalent
  absolute executable or jobs path, or its name resembles a memU bridging task;
- otherwise it is unrelated. The job name alone is not proof of a candidate.

Then apply exactly one branch:

- **Exactly one candidate and zero unresolved near matches:** record its
  schedule, delete only that exact job ID, then re-list automations and verify
  it no longer appears.
- **No candidate or near match:** continue to the creation path below.
- **Multiple candidates or any near match:** stop without creating, deleting,
  registering, or guessing. Report IDs and matched signals so the user can
  choose. Do not modify `~/.memu/hosts/openclaw/` working state.

## Step 1 — settle the schedule

Reuse the recorded schedule unless the user requested a change. Otherwise use
the requested schedule; if none was supplied, ask, with hourly at `0 * * * *`
local time as the default. Confirm before creating the external job.

## Step 2 — create and register the cron job

Create an OpenClaw cron job named `{{task_name}}` with:

- an `agentTurn` payload;
- `sessionTarget="isolated"` — load-bearing because each run receives
  `agent:<agentId>:cron:<jobId>:run:<sessionId>` before the model starts;
- the selected schedule;
- the recurring prompt below. Use it verbatim for the default OpenClaw state
  directory. For a non-default `OPENCLAW_STATE_DIR`, change only the PREPARE
  command to `memu-openclaw prepare --session-dir <state-dir>/agents`.

After creating the job, register its exact new job ID on the gateway host:

    memu-openclaw register-cron-job --job-id <jobId>

The job ID is the durable identity and the only selector. Do not persist or
compare the job's current agent or model: either may change. `prepare` searches
every per-agent store and ignores the mutable agent segment in OpenClaw's
canonical scheduler key.

```
Run the memU bridging pipeline. Do the four steps strictly in order; do not
skip a step even if the previous one looks like it produced nothing.

1. LEFTOVERS. If ~/.memu/hosts/openclaw/jobs/ already contains job files, they are unfinished
   work from an earlier run (a crash, or the install itself). Process them
   exactly as step 3 describes, then run memu-openclaw commit. If this leftovers
   commit exits non-zero, stop and follow ON FAILURE; only then continue.

2. PREPARE. Run this exact command with the shell tool:

     memu-openclaw prepare

   It regenerates ~/.memu/hosts/openclaw/jobs/. If the command exits non-zero,
   stop and report the error — do not continue.

3. SELF-EVOLVE. List ~/.memu/hosts/openclaw/jobs/*.txt and sort by each filename's integer stem,
   not lexically: 1.txt, 2.txt, …, 10.txt. The count changes every run; never
   assume a fixed number. If there are no job files, skip to step 4.

   For each job file: read it and follow its instructions to the letter. Each
   job is self-contained and already carries the concrete paths it needs. Order
   matters — finish one job before starting the next. Emitting no files for a
   job is a valid outcome; do not invent content to fill a job.

4. COMMIT. After every job is done, run this exact command with the shell tool:

     memu-openclaw commit

   It commits whatever the jobs created or changed. If it exits non-zero,
   report the error.

ON FAILURE. If any PREPARE or COMMIT command exited non-zero, run this once before you stop:

     memu-openclaw report error --stage remember --detail "<a full account of what went wrong>"

   Explain which step failed, what ran, what happened, and the likely cause.
   Do not paste command output, credentials, absolute paths, memory, or
   transcript text. Ignore a failure of the report command.

Finish with a one-line summary: how many jobs ran (leftovers included) and what was committed (or
that there was nothing to commit).
```

Only the schedule varies on a default installation. The prompt carries no job,
run, or session identity. A non-default state directory changes only the PREPARE
command described above.

## Step 3 — verify

Trigger the created job once and inspect its tool result plus gateway-host
filesystem traces; do not trust only its prose summary.

Every version:

- the scheduled tool result must show `memu-openclaw prepare` resolved and ran on
  the gateway host;
- fresh job timestamps or the current cycle's pending cursor prove `prepare`
  executed; the pipeline then reaches `commit`, or explicitly reports nothing
  to commit.

Structural schema:

- take the session ID from that triggered run's scheduler result, not from an
  older transcript or the newest database row;
- that ID appears in
  `~/.memu/hosts/openclaw/.self_sessions.openclaw.json`;
- that ID is absent from
  `~/.memu/hosts/openclaw/.session_manifest.openclaw.json.pending` when the
  pending manifest exists.

Legacy schema:

- one non-blocking compatibility warning is expected;
- sessions from legacy releases still produce jobs and the pipeline completes.

Report the job name and schedule in words. The first run only has work after new
OpenClaw session turns exist.

## Load-bearing notes

- Drain leftovers before `prepare`: prepare replaces unprocessed job files after
  their session cursor has already advanced.
- Always process jobs in ascending numeric order: memory before skill, resource
  description last.
- Existing schedules whose PREPARE step already runs plain
  `memu-openclaw prepare` need no prompt rewrite; register their exact job ID.
- Never infer the newest database row or match prompt text. Concurrent sessions
  and recalled text make both unsafe identity signals.
