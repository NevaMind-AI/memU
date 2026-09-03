# Developer integration

Applications that already own their conversation history can submit one completed session to memU without implementing a host adapter. The application decides when a session is ready, converts it to the canonical input, runs one external evolve executor, and commits the executor's result to the configured Local or Cloud backend.

This is an application integration contract. It starts with a completed session supplied by the application; selecting facts from an ongoing conversation or inventing a conversation on an agent's behalf is outside the v1 interface.

## Lifecycle

```text
completed application session
  → memu memorize prepare
  → one external executor processes all jobs serially
  → memu memorize commit
  → configured Local or Cloud backend
```

`prepare` and `commit` are the deterministic parts of the lifecycle. The middle step is real agent work: the executor reads the session, compares it with existing memory and skill files, and makes create, patch, or no-op decisions.

memU uses the fixed working directory `~/.memu/developer`. Version 1.0 permits one active developer run at a time:

```text
~/.memu/developer/
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

## 1. Build one canonical session

A payload represents one completed session. Its `items` must remain in the order in which the activity occurred.

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
memu memorize prepare session.json --json
```

Use `-` instead of a file path to read one payload from stdin.

`prepare` performs the following work before returning:

1. validates the canonical payload;
2. writes the message-only and full JSONL projections;
3. lists the current RecallFiles from the configured backend and writes them into the workspace's `memory/` and `skill/` directories;
4. snapshots the working copies by content hash;
5. creates three numbered jobs and the active-run marker.

A successful JSON response has this shape:

```json
{
  "workspace": "/home/alice/.memu/developer",
  "transcript": {
    "memory_path": "/home/alice/.memu/developer/input/1.jsonl",
    "skill_path": "/home/alice/.memu/developer/input/1_full.jsonl"
  },
  "jobs": [
    "/home/alice/.memu/developer/jobs/1.txt",
    "/home/alice/.memu/developer/jobs/2.txt",
    "/home/alice/.memu/developer/jobs/3.txt"
  ],
  "executor_prompt": "Process this prepared memU self-evolve run in one agent session.\nRead and carry out every job file below in the listed order:\n1. /home/alice/.memu/developer/jobs/1.txt\n2. /home/alice/.memu/developer/jobs/2.txt\n3. /home/alice/.memu/developer/jobs/3.txt\nRun one job at a time. Do not parallelize, skip, or reorder jobs. If any job fails, stop and report failure. Do not run `memu memorize commit`. Report success only after every job has completed.",
  "next_command": "memu memorize commit"
}
```

| Response field | Use |
|---|---|
| `workspace` | Fixed memU developer workspace. |
| `transcript` | Materialized inputs referenced by the jobs; applications normally do not edit them. |
| `jobs` | Authoritative execution order. |
| `executor_prompt` | Complete handoff to one external evolve executor. |
| `next_command` | Commit command to run once after executor success. |

Only one prepared run may be active. A second `prepare` is rejected until the current run commits.

## 3. Execute all evolve jobs

Start one external agent session in an environment that can:

- read and write the returned workspace;
- run the `memu` executable used by the generated resource job;
- read any original files that may be described as resources.

Pass `executor_prompt` to that agent. It instructs the executor to process these jobs:

| Order | Job | Expected outcome |
|---:|---|---|
| 1 | Memory evolution | Create, patch, or leave unchanged the user-memory Markdown files. |
| 2 | Skill evolution | Create, patch, or leave unchanged skills, then log files changed during the supplied session. |
| 3 | Resource description | Verify logged paths and describe readable files in `resources.md`. |

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
    "--json",
])
```

The executor API and process isolation are application choices. memU defines the filesystem handoff and serial execution contract, not how the external agent is hosted.

## 4. Commit the result

After the executor reports success, run `next_command` once. Add `--json` when a machine-readable result is required:

```bash
memu memorize commit --json
```

`commit` hashes the workspace's `memory/` and `skill/` files against the pre-evolve snapshot, reads successfully described resources, and submits the resulting records through the configured backend. The response contains `recall_files` and `resources`; either list may be empty after a valid no-op run.

On success, memU:

- updates the workspace snapshot;
- removes the projected input, numbered jobs, resource files, and active marker;
- leaves the `memory/` and `skill/` mirrors on disk;
- makes committed RecallFiles available to normal `list-files` and `retrieve` calls.

Only newly created or content-modified files are submitted. File deletion is not part of the v1 commit contract.

## Run states and recovery

| State | Evidence | Application action |
|---|---|---|
| Ready | No `.memorize_run.json` | Call `prepare` with one canonical session. |
| Prepared | Active marker and three jobs exist | Start exactly one evolve executor. |
| Executing | Executor is processing the jobs | Do not call another `prepare` or `commit`. |
| Evolve succeeded | Executor completed all jobs | Run `next_command` once. |
| Evolve failed | Executor stopped before all jobs completed | Do not commit. The active run remains for inspection; version 1.0 has no discard command. |
| Commit failed | Command returned non-zero and the active marker remains | Preserve the workspace, fix the backend problem, and retry `commit`; do not repeat `prepare` or evolve. |
| Committed | Active marker and ephemeral run files are gone | The fixed workspace is ready for the next run. |

Partial job execution is not resumable in the developer v1 interface, and there is currently no abort command. Backend commit failure intentionally retains the evolved workspace for commit retry.

## Consistency and concurrency

The fixed workspace permits only one active developer run, so applications must not start a second executor or `prepare` while its marker exists. It does not provide backend-level conflict resolution.

`prepare` reads the backend once and establishes the baseline for the run. The workspace is not refreshed again before `commit`. If another host or developer run changes the same `(track, name, user scope)` RecallFile during that window, the later successful commit may overwrite the earlier content. Version 1.0 has no ETag, base revision, three-way merge, or conflict copy.

Applications that may overlap with host bridging should serialize runs that can edit the same RecallFiles, or assign non-overlapping RecallFile ownership.

The prepare mirror is additive/overwriting: RecallFiles returned by the backend are written atomically into the workspace, but local files absent from the backend response are not deletion-synchronized. Applications should treat the backend—not a retained workspace directory—as the source of truth between runs.

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
