# Install memU for Codex

> **Audience: the agent.** A user will point you at this file ("follow this guide
> to install memU"). Work top to bottom. Each part ends with a **verify** gate —
> do not proceed until the current one passes.
>
> Parts marked ⚠️ depend on Codex's own configuration surface, which you must
> confirm against its docs before writing. Everything on the memU side is a
> `PATH` command; you should never need to write an absolute path to a script.

Installing memU on Codex is three parts:

1. **Install memU** — a Python package, and the store + provider it writes to.
2. **Register the bridging task** — the scheduled job that turns recent Codex
   sessions into durable memory (the *record* seam).
3. **Install the retrieval hook** — a UserPromptSubmit hook that tells you to pull
   relevant memory before each turn (the *inject* seam).

Parts 2 and 3 must share one store and one embedding space, or a query is
compared against vectors written elsewhere and retrieval silently returns
nothing. Part 1 is what makes them agree.

---

## Part 1 — Install memU

memU is distributed as a **pip package**. There is no npm package — do not look
for one; a Python runtime is required regardless, because the bridging task runs
Python.

### 1.1 Install

```
pip install memu-py
```

This puts two commands on `PATH`:

- **`memu`** — memU itself (memorize, retrieve, export, …). The library's own
  surface; this guide does not use it directly.
- **`memu-codex`** — the Codex adapter. Both Part 2 (record) and Part 3 (inject)
  go through it.

Confirm it resolves:

```
memu-codex --help
```

If it is not found, the install landed in an environment that isn't on your
`PATH`. Fix that now rather than working around it — the scheduled task in Part 2
and the hook in Part 3 both need this command to resolve from a bare, non-
interactive environment.

### 1.2 Configure the store and provider

memU needs a **database** and an **LLM/embedding provider**. Both seams read this
one config, so decide it once, here.

Collect from the user (or reuse values they already have):

| Setting | Env var | Example |
| --- | --- | --- |
| Database | `MEMU_DB` | `~/.memu/memu.sqlite3`, or a `postgres://…` DSN |
| Provider | `MEMU_LLM_PROVIDER` | `openai`, `anthropic`, … |
| API key | `MEMU_API_KEY` | the key, or the name of an env var holding it |

Write them to **`~/.memu/config.env`**, which every memU command loads:

```
MEMU_DB=/Users/<you>/.memu/memu.sqlite3
MEMU_LLM_PROVIDER=openai
MEMU_API_KEY=<key or env-var name>
```

Use an **absolute** path for `MEMU_DB`. A relative one resolves against the
working directory, and the scheduled task has no reliable working directory.

> Do **not** instead export these in a shell profile. The scheduled task does not
> inherit your interactive shell. The file is the carrier; a profile export is
> not. (A `MEMU_*` variable that *is* set in the environment wins over the file,
> so you can still override for one command.)

The API key sits in plaintext in this file. Tell the user, and set the
permissions: `chmod 600 ~/.memu/config.env`.

### ✅ Verify Part 1

```
memu-codex doctor
```

It prints the store and provider it resolved and runs a smoke-test retrieval. It
must exit cleanly. **Zero hits is the expected result** — the store is new; you
are testing that config resolves and the store answers, not that it has content.

If it errors, fix `~/.memu/config.env` before continuing. Both later parts depend
on this working, and both fail *silently* if it is wrong.

---

## Part 2 — Register the bridging (record) task

The *record* seam: a Codex scheduled task that periodically mines recent
`~/.codex/sessions` into durable memU memory, skills, and resources.

**Do not reinvent this.** Follow the packaged procedure:

```
memu-codex docs task
```

It is authoritative. In summary, you will settle a cron schedule with the user
(default: daily at midnight, `0 0 * * *`) and create a Codex scheduled task whose
recurring prompt is the three-step block that document gives you verbatim —
`memu-codex prepare`, then the agent works through `~/.memu/jobs/*.txt` in order,
then `memu-codex commit`.

Nothing in that prompt is machine-specific. If you find yourself substituting an
absolute path into it, you are doing it wrong.

### ✅ Verify Part 2

Confirm the scheduled task exists with the expected name and cron. Then dry-run
the first step by hand:

```
memu-codex prepare
```

It should report how many sessions it prepared (zero, if there is nothing new
since the cursor — that is fine and correct). Report the task name and schedule
back to the user.

---

## Part 3 — Install the retrieval (inject) hook

The *inject* seam: a **UserPromptSubmit** hook that, before you answer a prompt,
injects one instruction telling you to retrieve relevant memory first. You then
run the retrieval yourself and factor the results into your answer.

⚠️ Check Codex's hooks reference for the exact config file and schema before
writing anything: <https://learn.chatgpt.com/docs/hooks#userpromptsubmit>. The
block below is the *intent*; the syntax is whatever those docs specify.

### 3.1 The injected instruction

One line, added to the turn:

```
Before answering, run `memu-codex retrieve "<query>"` — where <query> is the
user's request, reworded into a clearer query or focused keywords when that
retrieves better (you need not pass their raw words verbatim). Use any relevant
results as context. If it returns nothing, proceed normally.
```

Notes:

- It points at **`memu-codex retrieve`**, a `PATH` command, never a script path.
  This is the LLM-free single-shot retrieval: it embeds the query once and ranks
  memory, skills, and resources. It prints JSON.
- Do **not** point the hook at `memu retrieve`. That is the LLM-routed path —
  high quality, but it costs an LLM call on every single turn, which is not what
  a prompt hook should do.
- It **fails open**: an empty store or a miss returns empty lists and the turn
  proceeds as normal.

### 3.2 Register the hook

Add a `UserPromptSubmit` hook to Codex's hook configuration that emits the
instruction above. Follow the linked docs for the exact file and shape;
conceptually it is one hook entry that outputs that string on the
`UserPromptSubmit` event.

### ✅ Verify Part 3

Start a normal Codex prompt and confirm the instruction reaches you in-context
(i.e. you are told to run `memu-codex retrieve …`). Run that command once by hand
and confirm it returns without error against the Part 1 store:

```
memu-codex retrieve "smoke test"
```

Empty result lists are fine — you are testing that the read path works, not that
the store has content yet.

---

## Done

Report back to the user:

- the store (`MEMU_DB`) and provider now in use;
- the scheduled task's name and cron, in words (e.g. "daily at 00:00 local");
- that the UserPromptSubmit retrieval hook is installed.

Record (Part 2) and inject (Part 3) both read `~/.memu/config.env`, so they
provably share the store you configured in Part 1 — what the task learns tonight
is what retrieval finds tomorrow.
