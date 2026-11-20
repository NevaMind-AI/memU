# ADR 0025: Explicit memory clearing through commit and safe local mirrors

- Status: Proposed; contract review before implementation
- Task: MEM-13; design handoff from MEM-16
- Related: [ADR 0012](0012-cloud-backed-agentic-backend.md), [ADR 0014](0014-paginated-list-all-recall-files.md)
- [中文](0025-memory-clearing-through-commit.zh.md)

## Goal and boundary {#goal}

Reduce obsolete memory content in segment retrieval and managed local files through the existing `commit_results` workflow. The initial scope is an explicitly targeted, existing `memory` file: clear its body, retain its database identity, reconcile its segments and safely remove its empty local mirror. This is a proposed contract, not an implemented lifecycle feature or a recoverable-delete guarantee.

The common service flow remains `AgenticMixin`. memU supports caller-managed user/agent scopes, including multiple users; the hosted product additionally binds authenticated organization/project tenants and uses distinct UUID models, segment identity/position constraints, audit and transaction ownership. Their repositories remain independently owned.

The public surface remains `list_all_recall_files`, `progressive_retrieve`, `commit_results`; the service remains embedding-only. `skill` and `resource` require separate decisions. PR #814 remains paused.

## Current evidence {#evidence}

Source baseline: memU runtime `12d144c`, documentation head `fbeea7a`; hosted checkout `cca499a`, pinning `memu-cli==0.11.0b3`. MEM-16 reports isolated inmemory/fake-embedding and temporary-file checks. MEM-13 re-read the following source paths; those reports are not live Cloud verification or a new cross-backend test result.

| Path | Observed behavior |
| --- | --- |
| `src/memu/app/agentic.py`: planning and segment reconciliation | Body text is stripped. Explicit empty content on an existing memory produces no segment texts and deletes stale segments after updating the file. The file record remains. |
| Same path: description update | An empty description does not clear an existing description; unchanged description can retain the file vector. Current segment-based retrieval does not directly retrieve a file using that vector. |
| Same path: skill segment generation | Empty skill content still generates a name/description segment. |
| `src/memu/hosts/bridging/recall_files.py` | The writer emits frontmatter even for an empty body; the reader parses body separately and requires a name. |
| `src/memu/hosts/bridging/pipeline.py`; `src/memu/hosts/retrieval.py` | Prepare lists and writes files; retrieval also materializes returned files. A writer-only skip cannot remove an old mirror. Commit advances snapshots/session state after backend success. |
| `src/memu/hosts/bridging/manifest.py` | Missing paths are not submitted as content updates. |

Current source treats omitted/null content as empty too. That is not evidence of deliberate clearing intent: the explicit-input contract below must be reviewed against callers before implementation.

## Proposed commit contract {#commit}

1. A deliberate clear names an existing memory in a validated scope and explicitly supplies `content: ""` (whitespace-only body is equivalent). A missing local file, empty directory or incomplete manifest supplies no clear intent. Keep identifying frontmatter when submitting an edited mirror.
2. Resolve the exact target using current scope/track/name rules. Review canonical-name and legacy collisions, unknown targets, and concurrent creation rather than silently creating a placeholder for a supposed existing target.
3. On confirmed success, persist an empty body, preserve file identity and remove its stored segments. Repeated clears should converge to this state. Other scopes/tracks stay unchanged.
4. Retain the existing description-update semantics for this proposal: `description: ""` does not mean erase old metadata. Name, description, timestamps and possibly a file-level vector remain; list/Dashboard can still show the record. This achieves segment-retrieval exclusion, not invisibility, historical erasure or storage deletion.
5. Decide omitted/null content handling explicitly before shipping. Inventory existing clients and choose compatible validation or an explicit-call convention; do not reinterpret every incomplete payload as deliberate clearing.

## Safe local mirror contract {#mirrors}

Use parsed body text (`body.strip()`), not total Markdown byte length, to classify an empty memory. Prepare and retrieval must follow the same policy and not advertise a path that was not materialized. Nonempty memory and skill behavior stays supported.

An authoritative empty memory should not create a Markdown shell. If an old path exists, remove it only when ownership, target identity and unchanged local bytes are proven. A valid managed baseline can establish that proof; filename or presence under a directory alone cannot. Missing/stale manifests, path collisions, symlinks, wrong roots or unknown ownership must preserve the file and report the uncertainty/conflict.

For a clear submitted from a local edit, distinguish the submitted bytes from the last committed baseline: the clear itself is an uncommitted edit until backend success. Capture and recheck the submitted fingerprint; preserve any later local edit. For an empty record observed by prepare/retrieval, compare against a trusted committed baseline. A hash check alone is not a lock: the implementation must address races between check and unlink/write, including another host process.

Backend failure must not trigger mirror cleanup or successful snapshot/session advancement. If the backend succeeds but local cleanup fails, report backend success separately from local reconciliation failure, preserve retry information and do not claim fully synchronized success. Define the manifest/session ordering and crash recovery before implementation; they are not currently an atomic filesystem transaction.

## Recovery, concurrency and partial failure {#failure}

Retaining identity does not retain old body text. Restoring content requires a known prior copy/history/backup, explicit scoped recommit and segment rebuilding. No automatic restore API or retention period is promised. Product audit before-images are not a verified recovery guarantee.

Both current Postgres paths use independent repository commits; shared mixin usage does not establish whole-batch atomicity. Failure can leave an empty file with stale segments or a partially applied batch. A failed attempt must be read back and reconciled/retried; it cannot be reported as successful retrieval exclusion. SQLite/inmemory guarantees must not be generalized to Cloud.

Before implementation decide how a clear conflicts with a concurrent content update, how exact targets are established and how partial completion is reported. Existing payloads do not establish a cross-backend compare-and-swap revision contract. Review last-writer behavior versus explicit conflict detection with the user. Test retries and avoid masking a newer write with an old retry. Whole-repository extraction is not required to expose and solve these specific risks.

## Impact and acceptance {#validation}

Expected effects are fewer searchable segments and fewer materialized memory files; retained records still cost listing bandwidth and storage. Segment cleanup cost scales with target segments; current planning also lists files per track. Mirror ownership checks add local I/O and possibly synchronization. No latency or cost improvement is measured yet; record provider calls, DB query/delete counts and mirror work for isolated small/large targets.

| Check | Required result |
| --- | --- |
| Explicit empty/whitespace body | Existing scoped memory identity retained, body empty, segments zero, current segment retrieval cannot hit it |
| Scope/track and metadata | Other records unchanged; retained metadata/list visibility documented; skill/resource behavior preserved |
| Missing files/empty directory/incomplete payload | No inferred clear from absence; omitted/null behavior explicitly agreed and tested |
| Prepare and retrieval | No new empty shell or nonexistent advertised path; managed unchanged old mirror safely reconciled |
| Local edits and unknown ownership | Concurrent/uncommitted edits retained, conflicts visible, no arbitrary file deletion |
| Backend/local failure and retry | No premature cleanup or state advancement; partial outcomes visible and recoverable by reconciliation |
| Concurrent backend writes | Reviewed conflict policy demonstrated, no undocumented atomicity or stale-retry guarantees |
| Restoration from known prior content | Explicit recommit rebuilds readable/searchable content without claiming historical retention |
| Local and Cloud | Separate backend readback and retrieval checks on isolated data; hosted pinned-version behavior independently established |

## Review and delivery {#review}

First review the explicit-input/target contract, metadata visibility, managed-file proof/races, partial-success state and concurrency/recovery limits. Only then implement small independently reviewable commits and update both languages with decisions and test evidence. Preserve the three entry points, scope validation and backend parity for any changed contract. Real Postgres and hosted checks remain required for their claims.

PR #816 contains design documentation only at this stage. It authorizes no release, deployment, production cleanup or automatic follow-up task creation. Personal memories are not test fixtures. This revision performed source/document checks only; MEM-16's experiments and earlier regression results are not acceptance of the proposed behavior.
