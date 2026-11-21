# 0025: Persist the Evolve Selection for Each Developer Memorize Run

Status: Accepted.

[中文](0025-developer-evolve-selection.zh.md) · Related: [#697](https://github.com/NevaMind-AI/memU/issues/697), [ADR 0019](0019-developer-run-workspaces.md)

Developer applications may need to update only user memory. Generating skill and
resource jobs for that run adds work unrelated to the requested knowledge kind.
The default remains the complete memory, skill, and resource flow.

## Decision

`memu memorize prepare --only memory` and the Python lifecycle's `only="memory"`
select memory-only evolution. Prepare persists `evolve_selection` as `memory` or
`all` in the run marker. Commit uses that selection; it has no override parameter.
Markers without this field retain the complete flow for compatibility, while
unknown selections fail before submission.

Selection controls the jobs, local mirrors, content snapshot, changed-file
collection, and submitted knowledge. A batch of N sessions generates N memory
jobs in memory-only mode, rather than the default 2N + 1 jobs. It skips skill and
resource template resolution. Extra skill files and resource lists are ignored
without parsing or submission, including malformed files. They may already exist
in a Python caller's working directory, so their presence does not reject a run.

The selection belongs to the prepared run rather than just its executor prompt:
the executor and commit execute separately, and a prompt alone cannot constrain
what commit reads. Allowing commit to choose again would also disconnect its
submission from the prepared jobs and snapshot.

## Consequences

- Canonical input, both JSONL projections, and the existing handoff response
  fields remain available. This change selects work; it does not redesign input
  materialization or add skill-only evolution.
- The backend API is unchanged. Prepare still pages through all recall-file
  tracks and only materializes selected files locally; this does not promise
  reduced backend or Cloud transfer.
- Existing acknowledgement, retry, and cleanup rules remain. The CLI removes
  its entire private run after success, including ignored extra artifacts; the
  Python lifecycle leaves its caller-owned directory and unselected skill and
  resource artifacts in place.
- New versions can complete older runs without a selection. The reverse is not
  safe for memory-only runs: older versions ignore the new marker field and
  commit the complete flow. Finish or discard these runs with a version that
  understands the selection before downgrading.
- Host adapter flows retain their complete default behavior. Evolve selection
  is distinct from the user scope that determines knowledge ownership.
