# ADR 0005: Gate Self-Evolution Through Instructions and Reviewed Patches

- Status: Accepted
- Date: 2026-06-04

## Context

Markdown-backed context harnesses can ingest agent logs, creator feedback,
uploaded files, observations, sidecars, and skill traces. Those raw sources are
valuable evidence, but letting them rewrite `memory.md`, `soul.md`, or
`skill.md` directly creates a self-contamination risk: noisy execution logs or
unreviewed model output can become durable context and then influence the next
context pack.

The self-evolve path needs traceability and review without breaking the
existing folder compiler ergonomics.

## Decision

Raw evidence must pass through this chain before it can update long-term
Markdown context:

```text
raw_data/
  agent logs
  creator feedback
  uploaded files
  observations
      -> Evidence extraction
      -> EvolutionInstruction
      -> PatchProposal
      -> ReviewDecision
      -> approved patches update memory.md, soul.md, skill.md
```

An `EvolutionInstruction` records the structured intent:

- `target`: `memory`, `soul`, or `skill`
- `operation`: `add`, `update`, or `delete`
- `reason`
- `evidence`
- `priority`
- `confidence`

Each instruction becomes a `PatchProposal`. The review gate evaluates
traceability, confidence, conflict markers, and patch safety. Approved proposals
are applied to generated Markdown blocks and manifest entries. Proposals that
need creator review remain auditable and do not update long-term context.

The compiler writes audit artifacts under `.memu/evolution/`:

- `instructions.jsonl`
- `patch_proposals.jsonl`
- `review_decisions.jsonl`
- `latest.json`

`FolderMemoryCompilerConfig.evolution_review` controls whether the review gate
auto-approves safe proposals or requires creator review. The CLI exposes this
with `--require-creator-review` and `--min-evolution-confidence`.

## Consequences

Positive:

- raw logs and feedback cannot directly pollute durable context
- every generated memory/soul/skill update has a structured provenance chain
- creator-review workflows can block writes while preserving proposals
- deleted sources also produce traceable delete proposals
- existing folder compiler calls still work because safe proposals auto-approve by default

Negative:

- manifest records are larger because they include per-source evolution audits
- manual-review mode can leave sources pending and therefore re-propose changes
- lightweight local conflict detection is heuristic until an LLM-backed reviewer is added
