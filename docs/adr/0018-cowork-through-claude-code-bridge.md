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

On Windows it discovers existing Claude Desktop roots under `%APPDATA%\Claude`,
`%LOCALAPPDATA%\Claude-3p`, and MSIX `Claude_*` roaming roots. Each root is an
independent scan region. An unchanged session ends only its own newest-first
region, so a known Code transcript cannot hide Cowork history or another Desktop
root.

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
- macOS/Linux root providers remain disabled until real-machine field evidence and
  sanitized fixtures establish their locations and layout.
