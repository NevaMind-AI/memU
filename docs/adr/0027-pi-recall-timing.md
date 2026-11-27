# ADR 0027: pi recall at prompt boundaries

- Status: Proposed
- Date: 2026-11-27
- Scope: pi host retrieval delivery and memorization timing (MEM-21).
- Builds on: [ADR 0021](0021-pi-extension-hooks.md), [ADR 0026](0026-shared-toml-config.md).
- Chinese: [中文](0027-pi-recall-timing.zh.md).

## Context

The pi extension previously submitted retrieval on input and called `sendMessage`
with `steer` and `triggerTurn: true` when it completed. A result arriving after a
complete answer could initiate another answer. A host retaining the last assistant
message could then replace the original answer with a retrieval-driven reply.
Hidden custom messages do not hide the assistant replies they trigger.

Users need a choice between current-prompt recall and immediate response. Hermes's
`recall_sync` distinction makes the latency/freshness tradeoff explicit. Every
eligible prompt still retrieves; this is separate from query extraction policy.

## Decision

Use `[hosts.pi] recall_sync = true` by default, with `MEMU_PI_RECALL_SYNC` as the
process override. A bounded `recall-settings` call resolves shared configuration
at session start/reload. Changes take effect on reload/new session. A settings
failure warns and leaves the synchronous default in place.

- Synchronous: `before_agent_start` awaits current-prompt retrieval, then returns
  a hidden reference message before generation. A three-second budget covers
  subprocess startup and the entire hook; failure/timeout skips injection.
- Asynchronous: start current-prompt retrieval without waiting. Only a completed
  result from the immediately preceding eligible prompt is offered at the next
  prompt boundary. The first prompt may have no memory. If a result is still
  pending at that boundary, cancel/discard it. There is no join wait.
- Neither mode sends steering/follow-up messages or requests another model turn.
  Empty successful retrieval does not produce a reference message.

Reference text names its source prompt, marks previous-prompt results as such,
and asks the model to use relevant facts only and follow the current task.
This is a relevance instruction, not a semantic topic-change classifier: async
results may still be irrelevant. No additional model call is introduced to filter
those results. Request context removes prior memU retrieval messages, retaining
only the current reference by unique ID; stored session history remains intact.

Session shutdown and tree navigation clear pending references and cancel hooks.
Generation/session guards discard late callbacks. The hook deadline kills the
Python process; managed query-extraction children retain their existing parent
lifetime cleanup. No retrieval result is persisted as a prefetch cache across
reloads or sessions.

Memorization starts only after the answer settles and current retrieval finishes
or expires, retaining the existing background-worker lock/cooldown. Retrieval
completion before generation must not start memorization while pi is still idle
inside `before_agent_start`.

## Validation and limits

Native Node tests execute the TypeScript extension with mocked child processes
and pi events. They check same-prompt blocking, next-prompt consumption, zero
steering, deadlines, late results, resets, context filtering and memorization
ordering. Python tests cover TOML/default resolution, installation and empty
recall. The lifecycle checks do not establish real-model answer quality or a
production latency distribution. A live installed pi reload and representative
answer-quality evaluation remain separate validation steps.

The generated template exposes the setting; existing TOML without it uses the
synchronous default. Existing installed extension copies need reinstallation
(`memu-pi install-prompt-hook`) and `/reload` to pick up this delivery change.
README/public documentation is coordinated with the docs site separately.
