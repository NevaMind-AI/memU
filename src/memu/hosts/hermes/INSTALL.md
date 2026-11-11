# Install memU for Hermes Agent

<!-- memu-hermes-install: plugin-v2 -->
<!-- {{task_name}} | {{former_task_names}} | {{all_task_names}} -->

Requires **Hermes v0.23.1 or newer**. This stable release includes the session
routing and queued message injection APIs used by memU across CLI, Desktop/TUI
and gateway sessions. The installer checks the CLI version before changing hooks.

Install Hermes first, then configure memU using the existing shared backend:

```sh
memu-hermes install --non-interactive --language en
```

For a new backend, pass `--backend cloud --cloud-api-key <key>` or
`--backend local --db <absolute-path>` with embedding settings. See
`memu-hermes install --help`.

The installer checks Hermes availability and backend connectivity, writes the
managed `memu-memory` plugin, grants its follow-up context injection permission
through `hermes config set plugins.entries.memu-memory.allow_gateway_injection true`,
reads the grant back, and enables the plugin through `hermes plugins enable`.
It verifies the installed files locally. Other plugin entries remain intact.
Use the same `HERMES_HOME` as the Hermes profile you
want to configure. On native Windows the default is `%LOCALAPPDATA%\hermes`;
on Linux/macOS it is `~/.hermes`.

Restart Hermes to load the plugin. `pre_llm_call` starts background retrieval
and immediately returns, allowing the model to answer. Results are queued into
the originating session through `ctx.inject_message(session_key=...)`: an idle
session starts a follow-up turn; a busy session finishes its current turn first.
The first answer may precede memory context. The plugin recognizes its own
one-use delivery marker, and waits for the retrieval continuation to complete
before starting detached memory processing. A queued result can add a model
turn. New input supersedes pending retrieval results; finalizing a session
invalidates its pending deliveries. When queued input is merged with a result,
its user-authored text is kept. Prepared memory transcripts omit the marked
retrieval context so it is not mined again as new user information.
The worker uses the existing Hermes model/provider configuration. The installer
does not verify model access with a paid request. Background retrieval is bounded
to 20 seconds and uses at most the first 2,000 characters of the user text.
Hook diagnostics live under `~/.memu/hosts/hermes/log/hooks/`.
The plugin runs memU with its installing Python runtime and clears inherited
`PYTHONPATH`/`PYTHONHOME` overrides. Subprocess startup errors, including the exit
code and bounded stderr, are recorded in Hermes's agent/error logs.

Existing SOUL.md instructions, skills, sessions, and memory are preserved.
Before relying on hooks, preview and remove the previous memU retrieval
instruction and legacy `memu-retrieve` skill:

```sh
memu-hermes remove-instruction --dry-run
memu-hermes remove-instruction
```

These commands use the active Hermes home described above, remove all complete
managed blocks belonging to `memu-hermes`, and preserve other SOUL.md content.
Restart Hermes after cleanup.

On Windows, install and uninstall automatically inspect legacy tasks under
`\memU\` using the recognized task names, expected PowerShell wrapper action,
and working directory. Cleanup errors stop the operation; removal is verified
by querying Task Scheduler again. Generated scripts, logs, and memory are kept.
Use the original `--base-dir` for a custom legacy workspace. To preview or remove
these registrations directly:

```sh
memu-hermes schedule status
memu-hermes schedule uninstall
```

The verified cleanup covers Windows Task Scheduler only. Linux/macOS schedules
and Hermes native cron jobs still require separate inspection and removal.
For native jobs, run `hermes cron list --all`, remove only confirmed memU bridging
job IDs with `hermes cron remove <job-id>`, then list again to confirm absence.
Do this before relying on hooks to avoid duplicate processing.
Stop on a nonzero installer exit and report its diagnostic.
