# Uninstall memU for pi

<!-- memu-cleanup: owned-artifacts -->

<!-- memu-pi-install: extension-v1 -->
<!-- {{task_name}} | {{former_task_names}} | {{all_task_names}} -->

```sh
memu-pi uninstall
```

Use the same `PI_CODING_AGENT_DIR` if pi uses a custom agent directory. The CLI
removes memU's extension, managed blocks in both `AGENTS.md` and
`AGENTS.override.md`, and its verified retrieval skill under `skills/memu-retrieve`.
It preserves unrelated instructions, skills, pi settings, sessions, shared memory
and working files. Ownership is checked before removing the extension. Stop on
a nonzero exit and report the path needing review.

On exit 0, accept the CLI result; do not inspect AGENTS.md, SKILL.md or ownership
records, or run retrieval-only cleanup afterward. On a nonzero exit, stop and
report the diagnostic, investigating only the reported failure. Do not bypass
ownership checks by deleting files manually.

Only if the user explicitly identifies a custom historical location, run
`memu-pi remove-instruction --path <file> --skills-dir <dir>` for that location.
Otherwise skip this step; do not search other profiles for hypothetical residue.

Inspect old OS bridge schedules (cron/launchd on Unix, Task Scheduler on Windows).
Confirm each registration runs this host's prepare/agent/commit pipeline, remove
only that exact entry and verify absence. Do not match all hosts by a generic
pipeline phrase or task name alone. The command does not enumerate schedulers;
report unresolved entries and retain their executable until resolved.

Run `/reload` in pi or close the session to unload the extension. An already
running memory worker may finish its current pass.
