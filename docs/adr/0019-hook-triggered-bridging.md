ADR 0019: Hook-Triggered Bridging — Network Steps Outside the Agent

- Status: Proposed
- Date: 2026-10-01
- Builds on: ADR 0009 (the CLI seam), ADR 0010 (multi-host adapters from a
  `HostSpec`), ADR 0015 (the bridging run must not mine itself)
- Scope: how the record seam is triggered and where its network steps run, for
  Codex and Claude Code. The pipeline (`prepare` → jobs → `commit`), the job
  files, the cursor, and the store contract are unchanged. Other hosts keep
  their scheduled task.

## Context

The record seam ran as a scheduled agent session whose prompt told the agent to
run `<binary> prepare`, work through the job files, then run `<binary> commit`.
Both commands need the network — `prepare` mirrors the store
(`list_all_recall_files`), `commit` embeds and writes (`commit_results`, or
memU Cloud) — and they ran *inside the agent's sandbox*. Codex scheduled tasks
run with network denied, so `commit` fails there; `claude -p` needs each command
pre-authorized in `settings.json`, and a missing or stale rule fails the run
silently in the background.

The judgement work in the middle — reading transcripts, writing Markdown — is
the only part that needs an agent, and it needs no network at all.

## Decision

Trigger bridging from the host's own hook, and run every network step in a
plain process outside the agent:

1. `<binary> install-hook` registers `<binary> hook` — Claude Code's
   `SessionEnd` command hook in `~/.claude/settings.json`; Codex's top-level
   `notify` in `~/.codex/config.toml`. Absolute paths for both memU and the
   agent binary are baked in, because a hook inherits the host app's `PATH`.
2. `hook` spawns `<binary> hook-run` detached and returns at once, so the host
   is never blocked. It never fails the host: problems go to `hook.log`.
3. `hook-run` takes a per-host lock, then performs the scheduled prompt's four
   steps as code: drain leftover jobs, `prepare`, run the headless agent over
   `jobs/*.txt` (prompt on stdin, cwd = the working tree), `commit`. The agent
   runs with exactly what the jobs need — Codex `exec --sandbox
   workspace-write`; Claude `-p --permission-mode acceptEdits` plus explicit
   `--allowedTools` — and is told not to run prepare or commit.
4. A failed agent run raises before `commit`, so jobs and the staged cursor stay
   for the next run, exactly as a crashed scheduled run did (#518).

Supporting rules:

- **No recursion.** The agent runs with `MEMU_BRIDGING_RUN=1`; its own hook
  sees it and stands down.
- **No self-mining (ADR 0015).** Claude's run takes a `--session-id` memU
  chooses, recorded before the transcript exists. Codex's thread id is read
  from `exec --json` (`thread.started`) and recorded after; the Codex source's
  `session_id` now returns the rollout file's trailing thread id to match.
- **Bursts.** A hook that finds the lock held leaves a re-run marker; the
  running pass goes again (bounded). Codex's `notify` fires per reply, so its
  hook defaults to a 30-minute minimum interval; later turns go to the next run.
- **Coexistence.** Codex allows one `notify` program. An existing one is saved
  to `codex-notify-chain.json`, every payload is forwarded to it, and
  `remove-hook` restores it. `settings.json` edits touch only memU's entry.

## Consequences

- Uploads no longer depend on any sandbox or permission rule; the scheduled
  task, its cron/launchd/Task Scheduler wrappers, and the `Bash(memu-… *)`
  allow rule are not needed for these two hosts.
- Mining latency follows activity, not a clock: a session is mined when it
  ends (Claude Code) or within the interval (Codex). A machine with no new
  sessions does no work.
- Hooks fire only from front ends that run them (Codex `notify`: the terminal
  UI). Sessions from other front ends are still mined — by the next run some
  hooked session triggers — since `prepare` scans every session from the cursor.
- The guides served from the server (ADR 0013) must be updated alongside the
  embedded ones, or installs keep following the scheduled procedure.
