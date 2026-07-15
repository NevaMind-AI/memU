"""Host adapters — memU as a sidecar to a desktop coding agent.

Distinct from :mod:`memu.integrations`, which holds *framework bindings* that a
user's own code imports in-process (LangGraph, …). A host adapter is the other
shape: memU runs *beside* an agent app, reads the session log that app writes,
and is driven by that app's scheduled tasks and hooks through its own console
script (``memu-codex``). Different consumer, different lifecycle, different
namespace.

Each host binds two seams (ADR 0008):

- **record** — a scheduled *bridging* task that mines the host's session log into
  durable memory. Its pipeline lives in :mod:`memu.hosts.bridging` and is shared
  by every host.
- **inject** — a standing instruction telling the agent to retrieve before it
  answers, plus the retrieval it names. Both halves are host-agnostic and live in
  :mod:`memu.hosts.instruction` and :mod:`memu.hosts.retrieval`; a host supplies
  only the path to its global instruction file (Codex: ``~/.codex/AGENTS.md``).

Adding a host means implementing :class:`memu.hosts.base.TranscriptSource` (where
its sessions live, how its records are shaped) plus a thin CLI that registers the
two shared seams. It must not mean copying the pipeline — or the instruction text.
"""
