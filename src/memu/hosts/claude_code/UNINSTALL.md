# Uninstall memU for Claude Code

<!-- memu-cleanup: owned-artifacts -->

<!-- memu-claude-install: cli-v1 -->

For the removal Agent. Use the user's language and run:

```sh
memu-claude-code uninstall --language en
```

Use `--language zh` for Chinese. Wait for this command to exit and report its
result. It removes memU's retrieval and background memory hook definitions,
and the owned managed CLAUDE.md block and retrieval skill under `~/.claude/skills`;
it works without the Claude CLI. User instructions outside the managed block,
other skills/settings, memory, shared backend configuration, sessions, jobs,
cursors, results and logs are preserved. Open a new Claude session afterward.

The command checks retrieval skill ownership before changing hooks or instructions.
Installation and refresh record the actual skill content in `.memu-owned.json`;
unchanged recorded skills can be removed across package and server-template updates.
Unrecorded skills must match the packaged content. Edited content, extra files,
links or invalid records stop cleanup with a nonzero exit and a diagnostic;
inspect the reported path and do not bypass the check by deleting the directory.
`memu-claude-code remove-instruction --dry-run` previews retrieval-only cleanup.

Also inspect any previously configured memU schedules. Confirm this host's
prepare/agent/commit action before removing each exact registration, then verify
absence. Check OS scheduling and the host's native task surface where applicable;
a missing registration is a no-op. Do not remove tasks by name alone or a generic
"memU bridging pipeline" phrase. The terminal command does not enumerate these
schedulers; report unresolved entries and retain the executable while needed.
Do not remove the package shared by other hosts or erase user memory.

Legacy task names: current `{{task_name}}`; former {{former_task_names}};
all recognized names: {{all_task_names}}.
