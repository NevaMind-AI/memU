# ADR 0004: Use Markdown Repositories for Context Harness and Skill Evolution

- Status: Accepted
- Date: 2026-06-04

## Context

memU needs a mode for agents that starts from a user-provided folder rather than an application event stream.

That folder can contain text, code, logs, conversations, images, audio, video,
PDFs, office documents, and unknown binary files.

The resulting memory should be inspectable by humans, portable across tools,
resilient to file changes, and directly usable as agent context.

The system also needs a way for agents to improve reusable skills over time.
Skill updates should be traceable to raw execution evidence, while durable
promoted skills should be editable by humans and survive re-extraction.

## Decision

Add a Markdown-backed context harness layer alongside the existing `MemoryService` workflows.

- Preserve the uploaded evidence under `raw_data/`
- Store generated memory in `memory.md` and `memory/`
- Store persona, tone, and language-style signals in `soul.md` and `soul/`
- Store reusable skills, workflows, and tool-use lessons in `skill.md` and `skill/`
- Track source hashes, sidecars, evidence paths, and generated entries in `.memu/manifest.json`
- Cache per-source evidence in `.memu/derived/`
- Persist repository-local, non-secret harness defaults in `.memu/harness.json`
- Allow explicit source-relative exclude globs and `.memuignore` files for noisy files while applying no default excludes
- Remove stale generated evidence when source files disappear from the current folder snapshot
- Replace only generated blocks marked by memU comments, preserving manual Markdown outside those blocks
- Treat sidecar files such as `image.caption.md`, `audio.transcript.txt`, and
  `report.summary.md` as semantic evidence for paired non-text sources
- Treat structured sidecars such as `image.metadata.json` and `video.frames.jsonl`
  as paired multimodal evidence instead of independent source files
- Provide context packs as Markdown, system prompts, chat message lists, and safe message injection helpers
- Allow CLI context outputs to be written as files for downstream agent harnesses
- Allow per-bucket context character limits for predictable `memory`, `soul`, and `skill` budgets
- Record skill traces under `raw_data/skill_traces/` so normal folder compilation can re-extract them
- Suggest skill promotions by grouping trace lessons, actions, tools, and outcomes without writing by default
- Promote durable skills into manual `skill.md` notes and stable `skill/promoted/*.md` cards
- Deduplicate promoted skill context by preferring full `skill/promoted/*.md` cards over their `skill.md` index snippets
- Generate a non-overwriting `AGENTS.md` bootstrap file so local agents can discover harness conventions
- Let command-line flags override `.memu/harness.json`, and let the config file override built-in CLI defaults for both `memu-harness` and `memu-context`

ADR 0005 narrows the write path for generated self-evolution: raw traces,
creator feedback, uploads, and observations are now converted into
`EvolutionInstruction` records and reviewed `PatchProposal`s before approved
changes update generated Markdown blocks.

`ContextHarness` is the composition API for this mode. It binds a raw-data
folder to a Markdown memory repository and coordinates scaffold, ingest, status,
context assembly, skill traces, promotion, and watch mode.

The harness config intentionally excludes API keys, LLM provider settings, and
user scope because those values are environment or request specific.

## Consequences

Positive:

- memory repositories are human-readable and version-control friendly
- raw evidence, generated summaries, and manual edits have clear ownership boundaries
- folder changes can be incrementally re-extracted without rewriting user notes
- multimodal files can carry local semantic evidence through sidecars even without an LLM
- context can be injected directly into chat-completion style agents
- skill evolution has both raw trace evidence and stable promoted skill cards
- repeated CLI runs can share repo-specific defaults without storing secrets

Negative:

- Markdown parsing and generated-block preservation require careful delimiter discipline
- local extraction is heuristic unless a multimodal/document-capable `MemoryService` is supplied
- sidecar naming conventions must be documented and consistently followed
- Markdown repositories add a second memory surface alongside database-backed storage
- repeated promotion and manual edits need merge rules to avoid losing provenance
