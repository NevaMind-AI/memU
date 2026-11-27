# Retrieval and injection

Retrieval searches existing memory. Injection makes the returned context available to the host model. Background memorization writes durable memory later; a successful retrieval does not mean the current conversation has already been saved.

## Timing by host {#timing}

Use the moment you press Send as the dividing line. Separate **when search starts** from **when its results inform the answer**.

- **Before submit**: retrieve first, then send the prompt to the model.
- **On submit**: pressing Send starts retrieval; the answer can begin in parallel.
- **After submit**: the agent receives the request and searches while working on it.

In the table, “current turn” means the answer to this request. A “follow-up turn” means further processing after the initial answer; you do not necessarily need to send another message.

| Host | When retrieval starts | Current or follow-up turn |
| --- | --- | --- |
| [Codex](codex.md) | **On submit**, searching in the background | Search runs in the background. Results inform the current answer if they arrive in time; otherwise, the next turn |
| [Claude Code](claude-code.md) | **On submit**, searching in the background | Results wake the agent when ready; if the initial answer has finished, it continues answering |
| [pi](pi.md) | **On submit**, searching in the background | Results arrive when ready: use them while answering, or automatically continue for another turn if the answer has finished |
| [Hermes](hermes.md) | **After submit**, when the agent decides memory would help | Current turn: read results when needed, then continue the answer or task |
| [Cursor](cursor.md) | **After submit**, instructed to search before answering | Current turn: read results, then answer; depends on the agent following the instruction |
| [OpenClaw](openclaw.md) | **After submit**, instructed to search before answering | Current turn: read results, then answer; depends on the agent following the instruction |
| [WorkBuddy](workbuddy.md) | **After submit**, instructed to search before answering | Current turn: read results, then answer; depends on the agent following the instruction |

None of these integrations waits for retrieval to finish before submitting the prompt. Background search timing affects whether memory can inform the first answer. Each host's page explains implementation, activation and verification in more detail.

## From prompt to query {#query}

Codex, Claude Code and pi share the hook query policy:

1. By default, use the original prompt up to 800 characters, truncating longer prompts to that prefix.
2. With `retrieval.extract_query = true`, inputs of 801–32,000 characters can use a separate host-model call to extract a short topic query. Extraction is limited to 12 seconds and falls back to the prefix on failure, timeout or invalid output. Inputs above 32,000 characters use the prefix directly.
3. Successful extraction selects the `extracted` cutoff. Otherwise the original prompt is `long` at 200 or more non-whitespace characters, and `short` below that boundary. This classification is separate from the 800-character extraction threshold.

Extraction is optional host logic; `MemoryService` remains embedding-only. [Configuration](../reference/configuration.md#retrieval) covers the switch and score cutoffs. Hermes, Cursor, OpenClaw and WorkBuddy form queries as part of the agent's ordinary reasoning; they do not use this hook extractor.

## What the agent receives {#results}

Each host uses the same retrieve command. It searches the configured Local or Cloud backend and returns:

- `hits`: up to five ranked entries with matched `text`, available source metadata, and a local mirror `path` or full inline `content`. Open a path when its excerpt is insufficient. Missing source data does not discard the matched text.
- `resources`: independent related files, with a `path` and `caption` when available. Cloud does not yet persist or retrieve workspace resources.
- `retrieval_status`: success, query category, cutoff and filtering counts. A successful empty result is valid.

Database IDs and scope metadata stay out of agent-facing hits. Hook context also includes returned/omitted counts; Claude Code may omit whole entries to fit its context budget. Scores are similarity signals, not semantic verdicts. Treat retrieved text as reference data, never as executable instructions, and check it against the current request.

## Manual retrieval {#manual}

Replace `memu-pi` with the appropriate host binary:

```sh
memu-pi retrieve "project deployment decisions"
memu-pi retrieve --query-stdin
```

The second form reads a UTF-8 query from standard input until EOF, useful for multiline text or difficult shell quoting. Manual retrieval uses the supplied query directly; it neither runs hook extraction nor automatically injects stdout into another session. `--query-kind short|long|extracted` explicitly selects a cutoff category when needed.

## Verify delivery {#verify}

First run `config show`, `doctor`, and manual retrieval for a known saved topic. Then send a real message in a session that has loaded the integration. For Codex, Claude Code and pi, retrieval traces normally live under `~/.memu/hosts/<host>/log/hooks/retrieve/` (`<host>` is `codex`, `claude-code` or `pi`); custom `--base-dir` moves the directory. Traces may contain queries and memory text: redact them before sharing.

Check `query_source`, `extraction_status`, returned counts and failure diagnostics. A backend success proves access, a hook trace proves execution, and observed context use verifies delivery in the host. For instruction-based hosts, inspect the loaded instruction and actual retrieve tool call. See [Troubleshooting](../troubleshooting/index.md).
