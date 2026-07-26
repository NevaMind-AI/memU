ADR 0013: Self-Updating Instruction Templates

- Status: Accepted
- Date: 2026-07-25
- Builds on: ADR 0008 (two host seams — record and inject), ADR 0012 (config in
  `~/.memu`, one shared backend selector)
- Scope: how the agent-facing instruction *text* the SDK carries — the three
  self-evolve job templates and the retrieval body — stays current between SDK
  releases. It changes neither the bridging pipeline's structure nor the host
  command surface.

## Context

Four blocks of text drive the agents memU steers, and all four ship embedded in
the SDK as Python string constants:

- `MEMORY_JOB_TEMPLATE`, `SKILL_JOB_TEMPLATE`
  (`memu/hosts/bridging/instructions.py`) and `RESOURCE_JOB_TEMPLATE`
  (`memu/hosts/bridging/resources.py`) — the **job templates**, filled with
  concrete paths at `prepare` time and handed to the self-evolve agent.
- `RETRIEVAL_BODY` (`memu/hosts/instruction.py`) — the **retrieval body**,
  installed into a host's `SKILL.md` or its managed instruction block, and read
  by the agent on every turn. The server publishes it as a *full skill document*
  (`retrieval-skill.txt` — frontmatter, `# Retrieve…` heading, and body): a skill
  host writes it verbatim, and an inline host carves out just the body
  (`_skill_body`) to slot into its own managed block.

Embedded text is a floor, not a ceiling. A wording fix or a better mining prompt
cannot reach an install until that install upgrades the SDK, and installs upgrade
rarely. We want these four to track a server-hosted copy so an improvement
reaches the field without a release — while never becoming *dependent* on the
server, since the embedded copy is always shippable-correct.

The two kinds of template are consumed on very different duty cycles, which the
design must respect:

1. **Job templates** are read only on the `prepare` run — hourly-to-daily,
   latency-tolerant, off the user's interactive path. Pulling every run is fine.
2. **The retrieval body** backs a file the host re-reads every turn, and the
   `retrieve` command runs on that same per-turn hot path. It must never fetch
   there. But its durable copy already lives on disk (the installed `SKILL.md` /
   managed block), so it needs refreshing only occasionally.

## Decision

### One fail-open resolver, `memu/hosts/templates.py`

A single module fetches `https://memu.pro/sdk/instructions/<name>.txt` for the
four names `memory-job`, `skill-job`, `resource-job`, `retrieval-skill`, and is
**fail-open by construction**: a missing network, a non-200, an oversize body
(> 64 KiB), or a malformed template all collapse to "fall back". No call raises.

The base URL defaults to `https://memu.pro/sdk/instructions` and is overridable
with `MEMU_TEMPLATE_BASE_URL`; setting it empty switches remote refresh off
entirely (air-gapped installs, offline CI, the test suite).

The `/sdk/` path segment marks these as SDK-consumed assets, not a human-facing
page. There is deliberately **no version segment today** (see Open issues).

### Validation is the trust boundary

These templates are instructions an autonomous agent executes with shell access,
and the job templates are `str.format()`-ed with concrete paths downstream. A
server-side typo must therefore be rejected before it is trusted, never carried
into a job file where `.format()` would raise mid-run. A fetched template is used
only if it is non-empty, contains every required `{placeholder}` for its name,
and `.format()`-s cleanly against exactly those keys — which rejects a dropped
placeholder, a stray brace, and an unknown field alike. The same check re-runs on
every cache read, so a truncated or hand-edited cache file is treated as absent.

### Two fallback shapes, matched to the two duty cycles

- **`resolve(name, embedded)` — server → last-good cache → embedded.** Used for
  the job templates at `prepare` time. A validated fetch also writes the text to
  a local last-good cache (`~/.memu/cache/instructions/<name>.txt`, shared across
  hosts since the templates are host-agnostic). The cache is what makes a
  *transient* outage a non-event: once an install has seen `v1`, a later day
  whose pull fails still runs `v1` rather than regressing to the embedded `v0`.

- **`fetch(name)` — server only, no cache.** Used for the retrieval skill
  (`retrieval-skill`), served as a full `SKILL.md` document. Its durable copy is
  not a cache but the file already installed on disk, so there is nothing extra to
  cache. `install-instruction` uses `fetch(...) or embedded` (an explicit, one-off
  command; the embedded floor is correct when the server is down mid-install). The
  scheduled refresh (below) uses `fetch(...)` and **skips the write entirely on
  `None`**, so a transient outage leaves the already-installed — and newer — copy
  in place rather than downgrading it.

### The retrieval body refreshes on the bridging schedule, never on retrieve

`instruction.refresh()` rewrites whatever holds the retrieval body — the
`SKILL.md` on a skill host (the server document verbatim), the inline managed
block on an inline host (just the body, carved out of that document by
`_skill_body`) — and is called from `_cmd_prepare`. This piggybacks the refresh on the low-frequency
`prepare` run the host already schedules, giving the "larger interval" the hot
path requires for free, with no timestamp bookkeeping. It is **best-effort**
(a failure is a note, never a failed `prepare`), **skip-not-downgrade** (see
above), and **refresh-not-bootstrap** (it does nothing where nothing is
installed yet — installing remains `install-instruction`'s job, so a scheduled
run never creates files a user did not ask for).

## Consequences

Positive:

- A prompt improvement reaches every install on its next `prepare`, without a
  release.
- The embedded copy remains a guaranteed floor; the server is pure upside and
  never a runtime dependency. A total outage degrades to embedded, never to
  nothing.
- The per-turn `retrieve` path is untouched — it still performs no network I/O
  for templates.
- A malformed server template cannot crash the pipeline or reach an agent.

Costs / limitations:

- `prepare` now makes up to four short, timeout-bounded HTTP calls per run. This
  is acceptable on its duty cycle and fully disabled by `MEMU_TEMPLATE_BASE_URL=""`.
- The server copy is trusted after structural validation but is **not
  cryptographically verified** (see Open issues).

## Open issues

- **No version numbers on the cache (deliberate, for now).** The last-good cache
  keeps *the last text seen*, not *the newest by version*. One regression follows
  from this: if the SDK is upgraded while the server is unreachable, a cached
  older-server copy can momentarily win over a newer embedded template, because
  nothing lets the resolver compare their ages. We accept this because it
  self-heals on the next successful pull — and a release publishes the matching
  server copy, so that pull is imminent — and because it can only affect the
  low-frequency job templates for at most a run or two (the retrieval body is
  uncached, so it is immune). The fix, when the infrastructure is ready, is a
  monotonic version integer on each template so the offline branch can pick the
  newest of {cache, embedded} while a reachable server stays authoritative
  (letting deliberate rollbacks still win). Not built yet.

- **No signing / integrity verification.** Because these templates are executed
  by an agent with shell access, a compromised `memu.pro/sdk/instructions/…` is a
  meaningful supply-chain surface. Today's guards are HTTPS, a pinned host, a size
  cap, and structural validation. Shipping a public key in the SDK and verifying
  a detached signature over each template is the recommended hardening.

- **No URL schema-version segment.** The placeholder set each template requires
  is a contract between the server copy and the installed SDK. Today an old SDK
  that fetches a server template needing a new placeholder simply rejects it in
  validation and falls back — safe, but it silently forgoes the upgrade. A `/v1/`
  segment bumped only when the placeholder contract changes would let the server
  serve contract-compatible copies per SDK generation. Cheap to add later; left
  out now to keep the first cut simple.

## Out of scope

- Versioned or signed template distribution (tracked above).
- Any change to what the templates *say* — only to how they are delivered.
- The bridging pipeline's prepare → self-evolve → commit structure (ADR 0008).
- Backend selection and cloud/local execution (ADR 0012).
