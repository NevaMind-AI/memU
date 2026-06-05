# Folder Memory Compiler

`FolderMemoryCompiler` turns an uploaded folder into a Markdown-backed memory repository.

It is designed for the workflow:

1. A user provides a folder containing raw data.
2. memU copies that folder into `raw_data/`.
3. memU compiles traceable evidence into `.memu/derived/`.
4. memU converts extracted evidence into structured Evolution Instructions.
5. memU builds Patch Proposals and sends them through the review gate.
6. Only approved proposals update `memory.md`, `soul.md`, and `skill.md`.
7. On the next run, changed files are re-extracted and deleted files become reviewed delete proposals.

## Output Layout

```text
memory_repo/
  AGENTS.md

  raw_data/
    ... original uploaded files, preserved as raw data

  memory.md
  memory/

  soul.md
  soul/

  skill.md
  skill/

  .memu/
    harness.json
    manifest.json
    evolution/
      instructions.jsonl
      patch_proposals.jsonl
      review_decisions.jsonl
    derived/
      ... per-source evidence markdown
```

`raw_data/` is the evidence source of truth inside the generated repository.
The compiler does not mutate the user's input folder.
`AGENTS.md` is a default, non-overwriting bootstrap file for local coding
agents. It points agents at `memory.md`, `soul.md`, `skill.md`, `raw_data/`,
sidecars, skill traces, and the main `memu-harness` commands.

`.memu/harness.json` stores repository-local, non-secret defaults for the
unified harness CLI. It is created by `memu-harness init` and can be edited by
humans or tooling.

## Markdown Buckets

- `memory.md` stores durable facts, preferences, events, knowledge, and general memory.
- `soul.md` stores persona, tone, voice, language style, and interaction-style signals.
- `skill.md` stores skills, workflows, tool-use patterns, procedures, and reusable capabilities.

Each top-level file has a generated block:

```md
<!-- memu:generated:start -->
...
<!-- memu:generated:end -->
```

memU replaces only this block on recompile. Human edits outside the block are preserved.

## Self-Evolve Review Gate

Raw data never edits `memory.md`, `soul.md`, or `skill.md` directly. For each
changed source, the compiler first writes evidence under `.memu/derived/`, then
creates an `EvolutionInstruction` with:

- `target`: `memory`, `soul`, or `skill`
- `operation`: `add`, `update`, or `delete`
- `reason`, `evidence`, `priority`, and `confidence`

Each instruction becomes a `PatchProposal`. The review gate approves, rejects,
or marks the proposal as `needs_review` using traceability, confidence, conflict
detection, and safety checks. Approved proposals update the generated Markdown
blocks; pending proposals remain auditable in `.memu/manifest.json` and
`.memu/evolution/`.

Use `--require-creator-review` with `memu-folder` or `memu-harness refresh` to
force proposals to remain pending until a creator reviews them. Then use
`memu-harness review-evolution` to approve or reject pending proposals:

```bash
memu-harness refresh memory_repo --require-creator-review
memu-harness review-evolution memory_repo
memu-harness review-evolution memory_repo --proposal-id patch_abc123 --reject
```

## Multimodal Raw Data

All files are copied into `raw_data/`, including:

- text and Markdown
- JSON, CSV, logs, and code
- images
- audio
- video
- PDFs and office documents
- unknown binary files

For text-like files, `.memu/derived/` stores text evidence. For binary,
document, or multimodal files, `.memu/derived/` stores traceable metadata
evidence. If a `MemoryService` with multimodal or document-capable LLM profiles
is provided, the compiler calls the existing `memorize` pipeline and appends
returned resource captions, memory items, and category summaries into the
evidence file.

Without an LLM, non-text sources can still carry semantic evidence through
sidecar text files. For a source such as `workflow.png` or `report.pdf`, the
compiler will read nearby files such as:

- `workflow.caption.md`
- `workflow.metadata.json`
- `workflow.png.caption.md`
- `workflow.transcript.txt`
- `workflow.ocr.jsonl`
- `workflow.notes.md`
- `report.summary.md`
- `report.pdf.notes.txt`

Supported sidecar labels are `alt`, `caption`, `description`, `notes`,
`summary`, `transcript`, `metadata`, `meta`, `ocr`, and `frames`. Supported
sidecar formats are Markdown, text, JSON, and JSONL. JSON and JSONL sidecars are
stable-formatted before being appended to the paired source's derived evidence,
so they can produce `memory`, `soul`, or `skill` entries that still point back
to the original raw source.

Sidecar files are treated as part of the paired source fingerprint.
Changing `workflow.caption.md` therefore re-extracts `workflow.png`, while the
sidecar itself is still copied into `raw_data/`.

When a source is deleted, memU creates delete Evolution Instructions. Approved
delete proposals remove generated Markdown entries, raw copies, and generated
`.memu/derived/**/*.evidence.md` files. Human-written Markdown notes outside
generated blocks are preserved.

## Usage

Command line:

```bash
memu-folder path/to/uploaded-folder path/to/memory-repo
```

Machine-readable summary:

```bash
memu-folder path/to/uploaded-folder path/to/memory-repo --json
```

Exclude noisy files explicitly with repeated posix glob patterns:

```bash
memu-folder path/to/uploaded-folder path/to/memory-repo \
  --exclude "node_modules/**" \
  --exclude "*.tmp"
```

You can also persist these rules in `.memuignore` at the uploaded folder root
or memory repository root:

```gitignore
# .memuignore
node_modules/**
*.tmp
**/__pycache__/**
```

Watch for changes and recompile automatically:

```bash
memu-folder path/to/uploaded-folder path/to/memory-repo --watch
```

For automation, emit one JSON line per compile event:

```bash
memu-folder path/to/uploaded-folder path/to/memory-repo \
  --watch \
  --json \
  --poll-interval 2
```

Each watch JSON event includes a `delta` object with `new`, `changed`, and
`removed` source paths computed before that compile event.

With `MemoryService` extraction:

```bash
memu-folder path/to/uploaded-folder path/to/memory-repo \
  --use-memory-service \
  --api-key-env OPENAI_API_KEY \
  --chat-model gpt-4o-mini
```

For both `memu-folder` and `memu-harness`, if `--api-key-env` is omitted, the
CLI uses the provider default (`OPENAI_API_KEY` for OpenAI-compatible defaults,
`XAI_API_KEY` for `--provider grok`). Pass `--api-key` only for local
experiments; avoid putting secrets in shell history for shared environments.

Pass user scope values with repeated `--user` flags:

```bash
memu-folder raw_data memory_repo --user user_id=u1 --user agent_id=assistant
```

Use the unified context harness command when one tool should own ingestion,
context assembly, watching, and skill evolution:

```bash
memu-harness init path/to/memory-repo --source-folder path/to/uploaded-folder

memu-harness doctor path/to/memory-repo --json

memu-harness refresh path/to/memory-repo \
  --query "current agent task"

memu-harness refresh path/to/memory-repo \
  --exclude "node_modules/**" \
  --exclude "*.tmp"

memu-harness status path/to/memory-repo --json
```

`init` creates `AGENTS.md`, `memory.md`, `memory/`, `soul.md`, `soul/`,
`skill.md`, `skill/`, `.memu/`, `.memu/harness.json`, and `raw_data/`. If
`--source-folder` is provided, the raw files are copied into `raw_data/` before
extraction. Existing `AGENTS.md` and `.memu/harness.json` files are preserved.

`doctor` is read-only. It validates the repository layout, manifest shape,
generated block markers, and manifest references to raw files, sidecars,
evidence files, per-source Markdown detail files, and orphaned derived evidence.
Missing `AGENTS.md` or orphaned `.evidence.md` files produce warnings, not
errors, so older repositories remain usable.

For `refresh`, `ingest`, `context`, `trace`, and `watch`, passing only the
memory repository path uses `repo/raw_data` as the source folder. Passing
`SOURCE_FOLDER REPO_DIR` is still supported when the raw-data folder lives
outside the repository.

For API calls, passing an already initialized memory repository as both
`source_folder` and `output_folder` is treated the same way: memU reads from
`repo/raw_data` and leaves repository-level Markdown notes alone.

If the output repository is placed inside the uploaded folder, memU excludes the
output repository subtree from scanning and from the initial `raw_data/` copy.

`status` is read-only. It compares the current raw-data source fingerprints
against `.memu/manifest.json` and reports `new`, `changed`, `unchanged`, and
`removed` sources, including media sidecar bindings.

`--exclude` patterns are matched against posix-style source-relative paths and
can be repeated. memU does not apply default excludes, so uploaded evidence is
preserved unless the caller explicitly excludes a path such as `node_modules/**`,
`*.tmp`, or `**/__pycache__/**`. `.memuignore` uses the same pattern syntax.
For one-path harness commands such as `memu-harness refresh memory_repo`, memU
uses `memory_repo/.memuignore` and scans `memory_repo/raw_data`.

### Harness Config

For repeated agent runs, store repo defaults in `.memu/harness.json`:

```json
{
  "version": 1,
  "compiler": {
    "exclude_patterns": ["node_modules/**", "*.tmp"],
    "max_text_chars": 4000
  },
  "context": {
    "buckets": ["memory", "soul", "skill"],
    "bucket_char_limits": {
      "soul": 1000,
      "skill": 2000
    },
    "format": "system",
    "max_chars": 8000
  }
}
```

`compiler.exclude_patterns` and `compiler.max_text_chars` are used by
`memu-harness ingest`, `refresh`, `status`, `trace`, and `watch`.
`context.max_chars`, `context.bucket_char_limits`, `context.buckets`, and
`context.format` are used by `memu-harness context`, `memu-harness refresh`,
and standalone `memu-context`. Command-line flags override
`.memu/harness.json`; the config file overrides built-in defaults. The config
intentionally excludes LLM provider, API key, and user-scope settings because
those are environment or request specific.

`doctor` validates the config shape and reports invalid values as health
errors.

Python callers can use the same config helpers:

```python
import json
from memu import default_harness_config, harness_config_path, load_harness_config

repo_dir = "path/to/memory-repo"
config_path = harness_config_path(repo_dir)
config_path.write_text(
    json.dumps(
        default_harness_config(
            exclude_patterns=["node_modules/**", "*.tmp"],
            max_text_chars=4000,
        ),
        indent=2,
    ),
    encoding="utf-8",
)
config = load_harness_config(repo_dir)
```

Record a reusable skill lesson and submit it to the self-evolve gate:

```bash
memu-harness trace path/to/memory-repo \
  --task "Validate generated context packs" \
  --outcome success \
  --lesson "Check generated skill sections before injecting context into an agent"
```

Suggest durable skills from accumulated traces without writing:

```bash
memu-harness suggest-skills path/to/memory-repo --json
```

Apply suggested skills explicitly:

```bash
memu-harness suggest-skills path/to/memory-repo --min-support 2 --promote
```

Promote a lesson into the durable manual skill library:

```bash
memu-harness promote-skill path/to/memory-repo \
  --title "Validate Context Packs" \
  --when "Before injecting generated context into an agent" \
  --action "Build the context pack" \
  --action "Check manual and generated skill sections" \
  --lesson "Inspect promoted skills before relying on generated context"
```

`suggest-skills` groups raw `skill_traces/*.md` lessons, actions, tools, and
outcomes into deterministic promotion candidates. It is read-only unless
`--promote` is passed. Promoted skills are written outside the generated block
in `skill.md` and as stable cards under `skill/promoted/`. Promoting the same
title again updates the same card and keeps prior lessons/actions, source, and
metadata, so `refresh` preserves the evolving skill library while generated
skill traces continue to produce reviewed proposals. Context assembly skips
`skill.md` promoted index snippets when their full `skill/promoted/*.md` cards
are present, avoiding duplicate promoted skill context.

Build an agent-ready context pack from the generated repository:

```bash
memu-context memory_repo --query "how should I answer this user?"
```

Machine-readable context pack or chat messages:

```bash
memu-context memory_repo --query "debug workflow" --json
memu-context memory_repo --query "debug workflow" --format summary
memu-context memory_repo --query "debug workflow" --format messages
memu-harness refresh memory_repo --query "debug workflow" --format system
```

Write the rendered context to a stable file for an agent or script:

```bash
memu-context memory_repo \
  --query "debug workflow" \
  --format system \
  --output context.system.md

memu-harness refresh memory_repo \
  --query "debug workflow" \
  --json \
  --output context-refresh.json
```

For large repositories, reserve or cap individual memory buckets so one category
does not crowd out the others:

```bash
memu-context memory_repo \
  --query "debug workflow" \
  --bucket-max soul=1000 \
  --bucket-max skill=2000
```

`bucket_char_limits` and `used_chars_by_bucket` are included in JSON and summary
outputs so agents can inspect context-budget pressure.

Record an execution trace for self-evolving skills:

```bash
memu-skill-trace raw_data \
  --task "Fix failing compiler tests" \
  --outcome success \
  --action "Read failing test output" \
  --action "Patch the affected module" \
  --lesson "Run focused tests after changing compiler behavior" \
  --tool "pytest:success:0.9" \
  --output-folder memory_repo
```

The trace is written under `raw_data/skill_traces/`. Because it is raw evidence,
a normal `memu-folder` compile or `--watch` run converts it into Evolution
Instructions and Patch Proposals before any approved skill update reaches
`skill.md` or `skill/`.

Python:

```python
import asyncio
from memu import FolderMemoryCompiler


async def main() -> None:
    compiler = FolderMemoryCompiler()
    result = await compiler.compile(
        source_folder="path/to/uploaded-folder",
        output_folder="path/to/memory-repo",
    )
    print(result.processed)


asyncio.run(main())
```

With an existing `MemoryService`:

```python
from memu import FolderMemoryCompiler, MemoryService

service = MemoryService(...)
compiler = FolderMemoryCompiler(memory_service=service)
```

Use the high-level context harness API when one object should own ingestion,
context assembly, watching, and skill evolution:

```python
import asyncio
from memu import ContextHarness, SkillToolTrace


async def main() -> None:
    upload_harness = ContextHarness(
        source_folder="path/to/uploaded-folder",
        repo_dir="path/to/memory-repo",
    )
    upload_harness.scaffold(copy_source=True)

    harness = ContextHarness.from_repo("path/to/memory-repo")
    run = await harness.refresh_context(query="current agent task")
    system_context = run.context_pack.to_markdown()

    await harness.record_skill_trace(
        task="Validate generated context packs",
        outcome="success",
        tools=[SkillToolTrace(name="memu-context", success=True, score=0.95)],
        lessons=["Check generated skill sections before injecting context into an agent."],
    )
    suggestions = harness.suggest_skills(min_support=1)
    print(system_context)
    print([suggestion.title for suggestion in suggestions])


asyncio.run(main())
```

`ContextHarness.from_repo(...)` uses `repo/raw_data` as the source folder and
applies `.memu/harness.json` defaults for compiler excludes, text evidence
limits, selected context buckets, total context budget, and per-bucket budgets.
Explicit Python method arguments still override those repo defaults. If a
custom `FolderMemoryCompilerConfig` is provided, non-default fields are
preserved while repo config can still fill compiler defaults such as
`exclude_patterns` and `max_text_chars`. `ContextHarness.health()` reports
invalid `.memu/harness.json` values as health errors; normal compile/context
operations fail until the config is fixed.

Load context in Python:

```python
from memu import MarkdownMemoryRepository

repo = MarkdownMemoryRepository("path/to/memory-repo")
pack = repo.build_context_pack(query="debugging style", max_chars=4000)
messages = pack.inject_into_messages(messages)
context_only_messages = pack.to_messages()
budgeted = repo.build_context_pack(
    query="debugging style",
    max_chars=8000,
    bucket_char_limits={"soul": 1000, "skill": 2000},
)
```

Record a skill trace in Python:

```python
from memu import SkillToolTrace, promote_skill, record_skill_trace

record_skill_trace(
    "raw_data",
    task="Validate generated context packs",
    outcome="success",
    actions=["Compile folder", "Build context pack", "Check skill sections"],
    tools=[SkillToolTrace(name="memu-context", success=True, score=0.95)],
    lessons=["Validate context packs before relying on generated skills."],
)

promote_skill(
    "memory_repo",
    title="Validate Context Packs",
    when_to_use="Before injecting generated context into an agent.",
    actions=["Build the context pack", "Check manual and generated skill sections"],
    lessons=["Inspect promoted skills before relying on generated context."],
)
```

## Incremental Update

`.memu/manifest.json` records each source file's path, hash, modality,
evidence path, generated entry IDs, and the latest self-evolve audit chain. On
recompile:

- unchanged files are skipped;
- changed files are re-extracted;
- changed media sidecars re-extract their paired media source;
- removed files create delete proposals; approved delete proposals remove
  generated Markdown and generated evidence;
- `raw_data/` is synchronized to match the current input folder.
- files matching configured `exclude_patterns` are ignored during scan, status,
  watch fingerprinting, sidecar pairing, and raw-data copy.

Manual Markdown files under `memory/`, `soul/`, and `skill/` are preserved. If a
generated per-source detail file becomes stale but contains manual notes outside
the generated block, memU clears the generated block instead of deleting the
file.

This makes the generated memory repository portable, inspectable, and suitable for version control.
