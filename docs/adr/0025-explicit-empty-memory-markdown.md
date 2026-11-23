# ADR 0025: Explicit Acknowledgement for Empty Memory Markdown

- Status: Proposed; implemented for review
- Task: MEM-9; related: MEM-13
- Extends: [ADR 0024](0024-memory-clearing-through-commit.md)
- [中文](0025-explicit-empty-memory-markdown.zh.md)

## Goal {#goal}

Prevent an accidentally blank Markdown body from clearing a stored memory. Make intentional clearing explicit and restoration automatic.

## Decision {#decision}

The shared Markdown reader used by host bridging commit and developer `memu memorize commit` requires exactly one literal `empty: true` frontmatter field when a memory body is empty after stripping whitespace:

```markdown
---
name: reading-preference
description: Reading preferences
empty: true
---
```

Missing, false, quoted, or duplicate acknowledgements reject the submission before calling the backend. Keep the existing name and description. An ordinary zero-byte file still fails name validation. Missing local files do not submit clears. Skill files retain their existing behavior.

A non-empty body always restores normal submission, including when the frontmatter still contains an `empty` field. After successful submission, the client removes that field atomically before taking the new manifest snapshot. The acknowledgement is therefore consumed: a subsequent blank body needs explicit acknowledgement again. Backend failure preserves the file, acknowledgement and pending run state for retry.

The marker is local Markdown metadata and is not included in backend payloads. Direct `commit_results` and JSON `memu commit` retain their existing empty-content semantics. Repository schemas, backend parity and Cloud APIs are unaffected. The backend record and metadata remain after clearing; the successful Markdown commit removes its local empty mirror as in ADR 0024.

## Agent guidance {#guidance}

Memory jobs append the submission contract after rendering the selected template, including remote and cached templates. Agents can clear intentionally by adding the acknowledgement and removing the body, or restore by simply writing a non-empty body.

## Validation {#validation}

Tests cover blank and whitespace bodies, invalid acknowledgements, skill isolation, local-only payloads, automatic restoration and acknowledgement removal, subsequent accidental blanks, backend failure and retry, and both Markdown commit entry points. Checks use synthetic records and temporary directories; this patch does not exercise production memories or prove backend transaction atomicity.
