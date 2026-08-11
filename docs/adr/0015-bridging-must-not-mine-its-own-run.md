ADR 0015: The Bridging Run Must Not Mine Itself — Identity from the Host, Gate from the Launch

- Status: Proposed
- Date: 2026-07-29
- Builds on: ADR 0008 (trajectory as the source), ADR 0010 (multi-host adapters), ADR 0011
  (generic host adapter)
- Scope: how a bridging run recognises the host session it is *itself* running in, so
  `prepare` never slices its own bookkeeping into a mining job. It does not change the
  pipeline, the cursor, `classify`, or any host's log format.

## Context

ADR 0008 chose trajectory as the source: memorization is not an API call the user makes but
a scheduled *agent run* that reads what the agent recently did. ADR 0010 then made that run
one shape across hosts — a `TranscriptSource` plus a thin CLI.

Neither ADR wrote down the consequence: **the record seam produces trajectory too.** The
bridging task runs as a session of the host agent, and the host logs that session in exactly
the directory (or table) memU discovers sessions from. So:

- every run hands the next run fresh "new" content, and `prepare` can never report zero —
  killing the idle signal that both `INSTALL.md` and the silent-blindness diagnosis of #528
  lean on;
- the mining jobs chew through memU's own `prepare → self-evolve → commit` bookkeeping;
- worst of the three, those transcripts are the *newest* on disk, so newest-first discovery
  floats them above real conversation and they consume the `MAX_JOBS` slots. That is the same
  harm #532/#533 fixed for trajectory/checkpoint sidecars, arriving from a different source.

Measured on one machine, counting only sessions that were actually sliced into a job:
`claude_code` 19 of 95 tracked sessions (2,111 of 25,833 records); `hermes` 4 of 5. On
`hermes` the entire mined "conversation" of one such session was a single run summary whose
own words were *"bridge sessions meta-only"* — the mining agent had already noticed what it
was reading.

Tracked as #606.

## Decision

### 1. Identity comes from the host, never from the transcript

A run learns *which* session it is in from the host, through
`HostSpec.session_id_env` — the environment variable the host uses to hand a tool subprocess
its session id (`CLAUDE_CODE_SESSION_ID`). `prepare` executes *inside* that session, so this
is an exact identity, not an inference. The id is appended to
`~/.memu/hosts/<host>/.self_sessions.<host>.json`, host-scoped for the same reason the cursor
file is, and `discover()`'s results are filtered against it.

`TranscriptSource.session_id()` maps a discovered session back to that same id. The default
is the file stem; hosts whose naming carries more than the id override it.

The rejected alternative — a sentinel string in the bridging prompt, matched against the
transcript — fails on two independent grounds, and both are worth recording because the idea
is the obvious one:

- **Content flows.** Paste the prompt into a chat to debug it, and it is mined into a memory;
  `retrieve` then injects that memory into an unrelated session, which now matches the rule
  and is skipped. Silent loss of real conversation. A rule that can be quoted can be forged.
- **Prompt prose drifts.** #591 caught a live host prompt diverging from canon
  ("shell tool" vs "bash") with the sync test not noticing. A sentinel tied to prose breaks
  the moment the prose is revised; an environment variable is not prose.

Filtering on the host's own scheduling metadata (`created_via = 'cron'`) was also rejected:
#532 settled that cron is not noise — a cron-driven prompt is a session-driving instruction —
so that filter would discard the user's own scheduled conversations. This decision is
strictly narrower.

### 2. Only the *scheduled* run may claim a session — the gate is the launch, not the command

Running `prepare` is **not** evidence that a session belongs to bridging. It is an ordinary
command, run during development and — more importantly — as a deliberate "remember this
conversation now". Treating its execution as the signal excludes the very session the user
asked to have mined, permanently and for every later run: the opposite of the request, and
silent.

So two facts must hold, and they come from different places:

```
the launcher : knows "this is a bridging run"   · does not know the session id
prepare      : knows the session id             · does not know why it is running
```

The launch-side fact is carried by `MEMU_BRIDGING_RUN`, exported by the invocation memU
controls, or by the run's working directory being the host's memU tree (`schedule` passes
`-WorkingDirectory`; the Unix wrapper cannot rely on this, since cron's cwd is `$HOME`).
Either suffices. Anything unrecognised is treated as a person: nothing recorded, nothing
skipped — failing open toward the pre-#606 behaviour, never toward dropping user data.

Both signals live in the *invocation*, not in the conversation, so neither is forgeable by an
injected memory. That is what separates them from the sentinel in decision 1.

### 3. Skip by `continue`, never by `break`

The scan stops at the first already-seen unchanged session, which is sound only because
discovery is newest-first. Self-sessions are the newest files on disk, so ending the scan
there would hide every real session beneath them. They are passed over instead.

### 4. The gate has three grades, and a host's grade follows from how it is scheduled

Hosts differ in *who* schedules the run, and this is the part that does not generalise for
free:

- **memU writes the invocation** (`claude_code`, `cursor`, `hermes` — crontab, launchd, Task
  Scheduler). The wrapper exports the marker. Strong: no prose, no compliance.
- **The host schedules it natively and the payload is a prompt** (`openclaw`'s `openclaw
  cron`, `codex`, `workbuddy`, `cola`'s native task UI). There is no wrapper to write, so the
  marker can only ride in the documented command inside the prompt. It is still read from the
  process environment rather than matched against a transcript, so it cannot be forged — but
  it depends on the agent reproducing the command, and #591 is the evidence that prompts
  drift. Weaker, and it fails open.
- **The host records which scheduled job created the session.** Where this exists it is
  better than either. OpenClaw persists every isolated run under the exact structural key
  `agent:<agentId>:cron:<jobId>:run:<sessionId>` in `session_windows` before the model starts.
  memU records the stable job id once at install time, then checks every per-agent store and
  accepts only rows whose key equals that store's agent prefix plus the registered job id and
  the row's own session id. This follows agent-owner changes without persisting mutable routing
  state. It needs neither marker nor
  environment variable, does not select the newest row, and never puts the concrete session
  id into prompt or tool content. Preferred wherever a host offers it.

A host's grade is not a fixed property of the host — it follows from what its guide tells the
user to register. `codex` sits in the second grade because its guide creates a native Codex
scheduled task; registering `codex exec` under an OS scheduler instead would move it to the
first. So the grade is something a guide can improve, not something to accept.

So each new host adapter owes one exact identity seam appropriate to its launcher. An
OS-scheduled host supplies the variable name (surveyed on a real install, on Unix — Windows
`os.environ` is case-insensitive and will hide a casing error), a `session_id()` that returns
what it holds, and a launch-side marker. A native-scheduled host may instead register the
exact task identity and resolve sessions from structural scheduler metadata. Both feed the
same remembered self-session list and `continue` filter; their identity sources need not be
forced into one shape.

## Consequences

- Every host is a separate survey. As of this ADR `claude_code` is verified end to end
  (2.1.220: headless `claude -p` exports the variable, and its value is the transcript's file
  name), and Hermes is verified to export `HERMES_SESSION_ID` to tool subprocesses during a
  one-shot run, matching its SQLite session id. Hosts with `session_id_env` empty keep the
  pre-#606 behaviour, which is why the default is empty rather than guessed.
- Codex still needs a `session_id()` override before an environment seam can be wired
  (`rollout-<ts>-<uuid>.jsonl` — the stem is not the id). OpenClaw instead uses its native
  scheduler metadata and therefore does not ask the run to report its own id. Hermes's
  virtual paths now return `path.name`, matching the SQLite id without truncating ids that
  contain a dot.
- Subagent transcripts must be attributed to the session that spawned them, not to their own
  file name: a run that spawns a subagent produces bookkeeping under a different name. Claude
  Code nests them two ways (`<sessionId>/subagents/…` and
  `<sessionId>/subagents/workflows/<wf>/…`), so attribution reads the first directory under
  the project slug rather than the parent directory.
- The fix is forward-only. Bridging sessions already recorded stay in the cursor and are
  inert — a finished session gains no new lines, so it is never re-offered.
- Claiming a session is permanent and therefore announced: `prepare` prints the id and the
  file to remove. The one remaining false positive is a person running `prepare` from inside
  the host's memU tree, which is visible and reversible.
- Upgrading an existing OS-scheduled install is not automatic. Unix users must re-copy the
  wrapper to pick up the marker; Windows tasks already pass `-WorkingDirectory`, so the
  directory signal covers them until `schedule install` is re-run. OpenClaw users instead
  register the existing memU cron job id once; the recurring prompt then returns to a plain
  `memu-openclaw prepare` call.

## Out of scope

- **`generic` cannot be wired by memU, because memU does not know what it is.** ADR 0011
  makes the host indeterminate by design, and *both* halves are missing rather than just one:
  there is no known variable to read, and no invocation that can be assumed to be ours to
  mark — the guide suggests cron, but a generic agent may well have a scheduler of its own,
  and memU never sees which the user chose. The escape is the one ADR 0011 already relies on:
  the user supplies what detection cannot. `session_id_env` is data, so a flag could carry it
  for an agent that does export an id. Deliberately not decided here.
- Wiring the remaining hosts, pending their surveys.
- Assigning the session id ourselves (`claude --session-id <uuid>`) was considered: it would
  make the id known before launch, covering a run that dies before `prepare`. Rejected as
  narrower than it looks — it needs both that memU launches the host *and* that the CLI has
  such a flag, which of the CLIs surveyed only `claude` does. Recorded so it is not
  re-proposed as a general answer.
- Not writing the run's session at all. Some agent CLIs appear to offer this — one machine's
  `claude --help` (2.1.220) and `codex exec --help` (codex-cli 0.144.5) each list such a flag.
  **Neither was run**: the behaviour above is read off a one-line help string, and which
  versions have it is unknown, so nothing in this ADR rests on it. If it does what it says, it
  would remove the problem rather than skip it — but only where memU constructs the
  invocation, and at the cost of the transcript a failed run is debugged from. Verify before
  building on it.

## Related ADRs

- Builds on `docs/adr/0008-two-integration-surfaces-hooks-and-api.md` — names the consequence
  of "trajectory as the source": the seam emits trajectory of its own.
- Builds on `docs/adr/0010-multi-host-adapters.md` — adds `session_id_env` and
  `session_id()` to what a host declaration owes, alongside its existing fields.
- Builds on `docs/adr/0011-generic-host-adapter.md` — the indeterminate host is the one memU
  cannot wire on its own; if it is wired, the user supplies the missing value, as with
  `--session-dir`.
