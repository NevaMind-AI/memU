# OpenClaw: retrieval and injection

## Trigger and query {#trigger}

After backend configuration, follow `memu-openclaw docs install`. `memu-openclaw install-instruction` installs a pointer in `~/.openclaw/workspace/AGENTS.md` and the procedure in `~/.openclaw/skills/memu-retrieve/SKILL.md`. OpenClaw loads the workspace instruction at session start; open a fresh session after installation.

The instruction asks the agent to use the retrieval skill before answering. The agent forms a query and invokes `memu-openclaw retrieve "<query>"` as an ordinary command tool call. memU does not install an automatic per-prompt retrieval hook for this host; the optional hook query-extraction switch does not govern this path.

## Injection timing {#injection}

The tool result enters the active conversation when retrieve finishes. The agent then uses relevant excerpts or opens a returned path before continuing. See the [shared result format](retrieval.md#results). Empty or failed retrieval should let the original task continue.

The standing pointer is loaded context; memory results arrive only after an actual retrieve tool call. A configured record schedule is not evidence that the skill ran.

## Profiles and recording {#recording}

For a custom `OPENCLAW_STATE_DIR`, pass its managed skills directory as `--skills-dir` and the actual workspace `AGENTS.md` as `--path` when installing instructions. Keep installation and runtime on the same workspace/profile.

The separate bridging task records session history on the schedule configured by the installation guide. It writes to the same backend but does not deliver results to a live turn. Memories become searchable after processing and commit.

## Activate and verify {#verify}

```sh
memu-openclaw doctor
memu-openclaw retrieve "a known saved topic"
memu-openclaw install-instruction --dry-run
```

Check both the workspace instruction and skill file. In a fresh session, ask about known memory and verify the actual tool call and relevant result use. A manual backend check cannot prove that OpenClaw loaded the correct workspace or skill.

See [Configuration](../reference/configuration.md) and `memu-openclaw docs install` for setup and scheduling.
