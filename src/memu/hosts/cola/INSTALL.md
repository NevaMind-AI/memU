# Install memU for Cola

> **Audience: the agent.** Work top to bottom. Each verify gate must pass
> before continuing.
>
> However this run ends — finished or abandoned — close it out with **Report
> the outcome to memU** at the bottom of this file.

Installing memU on Cola has three parts: install the shared backend, register
the scheduled bridge that records Cola sessions, and install the retrieval
skill plus its memory-bank pointer.

## Part 1 — Install and configure memU

```sh
pip install memu-cli
memu-cola --help
```

Reuse `~/.memu/config.env` if another memU host already configured it. Otherwise
ask the user to choose MemU Cloud or this device, write the chosen `MEMU_*`
settings to that file, use an absolute local `MEMU_DB`, and protect it with
`chmod 600 ~/.memu/config.env`. Never put these settings only in a shell profile:
Cola's scheduled task does not inherit an interactive shell.

### Verify Part 1

```sh
memu-cola doctor
```

The command must exit cleanly. A smoke-test retrieval with zero hits is normal
for a new store.

## Part 2 — Register the record bridge

Cola stores transcripts at `~/.cola/sessions/<scope>/*.jsonl`. `memu-cola`
reads user and assistant text plus tool calls, and ignores session headers and
model/thinking metadata.

Do not edit `~/.cola/crons.json` yourself. Ask Cola to follow its packaged task
procedure:

```sh
memu-cola docs task
```

On this machine the task is named `memU 记忆桥接`, has ID `memu-bridging`, runs
on `desktop:local`, and defaults to `0 * * * *` (hourly). Reuse and update that
task if it already exists; do not duplicate it.

### Verify Part 2

```sh
memu-cola prepare
```

It must report the number of prepared sessions. Zero is correct when no new
Cola turns have appeared since the cursor.

## Part 3 — Install retrieval

```sh
memu-cola install-instruction
```

This creates `~/.cola/resources/skills/memu-retrieve/SKILL.md` and adds a
managed pointer block to `~/.cola/memory-bank/MEMORY.md`. The skill contains
the detailed procedure; the memory-bank index keeps only the short instruction
to use it before answering. Existing memory-bank content is retained and backed
up before modification. Re-running is idempotent; use `--dry-run` or `--print`
to inspect the change first.

### Verify Part 3

```sh
memu-cola retrieve "smoke test"
```

Confirm the skill exists, the memory-bank block occurs exactly once, and a fresh
Cola session loads it. Empty result lists are valid.

---

## Report the outcome to memU

memU is otherwise blind to whether any of this worked: an install that died in
Part 2 looks exactly like one that was never attempted. Close this run with
**one** command, whichever way it ended.

It is best-effort throughout and never part of the install — if the command
fails, ignore it, and if `memu-cola` is not on `PATH` (a Part 1 that never
finished), there is nothing to report with, which is fine.

**Every gate passed:**

```
memu-cola report install
```

The event's *existence* is the success signal: there is no failure flag, and
nothing leaves the machine here — it records locally and returns.

**You are stopping early instead** — a part that failed, or a prerequisite you
could not resolve — then tell the user as usual:

```
memu-cola report error --stage install --detail "<a full account of what went wrong>"
```

**Be generous with `--detail`.** It is the whole of what a memU engineer will
have to work out what is broken on this machine, and a one-line summary tells
them almost nothing. Write a paragraph or two of plain language: which gate you
were on, what you ran, what happened instead of what the guide predicted, what
you had already tried, and what you believe the cause is. Your reading of the
failure is the part nobody else can reconstruct — that is what belongs here.
Report once for the run, not once per retry.

**Detailed, not a transcript.** Do not paste the traceback or raw command
output: memU reports the exception type and its frames on its own, so repeating
them only crowds out your account. And keep out, always: an API key, token, or
any other credential; an absolute path (`/Users/…`, `C:\Users\…`); a database
DSN or an endpoint URL; the user's memory content, file contents, or transcript
text. Describe those in words instead — *"the local embedding server answers 502
through what looks like a system proxy"* says everything useful and names
nothing secret.

## Done

Report the selected backend, the bridge task and schedule, and that Cola's
memory-bank index now points to the `memu-retrieve` skill. Both seams share
`~/.memu/config.env`, so recorded sessions and retrieval use the same backend.
