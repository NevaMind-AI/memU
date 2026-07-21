# Uninstall memU for Hermes Agent

> **Audience: the agent.** A user has pointed you at this file ("follow this
> guide to uninstall memU"). Work top to bottom. Each part ends with a
> **verify** gate — do not proceed until the current one passes.

Uninstalling is the install run in reverse, and it is three parts:

1. **Unregister the bridging task** — stop the scheduled job first, so nothing
   fires mid-teardown (the *record* seam).
2. **Unpatch `~/.hermes/SOUL.md` and remove the retrieval skill** — the
   standing instruction and the skill it points at (the *inject* seam).
3. **Apply the data-and-package defaults** — the user's memory is kept, the
   tooling is removed — and close by reporting both.

**One store, many hosts.** `~/.memu/config.env` and the store it names may be
shared by other memU host adapters on this machine (`memu-claude-code`,
`memu-codex`, …). Removing *this* host's seams never requires touching the
shared store; Part 3 spells out when touching it is safe at all.

---

## Part 1 — Unregister the bridging (record) task

Find the cron entry that runs the memU bridging pipeline — it invokes Hermes
headless with the three-step prepare / self-evolve / commit prompt — and
delete **only that line**. Everything else in the user's crontab is theirs and
stays, e.g. `crontab -l | grep -v 'memU bridging pipeline' | crontab -`. If
the memU line was the only reason a `PATH=` line was added, that line may go
too — but only if nothing else in the crontab needs it. If nothing at all
remains, `crontab -r` removes the now-empty crontab cleanly.

### ✅ Verify Part 1

`crontab -l` shows no memU bridging entry, and everything unrelated is still
there.

---

## Part 2 — Remove the retrieval instruction and skill

**Do not hand-edit the block out.** memU owns the text and removes it for you:

```
memu-hermes remove-instruction
```

It deletes memU's marked block from `~/.hermes/SOUL.md` and prints the diff.
Everything outside the markers is the user's and survives; the previous
contents are backed up to `~/.hermes/SOUL.md.bak` before the rewrite.
`--dry-run` shows the diff without writing. Re-running is a clean no-op — a
file with no block left is already the desired end state. If this install used
a non-default home (`HERMES_HOME`, or a profile), pass
`--path <home>/SOUL.md`.

The block pointed at the `memu-retrieve` skill; remove that too. The directory
is memU's own — the install wrote it whole, so it goes whole:

```
rm -r ~/.hermes/skills/memu-retrieve
```

(For a non-default home, it sits under `<home>/skills/` instead.) Other entries
in `~/.hermes/skills/` are the user's or Hermes's — leave them alone.

### ✅ Verify Part 2

`cat ~/.hermes/SOUL.md` — no `memu:begin`/`memu:end` markers remain, and the
user's own content is intact. `~/.hermes/skills/memu-retrieve` no longer
exists. A session already running loaded the old file; a fresh session is what
picks the removal up.

---

## Part 3 — The data, the config, and the package (defaults, then report)

No questions to ask here. Apply the defaults below, and make sure the final
report tells the user plainly what they got: **memory kept, tooling removed.**
Only one thing overrides a default: the user's own explicit words.

- **Keep the store and `~/.memu/config.env`.** Always. The store *is* the
  user's accumulated memory, and it survives an uninstall by design —
  reinstalling later picks it right back up. Delete it only if the user
  explicitly asked to erase their memory as part of this uninstall, and warn
  first, in plain words, that it is irreversible.
- **The session cursor lives and dies with the store.**
  `~/.memu/hosts/hermes/.session_manifest.hermes.json` records which
  session turns have already been mined *into that store*. Store
  kept (the default)? Keep the cursor — deleting it loses no memory, but the
  next install re-mines every old session for nothing. Store deleted at the
  user's request? Delete the cursor with it — a surviving cursor over an empty
  store marks history as already mined, and it would never be mined again.
- **Remove this host's residue.** Everything else under `~/.memu/hosts/hermes/`
  — job files and mirrors, sparing the session cursor above; and
  `~/.hermes/SOUL.md` itself **if** Part 2 left it
  empty (it held only memU's block, so the install created it) — a file with
  the user's own content stays, of course. Hermes's own `~/.hermes/state.db`
  belongs to Hermes, not memU — the adapter only ever read it; leave it alone.
- **Uninstall the package** — `pip uninstall memu-cli` (or `pipx uninstall
  memu-cli` — match how it was installed) — **unless** another host adapter is
  still integrated on this machine (another host's instruction file still
  carries a memU block, or its bridging task still exists). Then the package
  stays, and the report says which host is still using it.

### ✅ Done

Close the report with the two things the user needs to hear, in this order:

1. **What was kept:** their memory — the store at `MEMU_DB`,
   `~/.memu/config.env`, and the session cursor — untouched. A later reinstall
   picks it up as is and resumes mining right where it left off.
2. **What was removed:** the bridging schedule, the retrieval instruction and
   skill, this host's working state, and (unless another host still needs it)
   the `memu-cli` package.
