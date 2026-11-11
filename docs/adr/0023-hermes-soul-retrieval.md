# 0023: Hermes Retrieval Through a Managed SOUL.md Block

## Status

Accepted for the Hermes adapter. Supersedes the Hermes-specific hook integration
in ADR 0022; other host adapters retain their existing mechanisms.

## Context

Hermes queued plugin injection delivers retrieved references as a later turn,
which does not meet the desired task-continuation experience. Extraction and
live reload through Hermes Python internals also couple memU to host module
layout and version-specific APIs. On-demand retrieval can use the main agent's
understanding of the request and its ordinary CLI tool workflow.

## Decision

Install one complete, locally owned retrieval procedure in a managed SOUL.md
block. The agent decides whether missing historical information justifies a
search, forms the query, and calls `memu-hermes retrieve`. Greetings and
self-contained tasks normally need no search. Results remain reference data;
retrieval must not change the original task.

Resolve the current profile through memU's shared `hermes_home()` helper and the
HERMES_HOME environment passed by the host. Patch the file without importing or
executing Hermes Python modules. CLI availability is checked without a minimum
version gate. Existing memory-processing commands continue to use the Hermes CLI.

Install/uninstall verify legacy Windows schedule cleanup. A legacy managed memU
plugin is ownership-checked, removed with the Hermes CLI, and checked for absence.
Any migration error remains visible and fails the operation. Instruction updates
require a fresh session; legacy callbacks require a process restart. Local file
readback is not evidence of live gateway activation.

Hermes's instruction refresh uses the local on-demand policy so a remote shared
template cannot replace it with mandatory per-turn retrieval.

## Consequences

The installed retrieval procedure has one managed artifact and symmetric removal.
No host Python import exemptions or plugin-specific version requirement are needed.
Retrieval remains a tool call that the agent may await and the UI may show.
Autonomous discovery and recall coverage depend on the model and require ongoing
real-model evaluation. This installation does not schedule automatic memorization;
explicit bridging commands remain available. Linux/macOS legacy schedule cleanup
and Hermes native cron migration still require separate verification.
