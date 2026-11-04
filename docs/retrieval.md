# Host retrieval configuration

## Retrieval entry points

The current installation flows use the following retrieval entry points. Hook
migration is implemented for Codex and Claude Code; the other adapters continue
to ask the agent to invoke `<binary> retrieve`.

| Hosts | Retrieval entry point | Query preparation |
|---|---|---|
| Codex | `UserPromptSubmit` hook | Query extraction for eligible prompts; original/prefix fallback on failure or input limits |
| Claude Code | `UserPromptSubmit` hook | Original prompt, limited to its first 2,000 characters; no query extraction |
| Cola, OpenClaw, pi | Agent invokes `retrieve` through the `memu-retrieve` skill | Agent chooses the query using the skill's instructions |
| Cursor, Hermes, WorkBuddy, generic | Agent invokes `retrieve` through a managed inline instruction | Agent chooses the query using the inline instructions |

All of these host CLI retrieval paths return `retrieval_status` and use the
backend-specific score cutoffs below. Codex and Claude Code additionally wrap
results with shared agent-facing guidance and `context_counts`: `returned` and
`omitted` counts for hits/resources after applying any hook context budget.
Skill and inline-instruction paths expose the retrieval command's JSON directly;
they do not use that hook wrapper.

Re-running the Codex or Claude Code installer registers hooks and removes the
managed legacy retrieval instruction/skill. A package upgrade alone does not
migrate an existing installation. This table describes implementation and
installation behavior, not confirmation that hooks are enabled or delivered in
a particular running session.

## Score configuration

Host segment score cutoffs are selected by `MEMU_MEMORY_MODE`. Configure overrides
in `~/.memu/config.env`; process environment variables take precedence.

`<binary> init` and `<binary> config --cloud|--local` add a commented configuration
template once. The template explains the defaults and independent backend
settings; existing overrides and edits to the template are preserved on reruns.
The commands leave threshold assignments commented so Cloud defaults can evolve
with package upgrades and Local users can supply their own calibration.

## Cloud

Cloud retrieval uses the calibrated defaults below. They apply to the Cloud
embedding model used for calibration; a change to that model requires reviewing
the defaults. Users can override individual categories:

```dotenv
MEMU_MEMORY_MODE=cloud
MEMU_CLOUD_RETRIEVE_MIN_SCORE_SHORT=0.55
MEMU_CLOUD_RETRIEVE_MIN_SCORE_LONG=0.60
MEMU_CLOUD_RETRIEVE_MIN_SCORE_EXTRACTED=0.58
```

An unset Cloud category uses its default. Set a category to `-1` to retain all
valid cosine-scored candidates in that category.

## Local

Local retrieval has no default cutoff. Users calibrate their own embedding model
and corpus, then set the corresponding optional variables:

| Category | Variable | Default |
|---|---|---|
| Short | `MEMU_LOCAL_RETRIEVE_MIN_SCORE_SHORT` | Filtering disabled |
| Long | `MEMU_LOCAL_RETRIEVE_MIN_SCORE_LONG` | Filtering disabled |
| Extracted | `MEMU_LOCAL_RETRIEVE_MIN_SCORE_EXTRACTED` | Filtering disabled |

Recalibrate Local thresholds when changing the embedding model. Local and Cloud
settings are independent: changing `MEMU_MEMORY_MODE` selects only that backend's
thresholds.

## Filtering and query categories

Values must be finite numbers between -1 and 1; segments at or above the cutoff
survive. Only files referenced by surviving segments are returned and mirrored.
Resources are scored separately and are unaffected.

Host retrieval also returns `retrieval_status`: successful completion, query
category, applied cutoff (`null` when disabled), candidate segment count,
filtered and retained segment counts, and final returned hit count. Retained
segments are counted before the five-hit output cap. Score filtering is a
heuristic, not a definitive semantic relevance judgment.

`<binary> retrieve` classifies the original query as short below 200 non-whitespace
characters and long otherwise. `--query-kind short|long|extracted` overrides that
classification. The Codex prompt hook passes `extracted` only after successful
query extraction; failures and input-limit fallbacks retain the original prompt's
short/long category. This filtering applies to host adapters, not the Python
`MemoryService.progressive_retrieve` API or the standalone `memu retrieve` command.
