# Developer integration

Applications that already own their conversation history can send one complete session through memU's self-evolve pipeline without implementing a host adapter.

This interface prepares self-evolve work; it does not run an agent. The application is responsible for deciding when to submit a session and for starting an external agent that can read the generated instructions, read and write files, and run the resource-verification command.

## Workflow

```text
application session
  → memu memorize prepare
  → external agent processes numbered jobs
  → memu memorize commit
  → configured Local or Cloud backend
```

Only one prepared run may be active in a workspace at a time. The default workspace is `~/.memu/developer`; pass the same `--workspace` value to `prepare` and `commit` when overriding it.

### 1. Submit one session

The canonical payload contains a schema version and one ordered `items` list:

```json
{
  "schema_version": "1.0",
  "items": [
    {"type": "message", "role": "user", "content": "Save my dark-roast coffee preference."},
    {
      "type": "tool_call",
      "name": "write_file",
      "arguments": {"path": "profile.json"}
    },
    {
      "type": "tool_result",
      "name": "write_file",
      "content": "ok"
    },
    {"type": "message", "role": "assistant", "content": "Saved."}
  ]
}
```

`schema_version` defaults to `"1.0"`. Every payload must contain at least one user or assistant message. Tool calls and results are optional. The canonical model is strict: fields outside the documented item structures are rejected.

Memory evolution receives only `message` items. Skill evolution receives all items in their original order, so tool activity can teach repeatable workflows without becoming user memory.

Prepare from a UTF-8 JSON file:

```bash
memu memorize prepare session.json --json
```

Use `-` instead of a path to read the payload from stdin. `--json` returns the workspace, transcript paths, ordered job paths, and the command to run after the jobs finish.

### 2. Run the self-evolve agent

`prepare` creates three numbered instruction files under the workspace's `jobs` directory:

1. Mine the message transcript into durable user-memory Markdown.
2. Mine the full transcript, including tool activity, into durable skill Markdown and log files changed during the original session.
3. Verify and describe those changed files as resources.

Start an external agent and have it process every returned job file in numeric order. Each job is self-contained: the agent should read the instruction file and carry out its file and command operations as written. A job may legitimately make no changes when the session contains nothing durable.

Do not call `commit` before the agent has finished all jobs. Starting another `prepare` in the same workspace is rejected while this run is active.

### 3. Commit the result

After the external agent finishes:

```bash
memu memorize commit --json
```

`commit` sends only newly created or modified memory/skill Markdown and successfully described resources to the configured Local or Cloud backend. On success, it clears the run's input, jobs, resource files, and active marker.

If the backend commit fails, the workspace is preserved. Fix the backend problem and run `memu memorize commit` again; do not repeat `prepare`.

## Application responsibilities

The integrating application owns:

- collecting a complete session and deciding when it is ready to evolve;
- producing the canonical JSON payload;
- scheduling or launching the external self-evolve agent;
- making the agent process the returned jobs in order;
- calling `commit` only after that work succeeds;
- keeping one active run per workspace.

memU owns validation, memory/skill projection, transcript materialization, current RecallFile mirroring, job generation, workspace diffing, resource verification, embedding, and persistence through the configured backend.
