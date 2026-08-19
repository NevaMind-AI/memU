# ADR 0018: Mine Claude Cowork Through the Claude Code Bridge

- Status: Accepted
- Date: 2026-08-14
- Builds on: ADR 0010, ADR 0015

## Context

Claude Cowork stores one user-visible Recent workspace in
`local_<session-id>/audit.jsonl`. A file contains the outer Cowork ID plus internal
agent IDs and audit/lifecycle records. Claude Code Desktop metadata is already
covered by `~/.claude/projects`, so treating it as another input would duplicate
history. Windows field evidence confirms Cowork's audit directory is separate.

## Decision

Cowork is a distinct read-only `CoworkTranscriptSource`, composed into the existing
`memu-claude-code` bridge rather than exposed as a second binary or schedule.

Discovery is platform-specific rather than one mixed list. Windows checks existing
Claude Desktop roots under `%APPDATA%\Claude`, `%LOCALAPPDATA%\Claude-3p`, and
MSIX `Claude_*` roaming roots. macOS checks
`~/Library/Application Support/Claude`; Linux checks
`${XDG_CONFIG_HOME:-~/.config}/Claude`. These conventional macOS/Linux roots are
enabled for staging and remain subject to correction from real-machine field
reports.

`MEMU_COWORK_ROOTS` is the staging and nonstandard-install escape hatch: a
platform-path-separator-delimited list of Claude Desktop data roots. A declared
value replaces automatic discovery, nonexistent entries fail visibly, and an
empty value disables discovery. Constructor
roots remain the highest-priority test seam. Every selected root is an independent
scan region, so an unchanged session ends only its own newest-first region and
cannot hide Code history or another Desktop root.

The outer `local_<id>` directory is the session boundary and session identity.
Record-level IDs are execution details and never split the session. The source
normalizes only user/assistant message records, removes audit transport data and
internal identifiers, drops lifecycle/result/system records and `isReplay` user
copies, and reuses Claude content-block classification. It never opens `.audit-key`.

The existing Claude Code self-skip remains unchanged: scheduled `claude -p` runs
are Claude Code sessions under `~/.claude/projects`; Cowork is not assigned an
unverified environment identity contract.

## Consequences

- One schedule, working tree, CLI, and memory backend serve Claude Code and Cowork.
- Cowork memories are available through the shared store to all integrated hosts.
- Cowork parsing is isolated from Claude Code parsing, so protocol drift is pinned
  by fixture tests without widening the existing reader.
- Platform providers keep unrelated OS paths out of the scan; staging feedback can
  refine one provider without changing the reader or bridge.
- Explicit roots let testers and nonstandard installations run immediately without
  patching Python or mixing staged data with automatically discovered history.
