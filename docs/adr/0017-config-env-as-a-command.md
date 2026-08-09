ADR 0017: `config.env` Is Written by a Command, Not by the Agent — `init` for the Entry, `config` for the Detail

- Status: Proposed
- Date: 2026-08-05
- Builds on: ADR 0009 (the CLI seam and one config loader), ADR 0010 (multi-host
  adapters, one shared parser from a `HostSpec`), ADR 0012 (cloud/local backend
  selection, config in `~/.memu`), ADR 0013 (server-refreshable agent-facing
  docs), ADR 0016 (client event reporting, the install funnel)
- Scope: who writes `~/.memu/config.env` during an install, and through what
  command surface. It changes neither seam's behaviour, the store, the schema of
  the file, nor `env.py`'s resolution order — only the mechanism that produces
  the file and the two guides that drive it.

## Context

The install pipeline has three steps today:

1. `SKILL.md` — the entry document. Tells the agent to `pip install memu-cli`
   and pick its host binary.
2. `<binary> docs install` — prints the packaged, server-refreshable guide.
3. `INSTALL.md` — the guide, followed top to bottom.

`~/.memu/config.env` is created in step 3, by the agent, from prose. Two
problems follow from that placement.

**The file is written by hand.** `INSTALL.md` §1.2 tells the agent which keys to
write and the agent writes them, typically with a heredoc or `echo >>`. That file
is shared across every host on the machine, carries a plaintext credential, and
holds an invariant the guide can only state in words: record and inject must
agree on the backend, and in local mode on the DSN and embedding space too, or
retrieval silently returns nothing (ADR 0009's opening argument). The guide
already spends a paragraph on "repair the connection, never the identity" —
`MEMU_DB`, `MEMU_EMBED_PROVIDER`, `MEMU_EMBED_MODEL` must never be edited on an
existing store — and enforces it with nothing but emphasis. Field behaviour
matches the exposure: agents occasionally rewrite the file rather than merge into
it, taking unrelated keys with them.

This is the same argument that produced `install-instruction`. memU owns the
retrieval block's text, so memU writes it; the guide's instruction is "do not
hand-write this". `config.env` is a strictly harder file — merge semantics, a
secret, a cross-host invariant — and has no such command.

**The install-start event fires before the key exists.** `_report_install_started`
(ADR 0016 §4) is emitted from `docs install`, because printing the guide is the
first act on the install path that proves `memu-cli` resolves. On a first install
that happens in step 2, before step 3 has collected the memU Cloud key, so the
event goes out with no `Authorization` header and lands unattributed.

This second problem is **less severe than it first appears, and should not be the
sole justification for this ADR.** Every envelope already carries
`client_instance_id`, and `client_instance_id()` generates *and persists* the id
into `config.env` on first use — so the unattributed start already carries a
stable id that every later authenticated event on that machine reuses. The
backend can join anonymous → account on it retroactively. What ordering fixes is
attribution *at emission* — and it is what would let a later release fail fast on
a wrong key, which this one does not attempt (see Open issues).

The obvious alternative for the ordering — spool the start event without flushing
and let a later flush attach the key — is rejected: the flush at `docs install`
exists precisely so an install that dies in Part 2 still reports its start, and
those are the runs the event was added for.

## Decision

### Two verbs over one writer

`<binary> init` and `<binary> config`, registered on the shared host parser
(`host_cli.build_parser`) so every host adapter gets both, backed by **one** merge
function whose guard policy is a parameter. `init` is the inferring front door;
`config` is the explicit one. They must not each own a code path for
`MEMU_CLOUD_API_KEY`, or the two will drift within a release.

```
<binary> init [--cloud-api-key K]                    # entry; named in SKILL.md
<binary> config show                                 # read-only; the preflight probe
<binary> config --cloud [--cloud-api-key K] [--cloud-base-url URL] [--force]
<binary> config --local [--db PATH] [--embed-provider P] [--embed-api-key K]
                        [--embed-base-url URL] [--embed-model M] [--force]
```

`--force` is on `config` only, and `init` needs none: it never refuses, so there
is nothing to override. That is not a weaker contract than `config`'s but a
different one, and the reason is where each verb sits — see "`init` never
refuses" below.

The split is not cosmetic — the two verbs have different *policies*, and the
place each is named is the reason:

- `SKILL.md` is the least updatable surface memU has. It ships to users, is
  pasted into repos, and — unlike `INSTALL.md` — does not go through
  `templates.resolve_doc`, so it cannot be refreshed from the server (ADR 0013).
  Anything named there needs a contract expected to hold for years. `init` with
  at most one flag is that. A verb whose flag surface grows every time local mode
  gains a knob is not.
- `INSTALL.md` *is* server-refreshable, so `config`'s flag surface can evolve at
  the server's pace.
- Folding both into one verb is what produces the trap in the next section.

### `init` — infers, and hands back what it cannot infer

Zero or one flag, idempotent, safe to run on any machine in any state:

- `init --cloud-api-key K` — the user provided a key, which *is* the choice of
  cloud. Sets `MEMU_MEMORY_MODE=cloud` and persists the key, whatever the file
  said before.
- `init` — no key offered. If the file already declares `MEMU_MEMORY_MODE`,
  **keep it**: a re-install where the user did not re-supply a key must not flip
  cloud to local. If absent, set `local`.
- In every case, generate and persist `MEMU_CLIENT_ID` if missing.

#### `init` never refuses

Not "rarely" — never. Bare `init` has nothing to refuse *on*: every branch it
takes either keeps what is there or fills a vacuum. `init --cloud-api-key` on a
machine already configured for local with `MEMU_DB` set is the one case that
looks like it should, and it does not either. Three reasons, in order of weight:

- **A refusal there is terminal.** `init` has no `--force`, and it is the *first*
  command on the install path — the one `SKILL.md` names before `docs install`.
  Exiting non-zero does not redirect the agent to a better command so much as
  stop the install, and every step after it, on a machine whose user has just
  handed over their key.
- **The signal is unambiguous.** Having a memU Cloud key in hand and passing it
  is about as explicit as intent gets at this point in the flow. Treating it as
  something the caller might not have meant reads the situation wrong.
- **Nothing is destroyed.** The local store is not touched: `MEMU_DB` stays in
  the file and the rows stay in the database, unread until the mode is switched
  back with `config --local --force`. What the flip costs is that memories
  written locally stop being retrieved, and new ones go to the key's cloud
  account instead — real, reversible, and exactly the kind of consequence a
  warning is for.

So `init` says it, loudly, and proceeds: a `switched` row beside the mode, and a
fuller `warning:` on stderr naming what happened and the command that undoes it.
The guides carry the same consequence in prose where they ask for the key.

This is the one place `init` and `config` are allowed to disagree about the same
state test, and the asymmetry is the point: `config`'s caller named a backend and
can be handed `--force`, so refusing them costs one re-run. `init`'s caller has
no such second move.

Writing `MEMU_MEMORY_MODE=local` explicitly, rather than relying on
`memory_mode()`'s compatibility default, also retires the ambiguity `INSTALL.md`
currently has to explain in prose ("an existing file without `MEMU_MEMORY_MODE`
is local mode for backward compatibility"). It is safe to write into a file that
was silent on the question — including one carrying a `MEMU_CLOUD_API_KEY`,
which looks like a cloud install being demoted but is not: `memory_mode()`
already resolves that file to local today, so `init` records the mode the machine
was already in rather than changing it.

### `config` — explicit, and refuses ambiguity

`--cloud` or `--local` is **mandatory** to touch `MEMU_MEMORY_MODE`. This is the
verb `INSTALL.md` §1.2 drives once the user has actually chosen a backend, and
the only verb that configures the local-mode knobs.

`config --local` with no `--db` is **allowed**, and writes the mode alone. The
alternative — requiring `--db` whenever none is set — would put the refusal in
the wrong place: this verb runs inside `INSTALL.md`, where the agent is already
in a conversation with the user about the store and can ask. A mode with no
store fails the Part 1 verify gate loudly, which is the right amount of
enforcement for a value only the user can supply.

### `config show` — the read side, and the preflight probe

Prints the resolved mode and the keys that are set (never their values, beyond
`set`/`unset` for anything credential-shaped), and writes nothing. This is the
"is the backend already configured" question that `INSTALL.md`'s preflight and
§1.2's opening `if already configured, skip` both ask, and it is why the read
side is a *named* subcommand: a bare `config` that printed while a bare `init`
wrote is exactly the asymmetry agents get wrong.

### The one-backend guard is state-based, not declaration-based

This is the load-bearing decision, and without it the whole design has a hole.

If `MEMU_MEMORY_MODE` were an identity key guarded on declaration alone, the most
ordinary first install breaks: the agent runs bare `init` in step 2.5 (the user
had not found their key yet), `local` lands on disk, the guide then asks the
backend question, the user says cloud — and `config --cloud` is refused as a mode
flip. Once written, an *inferred* default is indistinguishable from a *chosen*
one, and a declaration-based guard can only see the file.

What the invariant actually protects is existing memory, not a string. So a mode
change is refused only when the current mode has something to lose — and only on
`config`, which is the verb that can offer the override:

| Current state | `config --<other-mode>` |
| --- | --- |
| `local`, `MEMU_DB` set | refuse without `--force` |
| `cloud`, `MEMU_CLOUD_API_KEY` present | refuse without `--force` |
| anything else (a vacuous declaration) | change it silently — this is the first real choice |

**"Has something to lose" is judged by declaration of the store, not by the
store's contents.** `MEMU_DB` being set is enough; whether the file exists, or
holds one memory or ten thousand, is not asked. `MEMU_DB` spans a bare path, a
`sqlite://` URL, a `postgres://` DSN and the in-memory sentinel
(`env.database_config`), so "the store exists" has no single cheap meaning —
and the one shape where it is cheap, a local SQLite file, is also the shape
where `database_config` *creates the parent directory as a side effect* of
being asked. A guard that mutates the filesystem to answer a question is worse
than a guard that over-refuses, and over-refusing costs one `--force` on a path
where the agent is already talking to the user.

**The state the guard reads is the file, never the resolved environment.** Every
other consumer in this codebase asks `env.env()`, which consults `os.environ`
first — correct for *resolving* config, wrong for *deciding what is on disk*. An
exported `MEMU_CLOUD_API_KEY` in the calling shell would otherwise make
`config --local` refuse a file that never declared anything, and `init`'s
"already set, keep it" would preserve a mode nobody ever wrote. So the writer and
the guard take the parsed dotenv as their only input, and the process
environment reaches neither.

`MEMU_DB`, `MEMU_EMBED_PROVIDER` and `MEMU_EMBED_MODEL` keep an *unconditional*
guard: those three bind an embedding space that already has vectors in it, and
"fixing" one silently strands every existing vector. Unconditional means no state
test, not no escape — `--force` still overrides, and must, because the
alternative to a supported override is the user hand-editing the file, which is
the thing this ADR exists to stop. Setting one of the three where none was set is
not a change and needs nothing. Connection-level keys
(`MEMU_CLOUD_BASE_URL`, `MEMU_BASE_URL`, `NO_PROXY`) are freely updatable — this
is the guide's existing "repair the connection, never the identity" rule, moved
from prose into a gate.

Two cases the inference rules do not cover on their own, settled here:

- **`init --cloud-api-key K` when the file says `local`.** This is a mode flip by
  inference, and `init` makes it in every case: a vacuous local config flips
  silently, a local config with `MEMU_DB` set flips with the warning described
  under "`init` never refuses". The same state test still decides *whether to
  warn*; it just does not decide whether to act.
- **`init --cloud-api-key K2` when `K1` is stored.** Replace it, and say so
  loudly ("replacing the stored memU Cloud key"). Refusing would block the
  legitimate rotated-key repair, and the client cannot distinguish a rotation
  from a different account. Announcing it is the honest middle.

### File mechanics

Merge, never rewrite. Parse the existing file, set only the named keys, leave
every other line and comment byte-identical, write to a temp file and
`os.replace`, `mkdir(0700)` the directory and `chmod 600` the file, then
`env.reload()`.

**One writer, for every key — including `MEMU_CLIENT_ID`.** `events.client_instance_id()`
already writes that key today, by appending to the file with no atomicity and no
permissions, and deliberately re-reading afterwards so two racing first runs
converge. Left alone it becomes a second mechanism for the same file, and a
worse interaction than duplication: this section's read-modify-write plus
`os.replace` *silently discards* a concurrent append. So `client_instance_id()`
moves onto this writer, keeping the two properties it was built with — it
swallows `OSError` and still returns an id, and it re-reads rather than trusting
what it wrote. That places the writer where `events` can import it without
reaching into `memu.hosts`.

**Permissions are reported as what actually happened.** `chmod 600` restricts
nothing on Windows — `os.chmod` there moves the read-only bit and no ACL — so
claiming it on that platform would replace an instruction the agent might follow
(today's guides say to restrict the file to the current user) with a line
asserting a protection that does not exist. POSIX chmods and says so; Windows
says the file holds a plaintext key and that its ACLs are inherited. Doing the
real thing there means shelling out to `icacls`, which is a subprocess and a new
failure mode on the install path; not worth it for a claim, and the honest line
leaves the door open to adding it later.

**Do not persist defaults.** `MEMU_CLOUD_BASE_URL` is written only when it
differs from `DEFAULT_CLOUD_BASE_URL`; baking today's default into the file
freezes a value the code should own across upgrades. Note also that
`MEMU_BASE_URL` is the *embedding* endpoint (local mode) and has no role in cloud
configuration — the two are easy to conflate.

### Flag naming follows the variable

`--cloud-api-key`, not `--api-key`. The codebase deliberately separates
`MEMU_CLOUD_API_KEY` (memU Cloud) from `MEMU_API_KEY` (the embedding provider),
and `INSTALL.md` has to warn against confusing them. A bare `--api-key` re-opens
that door on the one surface meant to close it. Local mode's embedding credential
is `--embed-api-key` for the same reason.

### Neither verb verifies — `doctor` stays the only prover

`init` and `config` report what is *declared*. `doctor` remains the only command
that proves the backend answers, and Part 1's verify gate remains where a wrong
key is caught.

Verifying the key inside `init --cloud-api-key` was considered and deferred (see
Open issues). Two reasons. The key is usually pasted from memU's own website
alongside the install instruction, so a *wrong* key is a rarer failure than the
design was weighting it as; and where an agent does garble one, the recovery is
already specified — a later `init --cloud-api-key K2` replaces it loudly.

The ordering argument is worth stating precisely, because it is what makes
deferring safe: verification must run **before** the write, not after. A
write-then-verify `init` leaves `cloud` plus a bad key on disk when it fails,
and that is exactly the state the guard table reads as "cloud, key present —
refuse without `--force`". The user who then abandons cloud and asks for local
hits a refusal on the most ordinary first install, which is the failure the
state-based guard exists to eliminate. Nothing needs to be on disk to verify —
the cloud client takes its base URL and key as arguments — so whenever
verification is added, it is added ahead of the write.

### Refusals are an exit code, not an exception

A guard refusal returns a distinct non-zero status (`2`, as `prepare` already
uses for a missing session log) from the handler. It must not raise: `host_cli.run`
catches exceptions into `record_cli_error` and flushes, which would file every
ordinary "you meant `--force`" into the error feed as if memU had broken.

### Output is the agent's next-step signal

Decisive lines, not a diff:

```
mode      cloud (from --cloud-api-key)
key       set
client    a1b2… (generated)
config    ~/.memu/config.env (chmod 600)
ready — continue with `memu-claude-code docs install`
```

and for the bare case, `mode local (default; no store configured yet)` plus a
pointer that `docs install` will guide the rest. On Windows the `config` line
reads `…\.memu\config.env (plaintext key; Windows ACLs inherited)` — see File
mechanics.

A `config` refusal prints the same shape: what is on disk, why it is protected,
and the exact `config … --force` to run if the change was meant. An `init` that
flipped a machine off a configured local store prints that shape too — a
`switched` row in the block, then the consequence and the `config --local
--force` that reverses it — but exits `0`, because it did the thing.

### On the host binaries, not `memu`

`memu` is the algorithmically correct home — `config.env` is host-irrelevant, and
ADR 0009 makes `memu` the algorithm surface with the adapters as sidecars. It is
nonetheless the wrong choice here. The install flow's ergonomic bet is that
`SKILL.md` Step 2 hands the agent exactly *one* binary name and every later step
is `<your-binary> …`; a second binary mid-flow adds a branch, a fresh
"command not found" mode, and a name far likelier to be shadowed on `PATH` than
`memu-claude-code` is. `doctor` is already just as host-irrelevant in substance
and lives on the host binaries for this reason. A thin `memu init` alias over the
same module is acceptable, but the guides name only `<your-binary>`.

### Guide changes

- **`SKILL.md`** gains a Step 2.5 between binary selection and `docs install`:
  ask the user for their memU API key, then run
  `<your-binary> init --cloud-api-key <key>`; no key → bare `<your-binary> init`.
  The prose stays minimal on purpose — everything that might change lives in the
  command's own output — with one exception it must state, because the command
  states it only *after* acting: passing a key on a machine already using local
  memory switches it to the cloud, and the local memories stop being retrieved.
- **`INSTALL.md` §1.2** collapses from ~70 lines of write-these-keys instruction
  to "if already configured, skip; otherwise `config --cloud|--local …`". The
  local-mode knobs and the no-embedding-key fallback survive as guidance for
  *choosing arguments*, not for writing the file.
- **Preflight** gains a cheaper probe: `<binary> config show` as the one-shot "is
  the backend configured" question, replacing the file test and the
  `MEMU_MEMORY_MODE` grep the preflight blocks do by hand today.

There are seven guides carrying this section, not one: six hosts head it
`### 1.2 Configure the memory backend`, the generic adapter has it as its
`## Part 1`, and Cola states it in prose with no heading. All seven change.

**The guides ship ahead of the code they name, and must not.** `docs install`
prefers the *server's* copy of `INSTALL.md` over the packaged one
(`templates.resolve_doc`, ADR 0013), so the moment this text is published
server-side every machine still on an older `memu-cli` is handed a guide telling
it to run a subcommand its binary does not have — argparse answers `invalid
choice` at the first step of Part 1. The server-side publish is therefore gated
on the release that carries the commands, and the new §1.2 keeps a line pointing
an agent that hits that error at upgrading `memu-cli`.

## Consequences

Positive:

- The cross-host invariant is enforced by code on the one file that carries it,
  instead of by emphasis in a document.
- Unrelated keys, comments, and another host's settings survive a re-install.
- Permissions and atomicity stop depending on the agent remembering `chmod 600`.
- The install-start event carries the key when the user had one to give.
- `MEMU_CLIENT_ID` exists before anything reports, rather than being appended by
  whichever event happened to fire first.
- `SKILL.md`'s command surface becomes something we expect never to change.

Costs / limitations:

- Two more verbs on every host binary, and a required-input prompt (the backend
  choice) moves into `SKILL.md` — the surface we cannot refresh from the server.
- The key lands in `argv`, so it is visible to `ps`, shell history, and the
  session transcript. Not a regression — the heredoc it replaces is equally
  exposed — but see Open issues.
- One more command in a flow whose main failure mode is agents skipping steps.
  `init` is idempotent and cheap, which is the mitigation, not a guarantee.
- `init --cloud-api-key` can strand a local store behind a warning nobody read.
  This is the deliberate trade in "`init` never refuses", and it is the one place
  where the safer behaviour was traded away for a flow that completes. The store
  survives and one `config --local --force` restores it, so the cost is confusion
  and a stretch of unretrieved memories rather than data loss — but the warning
  is all that stands between the two, and warnings are read less often than exit
  codes are.

## Open issues

- **The credential is in `argv`, and memU mines transcripts.** The record seam
  reads the very session log that will contain `init --cloud-api-key sk-…`.
  Accepting `MEMU_CLOUD_API_KEY` from the process environment, and
  `--cloud-api-key -` to read one line from stdin, are both cheap to add; agents
  are unreliable with stdin, so the flag stays primary. Whether the bridging
  pipeline should additionally redact key-shaped strings from mined transcripts
  is a separate question this ADR does not settle.
- **Nothing checks the key until Part 1's gate.** Deferring verification (above)
  costs the earliest failure point: a garbled key now survives `init`, survives
  `docs install` — whose install-start event it is attached to — and dies at
  `doctor`, several steps and one wasted funnel event later. Accepted for now
  because keys are copied, not typed, and because a re-`init` repairs one. When
  it is added: **before** the write, never after, for the guard-state reason
  given above, and reusing `doctor`'s call rather than inventing a second one.
- **Where the install-start event belongs.** This ADR only reorders the existing
  emission at `docs install`. Moving it into `init` — the first command on the
  install path that knows both the host and the key — is defensible and would
  make attribution unconditional, but `docs install` is the point that proves the
  package resolves, and re-running `init` on an already-configured machine is a
  weaker signal of "an attempt started". Left as is until the funnel data says
  otherwise.
- **Local mode's flag surface will grow.** Every new local knob is a new `config`
  flag. Acceptable while `INSTALL.md` is refreshable, but if the count keeps
  climbing, a `config set KEY=VALUE` form will be tempting — and would forfeit the
  identity-key guard, which is the reason for named flags.

## Out of scope

- The schema of `config.env` or `env.py`'s resolution order (ADR 0009/0012).
- Anything the guides *say* about choosing a backend — only who writes the result.
- The bridging pipeline, the instruction seam, and `install-instruction`.
- The event envelope and transport (ADR 0016); this ADR only changes when one
  event is emitted relative to the config being written.
