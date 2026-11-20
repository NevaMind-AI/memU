# ADR 0024: Empty memory bodies through commit and local mirroring

- Status: Proposed; design review
- Task: MEM-13
- Related: [ADR 0012](0012-cloud-backed-agentic-backend.md), [ADR 0014](0014-paginated-list-all-recall-files.md)
- [中文](0024-memory-clearing-through-commit.zh.md)

## Goal and scope {#goal}

Reduce obsolete memory content in segment retrieval and local files using the existing `commit_results` workflow. Submit an empty body for a memory, retain the database file record, remove its segments and omit its local Markdown mirror.

The service keeps its three entry points and embedding-only architecture. Shared service flow remains in `AgenticMixin`; local and hosted repositories retain their own models and scope responsibilities. The initial change applies only to `memory`. PR #814 is closed.

## Current behavior {#evidence}

Source baseline: memU runtime `12d144c`; hosted checkout `cca499a` pins `memu-cli==0.11.0b3`. MEM-16 reported isolated inmemory/fake-embedding and temporary-file checks; MEM-13 inspected the source. These observations do not establish live Cloud behavior.

| Path | Observed behavior |
| --- | --- |
| `src/memu/app/agentic.py` | Existing memory content is stripped and updated; empty content produces no segment texts, so reconciliation removes old segments. The file record remains. Empty description does not clear an existing description; a file vector may remain. |
| Same path: skill generation | Empty skill content still generates a name/description segment. |
| `src/memu/hosts/bridging/recall_files.py` | The writer creates frontmatter even when the body is empty. |
| `src/memu/hosts/bridging/pipeline.py` | Prepare writes listed files. Commit submits changed files and snapshots the directory after backend success. |
| `src/memu/hosts/retrieval.py` | Returned files are materialized and their paths exposed. |
| `src/memu/hosts/bridging/manifest.py` | Missing files are ignored by the content diff. |

## Intended behavior {#behavior}

1. Submit the targeted memory through the existing commit payload, with its identifying metadata and empty or whitespace-only body. Preserve current scope/name resolution and ordinary commit semantics.
2. After successful commit, its body is empty and its old segments are removed. The database record and metadata remain visible to list/Dashboard. Current segment retrieval no longer hits that memory once segment removal succeeds.
3. Classify empty memory by parsed body text (`body.strip()`), not Markdown byte size. Do not create a frontmatter-only mirror. Remove an existing mirror at the normal target path when processing an explicitly empty memory; merely skipping a write would leave old content behind.
4. Apply the empty-memory materialization rule to prepare and retrieval, and remove the submitted empty mirror after backend commit succeeds. Retrieval must not advertise a path that was not materialized. Absence from a list or retrieval result does not itself identify a file for removal.
5. Keep the existing silent overwrite behavior, snapshot/session flow and error propagation. A backend exception does not reach post-success cleanup. Filesystem failures follow ordinary host error handling.
6. A missing local file or empty directory still does not submit a backend clear. Skill and resource behavior remain unchanged.

Database identity retention is not body history retention. Metadata and possibly file-level vectors remain; the intended effect is segment-retrieval exclusion and removal of local empty shells. Existing Postgres method-level commits do not establish whole-batch atomicity. This proposal adds no recovery guarantee.

## Implementation plan {#implementation}

| Commit | Scope | Acceptance |
| --- | --- | --- |
| 1. Characterize commit | Focused synthetic-data tests for existing memory empty/whitespace content, retained metadata, segment removal and scope/track isolation. | Establish current behavior without changing payload semantics; distinguish Local results from hosted pinned-version evidence. |
| 2. Apply empty-memory mirror policy | Reuse existing writer/path logic; adapt prepare/retrieval callers for a skipped path and bridge commit for post-success removal of submitted empty memory mirrors. | No new shell; old target mirror removed; nonempty memory and skill keep current silent-write behavior; failed backend commit does not perform post-success removal. |
| 3. Verify integration | Test list/prepare, retrieval shaping and commit using isolated data; run relevant backend/host regression checks. | Body/segment state and mirror results agree; missing local files do not clear backend records; manifest/session behavior stays as before. Verify Cloud separately before making Cloud claims. |

Current source treats omitted/null content as empty. Changing that behavior, creation semantics or name resolution requires a separate compatibility decision; it is not included in this implementation plan.

## Impact and validation {#validation}

An unchanged-description clear with no new segment text needs no new content embeddings. Existing per-track listing and per-segment deletion costs remain. Local materialization adds an empty-body branch and may unlink the normal mirror path. No conflict tracking, new manifest format or synchronization protocol is needed for this scope. Measure relevant checks rather than claiming a speedup.

Use synthetic scoped records and temporary directories. Cover empty/whitespace memory, retained ID/description, zero segments and retrieval exclusion, old mirror removal, no new empty shell, no nonexistent retrieval path, unchanged skill/nonempty writing, backend failure and missing local files. Real Postgres and hosted behavior need their own isolated verification; inmemory tests do not establish their atomicity.

## Delivery {#delivery}

PR #816 currently contains design documentation. Implement only the agreed behavior in small commits, update both languages with test results, and preserve repository scope-validation and applicable backend-parity requirements. No production memory cleanup, release or deployment is authorized by this document.
