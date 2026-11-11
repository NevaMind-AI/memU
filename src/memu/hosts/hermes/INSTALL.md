# Install memU for Hermes Agent

<!-- memu-hermes-install: soul-v1 -->
<!-- {{task_name}} | {{former_task_names}} | {{all_task_names}} -->

Install Hermes and make `hermes` available on PATH, then run:

```sh
memu-hermes install --non-interactive --language en
```

The installer checks CLI availability, configures and checks the memory backend,
cleans verified legacy Windows schedules, removes a legacy managed memU plugin
when present, and installs the complete retrieval procedure in one managed
SOUL.md block. It reads the block back before reporting success. Repeating
installation updates the block in place while preserving other SOUL.md content.
The integration patches the instruction file and uses subprocess CLI commands;
it does not load Hermes's Python modules or require Hermes v0.23.1.

For a new backend, pass `--backend cloud --cloud-api-key <key>` or
`--backend local --db <absolute-path>` with embedding settings. See
`memu-hermes install --help`.

## Active profile and SOUL.md

All paths use the shared `hermes_home()` resolver. Hermes-launched subprocesses
inherit the selected profile through `HERMES_HOME`, which takes precedence.
Otherwise the platform default is `%LOCALAPPDATA%\hermes` on Windows and
`~/.hermes` on Linux/macOS. Windows falls back to
`%USERPROFILE%\AppData\Local\hermes` if LOCALAPPDATA is absent.
`HERMES_DATA_DIR_SUFFIX` applies to platform defaults. The CLI resolves the home
when invoked; SOUL.md is always relative to that home.

Start a fresh Hermes session to load the updated SOUL.md. If a legacy plugin was
removed, restart running Hermes processes to unload its callbacks. Installation
reports `restart_required=true`; it does not claim live gateway activation.

## On-demand retrieval

The agent decides whether prior preferences, decisions, or project history can
resolve missing information. Greetings and self-contained tasks normally need
no retrieval. The agent reads the whole request, forms a short query, and runs
`memu-hermes retrieve "<query>"` as an ordinary tool call. It uses applicable
results to continue the original task; empty or failed retrieval does not justify
inventing prior decisions. The tool UI may display the result and the agent may
wait for it. No separate extraction-model call is involved.

To manage only the instruction with an already-configured backend:

```sh
memu-hermes install-instruction --dry-run
memu-hermes install-instruction
memu-hermes remove-instruction
```

Default-path instruction installation removes a legacy `memu-retrieve` skill
after writing the inline procedure. `--path` can target a separate SOUL.md
without cleaning another profile's skills. Full `install` also handles legacy
plugin and schedule migration; `install-instruction` only patches instructions.

## Legacy cleanup

On Windows, install and uninstall inspect tasks under `\memU\` using recognized
task names, expected PowerShell wrapper action, and working directory. Errors
stop the operation; removal is verified by querying Task Scheduler again.
Generated scripts, logs, and memory are kept. Use the original `--base-dir` for
a custom legacy workspace. Preview or remove these registrations directly with:

```sh
memu-hermes schedule status
memu-hermes schedule uninstall
```

A legacy `memu-memory` plugin is removed only after checking its ownership and
files, using `hermes plugins remove memu-memory`, followed by a directory absence
check. Failed or unsupported CLI removal fails installation. Unknown files and
symlinks require inspection rather than automatic deletion.

Linux/macOS schedules and Hermes native cron require separate inspection and
removal. For native jobs use `hermes cron list --all`, inspect ownership, remove
confirmed memU bridging job IDs with `hermes cron remove <job-id>`, then list again.
Unsupported schedule cleanup commands return nonzero. Stop on a nonzero installer
exit and report its diagnostic.

## Memorization

SOUL.md installation configures on-demand retrieval only. It does not schedule
background memorization. The existing `prepare`, `verify-resources`, `commit`,
and CLI-driven `hook-run` bridging commands remain available for explicitly
managed memory processing; see `memu-hermes docs task`. Agent-directed retrieval
coverage and Desktop behavior still need broader real-model evaluation.
