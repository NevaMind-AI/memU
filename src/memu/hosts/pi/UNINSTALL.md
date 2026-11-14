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

Skill installation/refresh records the host and content fingerprint in
`.memu-owned.json`. Unchanged recorded content remains removable across template
and package changes. Unrecorded skills must match the packaged content; edits,
extra files, links or invalid records require ownership review. Do not delete an
ambiguous directory to bypass this check. For custom historical locations, preview
`memu-pi remove-instruction --path <file> --skills-dir <dir> --dry-run`, then apply
without `--dry-run` after review.

Inspect old OS bridge schedules (cron/launchd on Unix, Task Scheduler on Windows).
Confirm each registration runs this host's prepare/agent/commit pipeline, remove
only that exact entry and verify absence. Do not match all hosts by a generic
pipeline phrase or task name alone. The command does not enumerate schedulers;
report unresolved entries and retain their executable until resolved.

Run `/reload` in pi or close the session to unload the extension. An already
running memory worker may finish its current pass.
