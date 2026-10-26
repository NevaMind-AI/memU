# ADR 0020: Extract Long Codex Submit Queries in the Host Adapter

- Status: Accepted
- Date: 2026-10-26
- Scope: Codex `UserPromptSubmit` automatic retrieval

## Context

Automatic retrieval previously embedded only the first 2,000 characters of a
submitted prompt. A long message can put its actual request after background or
pasted material, outside that prefix. Codex's asynchronous command hook allows
query preparation and retrieval to run while the primary agent starts its task.

## Decision

The Codex host adapter uses the original prompt up to 500 Unicode characters.
For prompts of 501–32,000 characters, it asks the existing Codex CLI to produce a
concise memory-search query from the full prompt, preserving relevant names and
constraints, including requests near the end.

The child runs with `exec --ephemeral`, hooks disabled, an empty notify command,
a read-only sandbox and low reasoning effort. It uses the user's existing Codex
model and authentication configuration. A JSON schema and local output checks
require a nonempty query of at most 500 characters.

Extraction has a 12-second timeout. Unavailable executables, failed or malformed
responses, timeouts and prompts exceeding the input budget fall back to the
existing 2,000-character prefix. Extraction and retrieval share a 43-second
working budget within the registered 50-second hook timeout. On extraction
timeout, the adapter terminates the child process tree and reaps the agent.

The adapter records query source, extraction status and stage timings in the
existing hook log. The retrieval command and `additionalContext` result format
remain the same. Model invocation stays in the host adapter; `MemoryService`
continues to perform embedding-only retrieval.

## Consequences

Long prompts can recover intent beyond the old prefix, at the cost of an extra
model request and later memory delivery. The 500-character threshold is an
initial heuristic, not a measured optimum. The input budget bounds characters,
not exact model tokens; provider context-limit errors use the same fallback.

Asynchronous delivery can affect subsequent model requests in the active turn
or a later turn. It cannot alter an in-flight request, and more relevant queries
do not guarantee useful memory exists. Short follow-ups still use their literal
text, and concurrent submissions retain the host's existing delivery behavior.
