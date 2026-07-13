# Install memU for Codex

> **Audience: the agent.** A user will point you at this file ("follow this guide
> to install memU"). Work top to bottom. Each part ends with a **verify** gate —
> do not proceed to the next part until the current one verifies. Every path you
> write into a task or hook config must be **absolute** and correct for *this*
> machine; resolve them freshly, never copy the examples.
>
> **Status: SKETCH.** Parts marked ⚠️ depend on pieces that are decided (ADR 0009)
> but may not be built yet — confirm they exist before relying on them, and fall
> back to the noted alternative if not.

Installing memU on Codex is three parts:

1. **Install / verify memU** — a Python package on this machine.
2. **Register the bridging task** — the scheduled job that turns recent Codex
   sessions into durable memory (the *record* seam).
3. **Install the retrieval hook** — a UserPromptSubmit hook that tells you to pull
   relevant memory before each turn (the *inject* seam).

Parts 2 and 3 share one store and one config. Part 1 establishes both.

---

## Part 1 — Install or verify memU

memU is distributed as a **pip package** (ADR 0009: a Python runtime is required
either way, because the bridging task's scripts `import memu`). Do **not** look for
an npm package — there isn't one.

### 1.1 Check for an existing install

Try, in order, to find a Python interpreter that can import memU:

```
python3 -c "import memu; print(memu.__file__)"
```

If that fails, look for a project virtualenv (commonly `.venv/bin/python` at a repo
root) and try the same import with it. Record the interpreter that works as
**`<VENV_PYTHON>`** — you will need its absolute path in Part 2.

### 1.2 Fresh install (only if 1.1 found nothing)

Create/activate an environment and install the package:

```
pip install memu            # or: pip install -e <path-to-checkout>
```

Then re-run the import check and capture the absolute interpreter path as
`<VENV_PYTHON>` (e.g. `<venv>/bin/python`).

### 1.3 Configure the store and provider  ⚠️

memU needs at minimum a **database DSN** and an **LLM/embedding provider + API
key**. The *record* and *inject* seams must use **identical** config or retrieval
reads a different (empty) store than bridging wrote — so config is decided **once,
here**, and written to a file every seam loads (ADR 0009).

Collect from the user (or reuse existing values):

| Setting | Env var | Example |
| --- | --- | --- |
| Database DSN | `MEMU_DB` | `sqlite:////Users/<you>/.memu/memu.sqlite3` or `postgres://…` |
| Provider | `MEMU_LLM_PROVIDER` | `openai`, `anthropic`, … |

Write them to **`~/.memu/config.env`** (a dotenv), which every entrypoint loads:

```
MEMU_DB=sqlite:////Users/<you>/.memu/memu.sqlite3
MEMU_LLM_PROVIDER=openai
```

> Do **not** rely on exporting these in a shell profile — the scheduled task in
> Part 2 runs with no reliable inherited environment. The file is the carrier.

### ✅ Verify Part 1

Run a retrieval against the configured store and confirm it exits cleanly (an empty
result is fine — the store is just new):

```
memu retrieve "smoke test"    # ⚠️ if `memu` is not on PATH: <VENV_PYTHON> -m memu.cli retrieve "smoke test"
```

If this errors on config (e.g. wrong DSN), fix `~/.memu/config.env` before
continuing. Both later parts depend on this working.

---

## Part 2 — Register the bridging (record) task

This is the *record* seam: a Codex scheduled task that periodically bridges recent
`~/.codex/sessions` into durable memU memory/skills/resources.

**Do not reinvent this.** Follow **`skills/codex-memu-task/SKILL.md`** — it is the
authoritative procedure. In summary, you will:

1. Resolve `<VENV_PYTHON>` (from Part 1) and `<SKILL_DIR>` (the directory containing
   that `SKILL.md`), and verify `<VENV_PYTHON> -c "import memu; print('ok')"`.
2. Settle a cron schedule with the user (default: daily at midnight, `0 0 * * *`).
3. Create a Codex scheduled task named e.g. `memu-bridging` whose recurring prompt
   is the exact three-step block (PREPARE → SELF-EVOLVE → COMMIT) from that SKILL.md,
   with the absolute paths substituted in.

The scripts it runs (`prepare_jobs.py`, `commit_results.py`) load the same
`~/.memu/config.env` from Part 1, so the task writes to the store you configured.

### ✅ Verify Part 2

Confirm the scheduled task exists with the expected name and cron, and that the
embedded script paths are the absolute ones you resolved. Report them back to the
user. (First run only does work once there are new sessions since the last run.)

---

## Part 3 — Install the retrieval (inject) hook

This is the *inject* seam: a **UserPromptSubmit** hook that, before you respond to a
user prompt, injects a single instruction telling you to retrieve relevant memory
first. You then run the retrieval yourself and factor the results into your answer.

See the Codex hooks reference for the exact config location and schema:
<https://learn.chatgpt.com/docs/hooks#userpromptsubmit> ⚠️ *(confirm the concrete
file/format there before writing — the block below is the intent, not verified
syntax).*

### 3.1 The injected instruction

The hook adds one instruction to the turn. Keep it to a single line, e.g.:

```
Before answering, run `memu retrieve "<query>"` — where <query> is the user's
request, reworded into a clearer query or focused keywords when that retrieves
better (you need not pass their raw words verbatim). Use any relevant results as
context. If it returns nothing, proceed normally.
```

Notes:
- It points at the **CLI** (`memu retrieve`), not a script — the CLI is on PATH and
  is a stable contract (ADR 0009).
- ⚠️ This should target the **LLM-free single-shot** retrieval
  (`progressive_retrieve`). If a dedicated subcommand/flag for it exists
  (e.g. `memu retrieve --progressive`), use that; otherwise use `memu retrieve` and
  note the fallback to the user.
- It **fails open**: an empty store or a miss injects nothing and the turn proceeds.

### 3.2 Register the hook  ⚠️

Add a `UserPromptSubmit` hook to the Codex hook configuration that emits the
instruction above. Follow the linked docs for the exact file and shape; conceptually
it is one hook entry that outputs the instruction string on the `UserPromptSubmit`
event.

### ✅ Verify Part 3

Start a normal Codex prompt and confirm the instruction appears in-context (i.e. you
are prompted to run `memu retrieve …`). Run that command once by hand to confirm it
returns without error against the Part 1 store.

---

## Done

Report back to the user:

- the interpreter (`<VENV_PYTHON>`) and store DSN in use;
- the scheduled task name + cron (in words, e.g. "daily at 00:00 local");
- that the UserPromptSubmit retrieval hook is installed.

Record (Part 2) and inject (Part 3) now share the one store you configured in
Part 1, so what the task learns becomes retrievable on later prompts.
