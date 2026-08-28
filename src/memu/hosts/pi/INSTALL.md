# Install memU for pi

## Task identity

- Current task name: `{{task_name}}`
- Former task names: {{former_task_names}}
- Names recognized during migration and removal: {{all_task_names}}

> **Audience: the agent.** Work top to bottom. Do not continue past a failing
> verify gate. Finish or abandon the run by reporting the outcome at the end.

Installing memU for pi has three parts: configure the shared memory backend,
schedule pi to bridge new sessions, and add the retrieval skill to pi's global
instructions.

## Part 1 — Install and configure memU

```sh
pip install --upgrade memu-cli
memu-pi --help
```

`--upgrade` matters: an existing older package otherwise stays installed. If
`memu-pi` is missing, the installed package predates this adapter or its scripts
directory is not on `PATH`.

If pi itself is missing, install it with its official npm package:

```sh
npm install -g --ignore-scripts @earendil-works/pi-coding-agent
```

Create the shared memU configuration. If `SKILL.md` already ran `init`, reusing
the existing mode is correct and re-running is harmless:

```sh
memu-pi init --cloud-api-key <the user's memU key>
```

Use bare `memu-pi init` for local memory. Never edit `~/.memu/config.env` by
hand. Inspect it with `memu-pi config show`; reuse an existing backend from
another host. Otherwise configure exactly one:

```sh
memu-pi config --cloud --cloud-api-key <memu-api-key>
memu-pi config --local --db /absolute/path/memu.sqlite3 --embed-provider openai --embed-api-key <key>
```

Give `--db` an absolute path. Shell-only environment variables do not reach a
scheduled run.

### Verify Part 1

```sh
memu-pi doctor
pi -p "Reply with exactly: ok"
```

Both commands must exit cleanly. Zero retrieval hits is normal for a new store.
The pi probe proves a model and persistent credential work without an
interactive login.

## Part 2 — Register the record bridge

By default pi stores v3 JSONL sessions below `~/.pi/agent/sessions`. The adapter
keeps user and assistant text, routes tool calls and results to the full
transcript, and ignores session, compaction, model, and thinking metadata.

If `PI_CODING_AGENT_DIR`, `PI_CODING_AGENT_SESSION_DIR`, or `settings.json` moves
the session directory, pass the final directory to `memu-pi prepare
--session-dir <dir>` and use the same explicit path in the scheduled prompt.

**Refresh an existing bridging registration before continuing.** Check cron or
launchd for `hosts/pi/bridge\.sh|memU bridging pipeline`, or Task Scheduler for
`{{task_name}}`. Record its cadence and remove **only** that registration, then
verify it is gone. An absent registration is the normal first-install case.
Reuse the recorded cadence unless the user requested a change.

Follow the packaged scheduler procedure:

```sh
memu-pi docs task
```

### Verify Part 2

```sh
memu-pi prepare
```

It must report a session count. Zero is correct when no new turns exist.

## Part 3 — Install retrieval

Pi loads one global context file from its agent directory. Normally that is
`~/.pi/agent/AGENTS.md`; if `AGENTS.override.md` already exists there, it takes
precedence, so target that file instead. A custom `PI_CODING_AGENT_DIR` moves
both the instruction and skills directories.

Default installation:

```sh
memu-pi install-instruction
```

Custom or override installation:

```sh
memu-pi install-instruction --path <agent-dir>/AGENTS.override.md --skills-dir <agent-dir>/skills
```

The command creates `skills/memu-retrieve/SKILL.md` and adds one managed pointer
block to the selected global context file. Existing content is preserved;
re-running is idempotent.

### Verify Part 3

```sh
memu-pi retrieve "smoke test"
```

Confirm the managed block occurs once, the skill exists, and a fresh pi session
loads the selected context file. Empty result lists are valid.

## Report the outcome to memU

Every gate passed:

```sh
memu-pi report install
```

If the run stops early:

```sh
memu-pi report error --stage install --detail "<what failed, what was tried, and the likely cause>"
```

The report is best-effort. Do not include credentials, absolute paths, memory,
transcript text, or raw command output.

## Done

Tell the user which backend was selected, where the schedule was registered,
its cadence, and that retrieval takes effect in the next pi session.
