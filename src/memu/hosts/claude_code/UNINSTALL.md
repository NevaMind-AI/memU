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

The CLI performs ownership checks and cleanup. On exit 0, accept its result;
do not read CLAUDE.md, SKILL.md or ownership records, run `remove-instruction`,
or repeat filesystem checks after success. On a nonzero exit, stop and report
the diagnostic; investigate only the reported path and do not bypass the check
by deleting files manually.

Also inspect any previously configured memU schedules. Confirm this host's
prepare/agent/commit action before removing each exact registration, then verify
absence. Check OS scheduling and the host's native task surface where applicable;
a missing registration is a no-op. Do not remove tasks by name alone or a generic
"memU bridging pipeline" phrase. The terminal command does not enumerate these
schedulers; report unresolved entries and retain the executable while needed.
Do not remove the package shared by other hosts or erase user memory.

Legacy task names: current `{{task_name}}`; former {{former_task_names}};
all recognized names: {{all_task_names}}.
