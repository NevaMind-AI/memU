ADR 0010: Multi-Host Adapters — Claude Code, Cursor, OpenClaw, and Hermes

- Status: Accepted
- Date: 2026-07-16
- Builds on: ADR 0008 (two integration surfaces), ADR 0009 (packaging, CLI seam, one config
  loader)
- Scope: adding four host adapters beyond Codex, and the two pieces of shared structure that
  shipping a second host forced: a common CLI builder, and per-host working trees. It does
  **not** revisit the pipeline, the seams, or the config decisions of 0008/0009.

## Context

ADR 0009 closed with a claim and an IOU. The claim: "a second host is a `TranscriptSource`
and a CLI, not a forked pipeline." The IOU: the working directories (`~/.memu/jobs`,
`~/.memu/sessions`, the touched-file log) are shared and wiped per run — "two hosts' bridging
tasks running at the same time would race. Fine while Codex is the only host; must be settled
before the second one ships."

Four hosts now ship at once: **Claude Code**, **Cursor**, **OpenClaw**, and **Hermes Agent**.
Each was located empirically (inspecting a live machine and, for OpenClaw and Hermes, the
hosts' own source) rather than from documentation alone:

| Host | Session log | Container | Record shape |
| --- | --- | --- | --- |
| Codex | `~/.codex/sessions/**/*.jsonl` | JSONL per session | `{timestamp, payload: {type, role, …}}`; `type: message` (user/assistant) vs `function_call`/`function_call_output` |
| Claude Code | `~/.claude/projects/<escaped-cwd>/<session-uuid>.jsonl` (subagent transcripts in per-session subdirs) | JSONL per session | `{type: user\|assistant, timestamp, message: {role, content}}`, one content block per record: `text` / `tool_use` / `tool_result` / `thinking`; plus non-message noise types (`queue-operation`, `attachment`, `system`, `pr-link`, `last-prompt`) and `isMeta` user records |
| Cursor (Agent/CLI) | `~/.cursor/projects/<escaped-cwd>/agent-transcripts/<id>/<id>.jsonl` | JSONL per session | `{role, message: {content: [blocks]}}`; `text` and `tool_use` blocks, often in one record; **no timestamps**. The IDE's Composer chats live in the editor's `state.vscdb` SQLite and are out of scope |
| OpenClaw | `~/.openclaw/agents/<agentId>/sessions/<sessionId>.jsonl` (`-topic-<threadId>` suffix for topic sessions; `sessions.json` index alongside; root moves with `OPENCLAW_STATE_DIR`) | JSONL per session | parent-linked entry tree: `{type: session\|message\|compaction\|custom…, id, parentId, timestamp, message: {role, content}}`; roles `user`/`assistant`/`toolResult` |
| Hermes Agent | `~/.hermes/state.db` (moves with `HERMES_HOME`; `~/.hermes/sessions/saved/` holds only manual snapshots) | **SQLite**, WAL mode | `sessions` + `messages` tables; OpenAI-shaped rows: `role` (`system`/`user`/`assistant`/`tool`), `content`, `tool_calls`, `tool_call_id`, epoch-seconds `timestamp` |

And the inject seam's landing file per host:

| Host | Instruction file | Why |
| --- | --- | --- |
| Codex | `~/.codex/AGENTS.md` | global, loaded every session (ADR 0009) |
| Claude Code | `~/.claude/CLAUDE.md` | the global memory file, loaded in every project |
| Cursor | `./AGENTS.md` (per project) | Cursor's CLI honors no global instruction *file*; User Rules are IDE settings out of a CLI's reach |
| OpenClaw | `~/.openclaw/workspace/AGENTS.md` | the workspace file loaded at the start of every session |
| Hermes | `~/.hermes/SOUL.md` | the one file loaded from `HERMES_HOME` regardless of cwd; project files (`.hermes.md`, `AGENTS.md`) would miss sessions started elsewhere |

Two of the four break assumptions Codex allowed:

- **Hermes's log is not files.** The `TranscriptSource` defaults (rglob, line reads, string
  timestamps) assume JSONL-on-disk. 0009's seam anticipated this ("a host with a different
  container overrides `discover`, `read_records`, `timestamp`"), but no host had exercised it.
- **Claude Code's roles lie.** A tool result is logged as a *user*-typed record. Any
  classification keyed on role alone would put tool output in the conversation transcript the
  memory job reads.

## Decision

### 1. The host CLI is built from a declaration, not copied

Five binaries share one verb set — `retrieve`, `install-instruction`, `prepare`, `commit`,
`verify-resources`, `doctor`, `docs` — because the behavior behind every verb is host-agnostic.
So the parser and handlers move to `memu.hosts.host_cli`, built from a `HostSpec`: the host id,
the session-log default, the instruction-file default, and the docs package. A host's `cli.py`
is now the spec plus `main`, ~40 lines; `memu-codex` is rebuilt on the same spec with byte-
identical behavior.

The standing-instruction text (ADR 0009's managed block) is likewise parameterized on the host
binary rather than hardcoding `memu-codex`; each host's block names its own `retrieve`, and the
per-binary begin-marker means two hosts pointed at one file manage two independent blocks.
Codex's rendered block is unchanged, so already-installed markers still match and upgrade in
place.

What stays per host is exactly what 0009 predicted — a `TranscriptSource` — plus the two paths
(session log, instruction file) and the packaged guides. Cursor's `discover` is narrowed to
`*/agent-transcripts/**/*.jsonl` (the project dirs also hold canvases and terminal logs);
Hermes overrides the container seam wholesale: sessions are *virtual paths* keyed by session
id, `read_records` serializes message rows to JSON lines ordered by insertion id, and
`discover` orders by last activity so the manifest's early-stop stays sound. The database is
opened **read-only** — the bridging task must never contend for Hermes's WAL write lock. The
line-count cursor carries over untouched: message rows are append-only per session, so "lines
seen" is "rows seen."

### 2. Working trees are per host; the store stays shared

0009's open issue is settled by removing the sharing, not by locking: every host's `Layout`
gets its own base directory, `~/.memu/hosts/<host>/`, holding its jobs, sliced sessions,
mirrors, manifests, and touched-file log. Concurrent bridging runs of different hosts touch
disjoint trees. **Codex keeps `~/.memu`**: its job-file paths are baked into users' already-
scheduled task prompts (the exact fragility 0009's `PATH`-command decision was protecting
against — the prompt references `~/.memu/jobs/*.txt` literally), and breaking every existing
install to make five directories symmetrical is a bad trade. The asymmetry is recorded in
`HostSpec.base_dir` with a comment saying why.

What is *not* per host: `~/.memu/config.env` and the store behind `MEMU_DB`. That is the
point of the whole exercise — a session mined from Claude Code tonight is retrievable from
Cursor tomorrow. The install guides instruct an agent that finds an existing `config.env` to
reuse it as is, because a second host writing a second store/provider would silently split the
embedding space (0009's core invariant).

### 3. Classification is by record shape, not role

Each host's `classify` encodes its log's actual semantics, pinned by tests with hand-written
records in the host's real shape:

- **Claude Code**: block type decides — `text` (or a raw-string user message) is conversation;
  `tool_use`/`tool_result` are tool records regardless of the wrapping role; `thinking` blocks,
  `isMeta` user records, and all non-message types are dropped.
- **Cursor**: a record with prose is conversation even when it also carries the `tool_use`
  blocks it narrates; only bare tool-block records go to the tool transcript. No timestamps
  exist, so the manifest records `null` and the line count alone drives incrementality.
- **OpenClaw**: `type: message` with role user/assistant is conversation, role `toolResult` is
  a tool record; session headers, compaction summaries, and extension entries are dropped.
  Timestamps may be ISO strings or epoch millis; both normalize.
- **Hermes**: role `tool`, and assistant rows carrying only `tool_calls`, are tool records;
  user/assistant rows with content are conversation; `system` rows are dropped. Epoch-seconds
  timestamps normalize to ISO.

## What this changes

- Four new console scripts — `memu-claude-code`, `memu-cursor`, `memu-openclaw`,
  `memu-hermes` — each with packaged `INSTALL.md` / `BRIDGING_TASK.md` guides printable via
  `<binary> docs`, alongside the unchanged `memu-codex`.
- `memu.hosts.host_cli` (new): `HostSpec` + the shared parser/handlers. `codex/cli.py`
  shrinks to its spec; its public names (`build_parser`, `AGENTS_MD`, `HOST`,
  `VERIFY_COMMAND`) survive.
- `memu.hosts.instruction`: `INSTRUCTION`/`BEGIN` constants become `instruction(binary)` /
  `begin(binary)` templates; `install`/`patch`/`register` take the binary.
- `memu.hosts.base.TranscriptSource` gains `exists()` (default: root is a directory) so a
  SQLite-backed host can gate `prepare` on its file instead.
- New host packages: `hosts/claude_code`, `hosts/cursor`, `hosts/openclaw`, `hosts/hermes` —
  each a `sessions.py`, a spec-sized `cli.py`, and the two guides.

## Consequences

Positive:

- The 0009 claim is now demonstrated: four hosts, zero pipeline forks, and the next host is a
  `classify` method, two paths, and two markdown files.
- Concurrent bridging across hosts is safe by construction (disjoint trees), with no locking
  protocol to get wrong.
- One instruction text and one CLI surface to improve; all five binaries pick up fixes at once.

Negative / costs:

- Codex's `~/.memu` vs everyone else's `~/.memu/hosts/<host>` is a visible asymmetry, carried
  for compatibility. A future major release could migrate Codex in.
- The recall-file mirror is written once per host per run instead of once per machine —
  redundant disk writes, accepted for isolation.
- Cursor's inject seam is per project (no global file), so its instruction install is a
  per-project step the guides must (and do) call out.
- Host log formats are observed, not contracted. OpenClaw already has a SQLite session target
  behind a flag; if it becomes the default, that host needs the Hermes treatment. The
  per-host fixture tests localize such breaks.

## Open issues (deferred)

- **Same-host concurrency.** Two bridging runs of the *same* host still race on that host's
  tree; scheduled tasks make this unlikely, and per-run lock files remain available if it
  bites.
- **IDE-container hosts.** Cursor's Composer history (`state.vscdb`) and any host whose log
  lives inside an editor's private state would need the SQLite treatment plus a stability
  story for schema drift; not attempted.
- **Session-dir env vars.** OpenClaw (`OPENCLAW_STATE_DIR`) and Hermes (`HERMES_HOME`) can
  relocate their logs; the adapters take `--session-dir` rather than reading the host's env,
  keeping the contract explicit. The guides say when to pass it.

## Related ADRs

- Builds on `docs/adr/0008-two-integration-surfaces-hooks-and-api.md` — each new host binds
  the same two seams.
- Builds on `docs/adr/0009-codex-packaging-cli-and-config.md` — settles its "concurrent
  hosts" open issue via per-host working trees; keeps its distribution, CLI-command, and
  config decisions unchanged.
