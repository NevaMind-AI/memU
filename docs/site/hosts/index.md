# Host adapters

Host adapters connect a desktop or coding agent to the shared memory backend. Choose the binary for your host:

| Host | Binary |
| --- | --- |
| [Codex](codex.md) | `memu-codex` |
| [Claude Code](claude-code.md) | `memu-claude-code` |
| [Cursor](cursor.md) | `memu-cursor` |
| [OpenClaw](openclaw.md) | `memu-openclaw` |
| [Hermes](hermes.md) | `memu-hermes` |
| [WorkBuddy](workbuddy.md) | `memu-workbuddy` |
| [pi](pi.md) | `memu-pi` |

Want to bring memU to your favorite coding agent? New host adapters are welcome—PRs welcome! See the [contribution guide](https://github.com/XnneHangLab-Mirror/memU/blob/main/CONTRIBUTING.md) to get started.

## Upgrading from Cola or generic

The Cola and generic adapters and their `memu-cola` / `memu-agent` commands have
been removed. Before upgrading, use the previous installation to print the
applicable `memu-cola docs uninstall` or `memu-agent docs uninstall` guide and
follow it. Remove only confirmed integration-owned schedules, retrieval
instructions and skills; preserve user edits, shared memory, configuration and
other hosts' tooling. Package upgrades do not clean up these integrations, so
leftover tasks and instructions will invoke missing commands. If already
upgraded, restore the previous package version to complete cleanup first.

## Install and uninstall

Codex, Claude Code, pi, and Hermes provide direct commands:

| Host | Install | Uninstall |
| --- | --- | --- |
| Codex | `memu-codex install` | `memu-codex uninstall` |
| Claude Code | `memu-claude-code install` | `memu-claude-code uninstall` |
| pi | `memu-pi install` | `memu-pi uninstall` |
| Hermes | `memu-hermes install` | `memu-hermes uninstall` |

The installer configures the backend and host integration. Uninstall preserves settings and memory. Follow the terminal prompts to complete each operation.

For other hosts, ask an agent to follow their guides. For example, Cursor:

```sh
memu-cursor docs install
memu-cursor docs uninstall
```

`docs install` / `docs uninstall` only print instructions; they do not install or remove the integration. Ask your agent to read and execute those steps, including any scheduling setup the guide requires.

## Retrieval cleanup guarantees {#retrieval-cleanup}

Codex, Claude Code and pi uninstall commands remove their current hooks/extension
and the owned retrieval instruction/skill at the host's default paths. pi checks
both `AGENTS.md` and `AGENTS.override.md`. Use the same host home/profile as the
installation. For custom historical paths, preview
`remove-instruction --path <file> --skills-dir <dir> --dry-run`, then apply after review.

Skill installation and refresh write `.memu-owned.json` beside `SKILL.md`, recording
the host and a fingerprint of the installed text. An unchanged recorded skill can
be cleaned up after package or server-template changes without a version-by-version
migration. User edits, extra files, links and invalid records stop cleanup with a
diagnostic. Older skills without a record are removed automatically only when
recognized as the packaged content; other old copies need ownership review. Do
not delete an ambiguous directory to bypass this check.

Historical schedules still need the checks in `docs uninstall`. The command alone
does not enumerate all OS/native schedulers or discover every project/profile.
Report unresolved entries before claiming complete removal. Memory, shared
configuration and unrelated integrations are preserved. Start a fresh session,
or `/reload` pi, to unload previously loaded instructions/extensions.

## Hooks and activation

See [Retrieval and injection](retrieval.md) for the trigger/delivery comparison and result format, then open your host's page above for its exact sequence. [Configuration](../reference/configuration.md) covers shared TOML settings, query extraction and score cutoffs.

Codex uses an asynchronous submit hook; Claude Code uses `asyncRewake`; pi uses an input extension and steer messages. Their initial responses can begin before retrieval finishes. Query extraction defaults off. Hermes retrieves on demand, while Cursor, OpenClaw and WorkBuddy use standing instructions to ask the agent to retrieve before answering.

The host can use a model to prepare memory or optionally extract a query. `MemoryService` itself remains embedding-only. Recording and retrieval have separate lifecycles; registration does not prove memory processing or context delivery.

After installing pi, run `/reload` or open a new session. After installing Claude Code hooks or changing standing instructions, open a new session. Verify actual host execution separately from local registration. Capabilities vary by host, OS, and version; check the [repository support matrix](https://github.com/XnneHangLab-Mirror/memU/blob/main/README.md#agent-support) for recorded platform limitations.

## Manual retrieval

```sh
memu-pi retrieve "What do we know about this repository?"
```

Host output contains up to five self-contained `hits` and independent `resources`. Hits combine matched text with source metadata and a local mirror path or inline content. Database IDs and scope metadata are omitted from the agent-facing output.

If a backend check succeeds but the agent receives no context, follow [Troubleshooting](../troubleshooting/index.md).
