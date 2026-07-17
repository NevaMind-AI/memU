# Uninstall memU for Cursor

> **Audience: the agent.** A user has pointed you at this file ("follow this
> guide to uninstall memU"). Work top to bottom. Each part ends with a
> **verify** gate — do not proceed until the current one passes.

Uninstalling is the install run in reverse, and it is three parts:

1. **Unregister the bridging task** — stop the scheduled job first, so nothing
   fires mid-teardown (the *record* seam).
2. **Unpatch `AGENTS.md`** — remove the standing retrieval instruction from
   every project it was installed into (the *inject* seam).
3. **Decide about the data and the package** — the store is the user's
   accumulated memory; deleting it is their call, never yours.

**One store, many hosts.** `~/.memu/config.env` and the store it names may be
shared by other memU host adapters on this machine (`memu-claude-code`,
`memu-codex`, …). Removing *this* host's seams never requires touching the
shared store; Part 3 spells out when touching it is safe at all.

---

## Part 1 — Unregister the bridging (record) task

Find the cron entry that runs the memU bridging pipeline — it invokes
`cursor-agent -p 'Run the memU bridging pipeline. …'` — and delete **only that
line**. Everything else in the user's crontab is theirs and stays, e.g.
`crontab -l | grep -v 'memU bridging pipeline' | crontab -`. If the memU line
was the only reason a `PATH=` line was added, that line may go too — but only
if nothing else in the crontab needs it.

### ✅ Verify Part 1

`crontab -l` shows no memU bridging entry, and everything unrelated is still
there.

---

## Part 2 — Remove the retrieval instruction

Cursor's inject seam is per-project: install patched the `AGENTS.md` at each
project root where memU was set up. **Do not hand-edit the block out.** From
each such project root, run:

```
memu-cursor remove-instruction
```

(or `memu-cursor remove-instruction --path <file>` from anywhere). It deletes
memU's marked block and prints the diff. Everything outside the markers is the
user's and survives; the previous contents are backed up to `AGENTS.md.bak`
before the rewrite. `--dry-run` shows the diff without writing. Re-running is
a clean no-op — a file with no block left is already the desired end state.

Ask the user which projects memU was installed into if you cannot tell;
`grep -l 'memu:begin' */AGENTS.md`-style searches from their project parent
directories are a fair way to find stragglers.

### ✅ Verify Part 2

Each patched `AGENTS.md` shows no `memu:begin`/`memu:end` markers, and the
user's own content is intact.

---

## Part 3 — The data, the config, and the package (ask first)

Everything in this part is **opt-in: ask the user, then act.** The safe
default is to keep data.

- **This host's working tree** — `~/.memu/hosts/cursor/` holds only this
  adapter's run-scoped state (job files, session cursors, mirrors). Safe to
  delete once Parts 1–2 are done.
- **The store and `~/.memu/config.env`** — shared by every host adapter on
  the machine. Delete only if the user says so **and** no other host adapter
  is still integrated. Warn first, in plain words: the store *is* their
  accumulated memory, and deleting it is irreversible.
- **The package** — once no host on this machine uses memU any more:
  `pip uninstall memu-cli` (or `pipx uninstall memu-cli` — match how it was
  installed).

### ✅ Done

Report to the user exactly what was removed and what was deliberately kept:
the schedule (gone), the instruction (removed from which projects), the store
(kept where, or deleted), the package (kept or uninstalled). If the store was
kept, say so explicitly: reinstalling later picks it right back up — memory
survives an uninstall by design.
