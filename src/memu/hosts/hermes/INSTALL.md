# Install memU for Hermes Agent

<!-- memu-hermes-install: plugin-v1 -->
<!-- {{task_name}} | {{former_task_names}} | {{all_task_names}} -->

Install Hermes first, then configure memU using the existing shared backend:

```sh
memu-hermes install --non-interactive --language en
```

For a new backend, pass `--backend cloud --cloud-api-key <key>` or
`--backend local --db <absolute-path>` with embedding settings. See
`memu-hermes install --help`.

The installer checks Hermes availability and backend connectivity, writes the
managed `memu-memory` plugin, enables it through `hermes plugins enable`, and
verifies its local files. Use the same `HERMES_HOME` as the Hermes profile you
want to configure. On native Windows the default is `%LOCALAPPDATA%\hermes`;
on Linux/macOS it is `~/.hermes`.

Restart Hermes to load the plugin. Each user turn retrieves context through
`pre_llm_call`; successful turn completion starts detached memory processing
through `on_session_end`. The worker uses the existing Hermes model/provider
configuration. The installer does not verify model access with a paid request.
Retrieval waits up to 20 seconds and uses at most the first 2,000 characters of
the user text. Hook diagnostics live under `~/.memu/hosts/hermes/log/hooks/`.
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
Restart Hermes after cleanup. Inspect and remove previous scheduled bridging
tasks separately to avoid duplicate processing.
Stop on a nonzero installer exit and report its diagnostic.
