# 0022: Hermes Plugin Hooks for Retrieval and Memorization

Status: Accepted

Hermes needs the CLI-managed installation and removal flow already used by pi.
Its native plugin API exposes `pre_llm_call` for context injection and
`on_session_end` for completed-turn notification across CLI and gateway sessions.

Install a managed `memu-memory` plugin under the active Hermes home. Bind it to
the installing Python runtime and memU host directory. Delegate activation and
removal bookkeeping to Hermes's native plugin commands, with ownership and
symlink checks before modifying files. Preserve other plugins, user instructions,
sessions and shared memory. Reuse the shared backend installation lifecycle.

Retrieval runs in a bounded subprocess before inference. Successful turn
completion starts a detached prepare/agent/commit worker with the existing
whole-pass lock and 30-minute cooldown. Mark worker launches and remember their
Hermes session IDs so the pipeline does not mine its own sessions. Service code
remains embedding-only; Hermes executes the headless memory jobs.

The initial implementation uses a bounded prompt prefix for retrieval and the
configured Hermes default model/provider for memory processing. Plugin readback
and backend checks do not prove model connectivity. Existing scheduled tasks and
standing retrieval instructions require separate inspection and cleanup.

References: [pi hooks](0021-pi-extension-hooks.md),
[Hermes event hooks](https://hermes-agent.nousresearch.com/docs/user-guide/features/hooks).
