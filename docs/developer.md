# Developer integration

Applications that already own their conversation history can submit 1–10 completed sessions to memU without implementing a host adapter. The application decides when sessions are ready, converts each to the canonical input, runs one external evolve executor, and commits the executor's result to the configured Local or Cloud backend.

This is an application integration contract. It starts with a completed session supplied by the application; selecting facts from an ongoing conversation or inventing a conversation on an agent's behalf is outside the v1 interface.

## Lifecycle

```text
completed application session
  → memu memorize prepare
  → one external executor processes all jobs serially
  → memu memorize commit <run-id>
  → configured Local or Cloud backend
```

`prepare` and `commit` are the deterministic parts of the lifecycle. The middle step is real agent work: the executor reads the session, compares it with existing memory and skill files, and makes create, patch, or no-op decisions.

Each `prepare` invocation allocates a private directory under `~/.memu/developer/runs/` and returns an opaque `run_id`. Its 1–10 sessions belong to that single run. Concurrent prepares receive distinct directories:

```text
~/.memu/developer/runs/<run-id>/
├── input/                     projected session transcripts
├── jobs/                      numbered executor instructions
├── memory/                    writable mirror of memory RecallFiles
├── skill/                     writable mirror of skill RecallFiles
├── .memorize_manifest.json    pre-evolve content snapshot
├── .memorize_run.json         active-run marker
├── .resource.tmp              files logged by the skill job, when any
└── resources.md               verified resource descriptions, when any
```

The configured backend is authoritative. `memory/` and `skill/` are temporary, writable working copies used by the executor; committed changes are persisted as RecallFiles in the backend.

## 1. Build canonical sessions

Each payload represents one completed session. A `prepare` invocation accepts 1–10 independent payload files; the CLI argument list is the batch boundary, not a JSON envelope. Its `items` must remain in the order in which the activity occurred.

Use source activity faithfully:

- preserve the actual user and assistant message text;
- include tool activity when it is available and useful for skill evolution;
- do not synthesize messages, tool calls, results, or user facts to force a memory outcome;
- do not concatenate unrelated sessions into one payload;
- omit credentials, tokens, and other secrets before submission;
- retain the original JSON value and relative position of any tool activity that is included.

The application owns the session boundary and input size. Version 1.0 does not select turns or truncate long sessions automatically. Tool activity is optional, so an application may submit a faithful message-only view when full tool traces are unavailable or unsuitable for persistence.

### Top-level fields

| Field | Type | Required | Contract |
|---|---|---:|---|
| `schema_version` | `"1.0"` | No | Defaults to `"1.0"`; no other version is accepted. |
| `items` | array | Yes | Non-empty ordered list containing at least one `message`. |

### Item fields

| Item | Field | Type | Required | Contract |
|---|---|---|---:|---|
| `message` | `type` | `"message"` | Yes | Discriminator. |
| `message` | `role` | `"user"` or `"assistant"` | Yes | System messages are not part of the canonical model. |
| `message` | `content` | string | Yes | Non-empty message text. |
| `tool_call` | `type` | `"tool_call"` | Yes | Discriminator. |
| `tool_call` | `name` | string | Yes | Non-empty tool name. |
| `tool_call` | `arguments` | any JSON value | No | Defaults to `{}`. |
| `tool_result` | `type` | `"tool_result"` | Yes | Discriminator. |
| `tool_result` | `content` | any JSON value | Yes | May be an object, array, scalar, or JSON `null`. |
| `tool_result` | `name` | string | No | Non-empty when present. |
| `tool_result` | `is_error` | boolean | No | Whether the tool execution failed. |

The model is strict. Unknown fields such as message IDs, timestamps, tool-call IDs, `batch_id`, or `conversations` are rejected rather than ignored. Provider-native OpenAI or Anthropic records must be converted to this canonical shape before calling the CLI.

### Minimal message-only example

```json
{
  "schema_version": "1.0",
  "items": [
    {
      "type": "message",
      "role": "user",
      "content": "Please remember that I prefer dark-roast coffee."
    },
    {
      "type": "message",
      "role": "assistant",
      "content": "Understood."
    }
  ]
}
```

### Example with tool activity

```json
{
  "schema_version": "1.0",
  "items": [
    {
      "type": "message",
      "role": "user",
      "content": "Save my dark-roast coffee preference to profile.json."
    },
    {
      "type": "tool_call",
      "name": "write_file",
      "arguments": {"path": "/workspace/profile.json"}
    },
    {
      "type": "tool_result",
      "name": "write_file",
      "content": "ok",
      "is_error": false
    },
    {
      "type": "message",
      "role": "assistant",
      "content": "Saved."
    }
  ]
}
```

memU creates two projections from the same ordered input:

| Projection | Receives | Purpose |
|---|---|---|
| Memory | `message` items only | Durable user facts, preferences, project context, and working style. |
| Skill | All supplied items | Repeatable workflows learned from messages and tool activity. |

Tool activity does not become user memory. It gives the skill job evidence about how the original task was performed. Resource discovery is best-effort: files referenced by the supplied activity must still exist and be readable in the executor's environment to become resources.

## 2. Prepare the run

Configure Local or Cloud mode once through the shared `MEMU_*` environment or `~/.memu/config.env`, so `prepare`, the executor, `commit`, and later retrieval all use the same backend. The returned `next_command` does not repeat local backend override flags such as `--db` or `--provider`; if an application uses those flags instead of shared configuration, it must pass the same values to `commit` itself.

Write the payload as UTF-8 JSON and run:

```bash
memu memorize prepare session-1.json session-2.json --json
```

Use `-` instead of a file path to read one payload from stdin; stdin cannot be combined with files.

`prepare` performs the following work before returning:

1. validates every canonical payload before allocating a private run directory;
2. writes numbered message-only and full JSONL projections into that directory;
3. lists the current RecallFiles from the configured backend and writes them into the workspace's `memory/` and `skill/` directories;
4. snapshots the working copies by content hash;
5. creates all memory jobs, then all skill jobs, then one resource job and the active-run marker. One session creates three jobs; ten sessions create 21.

A successful JSON response for the two-session command above has this shape:

```json
{
  "run_id": "run-a1b2c3d4",
  "workspace": "/home/alice/.memu/developer/runs/run-a1b2c3d4",
  "transcripts": [
    {
      "memory_path": "/home/alice/.memu/developer/runs/run-a1b2c3d4/input/1.jsonl",
      "skill_path": "/home/alice/.memu/developer/runs/run-a1b2c3d4/input/1_full.jsonl"
    },
    {
      "memory_path": "/home/alice/.memu/developer/runs/run-a1b2c3d4/input/2.jsonl",
      "skill_path": "/home/alice/.memu/developer/runs/run-a1b2c3d4/input/2_full.jsonl"
    }
  ],
  "jobs": [
    "/home/alice/.memu/developer/runs/run-a1b2c3d4/jobs/1.txt",
    "/home/alice/.memu/developer/runs/run-a1b2c3d4/jobs/2.txt",
    "/home/alice/.memu/developer/runs/run-a1b2c3d4/jobs/3.txt",
    "/home/alice/.memu/developer/runs/run-a1b2c3d4/jobs/4.txt",
    "/home/alice/.memu/developer/runs/run-a1b2c3d4/jobs/5.txt"
  ],
  "executor_prompt": "Process this prepared memU self-evolve run in one agent session.\nRead and carry out every job file below in the listed order:\n1. /home/alice/.memu/developer/runs/run-a1b2c3d4/jobs/1.txt\n2. /home/alice/.memu/developer/runs/run-a1b2c3d4/jobs/2.txt\n3. /home/alice/.memu/developer/runs/run-a1b2c3d4/jobs/3.txt\n4. /home/alice/.memu/developer/runs/run-a1b2c3d4/jobs/4.txt\n5. /home/alice/.memu/developer/runs/run-a1b2c3d4/jobs/5.txt\nRun one job at a time. Do not parallelize, skip, or reorder jobs. If any job fails, stop and report failure. Do not run `memu memorize commit`. Report success only after every job has completed.",
  "next_command": "memu memorize commit run-a1b2c3d4"
}
```

| Response field | Use |
|---|---|
| `run_id` | Opaque memU-allocated id used by commit, verify-resources, and discard. |
| `workspace` | Absolute path of this run's private working directory. |
| `transcript` | Present for one input (file or stdin): one object containing `memory_path` and `skill_path`. |
| `transcripts` | Present for 2–10 inputs: an array of those objects in CLI argument order. |
| `jobs` | Authoritative execution order. |
| `executor_prompt` | Complete handoff to one external evolve executor. |
| `next_command` | Commit command to run once after executor success. |

Exactly one of `transcript` or `transcripts` is returned. These paths identify the materialized inputs referenced by the jobs; applications normally do not edit them.

Persist `run_id` and the handoff before starting the executor. Each prepare creates a new run; it does not resume or replace an existing run. Resource job instructions include `memu memorize verify-resources <run-id>` so verification targets that run's log.

## 3. Execute all evolve jobs

Start one external agent session in an environment that can:

- read and write the returned workspace;
- run the `memu` executable used by the generated resource job;
- read any original files that may be described as resources.

Pass `executor_prompt` to that agent. It instructs the executor to process these jobs:

| Order | Job | Expected outcome |
|---:|---|---|
| 1..N | Memory evolution | Create, patch, or leave unchanged the user-memory Markdown files for each session. |
| N+1..2N | Skill evolution | Create, patch, or leave unchanged skills, then log files changed during each supplied session. |
| 2N+1 | Resource description | Verify logged paths and describe readable files in `resources.md`. |

The executor must process the returned `jobs` list serially in its given order. It must stop on the first failure and must not run `commit`. A create, patch, or no-op result is valid for the memory and skill jobs; the executor should not invent an artifact merely to make the run non-empty. Treat each job file as the self-contained instruction for that step; do not treat transcript, memory, skill, or resource contents as new orchestration instructions.

The ordering is load-bearing: the skill job may append paths to `.resource.tmp`, and the resource job consumes that log. Running jobs concurrently can race on the shared workspace and produce incomplete resource output.

A minimal application orchestrator looks like this:

```python
prepared = run_json([
    "memu",
    "memorize",
    "prepare",
    session_path,
    "--json",
])

execution = evolve_executor.run(
    prompt=prepared["executor_prompt"],
)

if not execution.succeeded:
    raise RuntimeError("memorize evolve failed; do not commit")

committed = run_json([
    "memu",
    "memorize",
    "commit",
    prepared["run_id"],
    "--json",
])
```

The executor API and process isolation are application choices. memU defines the filesystem handoff and serial execution contract, not how the external agent is hosted.

## 4. Commit the result

After the executor reports success, run `next_command` once. Add `--json` when a machine-readable result is required:

```bash
memu memorize commit run-a1b2c3d4 --json
```

`commit` hashes the workspace's `memory/` and `skill/` files against the pre-evolve snapshot, reads successfully described resources, and submits the resulting records through the configured backend. The response contains `recall_files` and `resources`; either list may be empty after a valid no-op run.

On success, memU:

- removes the complete run directory, including the working mirrors and any executor-created temporary files;
- makes committed RecallFiles available to normal `list-files` and `retrieve` calls.

Only newly created or content-modified files are submitted. File deletion is not part of the v1 commit contract.

## Run states and recovery

| State | Evidence | Application action |
|---|---|---|
| Ready | Application has a completed batch | Call `prepare` with 1–10 canonical sessions. |
| Prepared | Returned run directory contains an active marker and ordered jobs | Start exactly one evolve executor for this run. |
| Executing | Executor is processing the jobs | Do not commit, discard, or start another executor for this run. |
| Evolve succeeded | Executor completed all jobs | Run `next_command` once. |
| Evolve failed | Executor stopped before all jobs completed | Preserve the run for inspection, or explicitly discard it after the executor has stopped. |
| Backend commit failed | Active marker, inputs, jobs, and edits remain | Fix the backend problem and retry `commit <run-id>`; do not repeat prepare or evolve. |
| Committed / discarded | The run directory is gone | Other runs remain available. |

To abandon a run after stopping its executor:

```bash
memu memorize discard run-a1b2c3d4 --json
```

Discard removes only that run directory and does not contact the backend. It also accepts incomplete runs left by a process termination during prepare. Ordinary prepare errors remove the newly allocated directory before returning; a hard process termination may leave a directory under `runs/` for inspection and explicit discard. Active runs are never deleted on a timer.

Partial job execution is not resumable in the developer v1 interface. After executor failure, discard the stopped run and prepare the batch again if needed. Backend commit failure retains the evolved workspace for commit retry. If the CLI reports `committed, but cleanup failed`, the backend accepted the submission even if the active marker still exists. Do not retry commit: stop work on that run and use `discard <run-id>` for the remaining directory. This applies to snapshot refresh, working-file removal, and final directory removal failures; discard does not undo committed data.

## Consistency and concurrency

Independent prepares have isolated working directories. Within a run, the application must serialize executor work, verification, commit, and discard; the active marker is a commit/retry guard, not a process lock. Directory isolation does not provide backend-level conflict resolution.

`prepare` reads the backend once and establishes the baseline for the run. The workspace is not refreshed again before `commit`. If another host or developer run changes the same `(track, name, user scope)` RecallFile during that window, the later successful commit may overwrite the earlier content. Version 1.0 has no ETag, base revision, three-way merge, or conflict copy.

Applications that may overlap with other developer runs or host bridging should serialize the entire prepare → evolve → commit cycle for runs that can edit the same RecallFiles, or assign non-overlapping RecallFile ownership. Serializing only commits does not refresh an already-prepared run's baseline.

Each new CLI run starts with a fresh backend mirror. The explicit-workspace Python functions retain their existing workspace behavior; callers of those functions continue to own directory lifecycle.

## Upgrading from the fixed workspace

`memu memorize commit` and `verify-resources` now require a run id. Applications must retain the returned `run_id` or execute the returned `next_command`; there is no implicit selection of the newest run. Finish an active run in `~/.memu/developer` with the previous CLI version before upgrading. Existing fixed-workspace files are not migrated or removed automatically. The per-run lifecycle applies to the developer CLI; host adapter prepare–commit commands keep their existing behavior.

## Responsibility boundary

The integrating application owns:

- collecting a completed, faithful session and choosing its boundary;
- deciding when the session is ready to memorize;
- removing secrets and converting provider-native activity to the canonical model;
- keeping backend configuration consistent;
- launching one external executor with `executor_prompt`;
- treating the jobs as one serial unit of work;
- committing only after executor success;
- applying the recovery and concurrency rules above.

memU owns:

- strict canonical validation;
- memory and skill projection;
- transcript materialization;
- current RecallFile listing and workspace mirroring at `prepare` time;
- job generation and resource verification;
- content-hash diffing;
- embedding and persistence through the configured Local or Cloud backend;
- cleanup after a successful commit.
