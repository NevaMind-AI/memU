# Uninstall memU (generic `memu-agent`)

> **Audience: the agent.** A user has pointed you at this file ("follow this
> guide to uninstall memU"). Work top to bottom. Each part ends with a
> **verify** gate — do not proceed until the current one passes.

Uninstalling is the install run in reverse, and it is three parts:

1. **Unregister the bridging task** — stop the scheduled job first, so nothing
   fires mid-teardown (the *record* seam).
2. **Unpatch the instruction file** — remove the standing retrieval
   instruction from wherever `memu-agent install-instruction` put it (the
   *inject* seam).
3. **Decide about the data and the package** — the store is the user's
   accumulated memory; deleting it is their call, never yours.

A retrieval-only integration (detect found no recognizable session log, so no
bridging task was ever registered) simply has no Part 1 — skip to Part 2.

**One store, many hosts.** `~/.memu/config.env` and the store it names may be
shared by other memU host adapters on this machine (`memu-claude-code`,
`memu-codex`, …). Removing *this* host's seams never requires touching the
shared store; Part 3 spells out when touching it is safe at all.

---

## Part 1 — Unregister the bridging (record) task

Find where the bridging run was scheduled at install time — the agent's own
scheduler if it has one, otherwise a system cron entry — and delete **that
entry only**. Its prompt is recognizable: the three-step block running
`memu-agent prepare --session-dir …`, the job files, then `memu-agent commit`.
Everything else in the scheduler is the user's and stays; for cron:
`crontab -l | grep -v 'memU bridging pipeline' | crontab -`.

### ✅ Verify Part 1

The scheduler (crontab or the agent's own) no longer lists a memU bridging
entry, and everything unrelated is still there.

---

## Part 2 — Remove the retrieval instruction

**Do not hand-edit the block out.** memU owns the text and removes it for you.
From the project root whose `AGENTS.md` was patched (repeat per project if it
was installed into several):

```
memu-agent remove-instruction
```

(or `memu-agent remove-instruction --path <file>` for whatever file
`install-instruction --path` targeted). It deletes memU's marked block and
prints the diff. Everything outside the markers is the user's and survives;
the previous contents are backed up to `<file>.bak` before the rewrite.
`--dry-run` shows the diff without writing. Re-running is a clean no-op — a
file with no block left is already the desired end state.

### ✅ Verify Part 2

Each patched instruction file shows no `memu:begin`/`memu:end` markers, and
the user's own content is intact.

---

## Part 3 — The data, the config, and the package (ask first)

Everything in this part is **opt-in: ask the user, then act.** The safe
default is to keep data.

- **This host's working tree** — `~/.memu/hosts/agent/` (or the `--base-dir`
  chosen at install time, for a named generic agent) holds only run-scoped
  state (job files, session cursors, mirrors). Safe to delete once Parts 1–2
  are done. The agent's own session log belongs to the agent — memU only ever
  read it; leave it alone.
- **The store and `~/.memu/config.env`** — shared by every host adapter on
  the machine. Delete only if the user says so **and** no other host adapter
  is still integrated. Warn first, in plain words: the store *is* their
  accumulated memory, and deleting it is irreversible.
- **The package** — once no host on this machine uses memU any more:
  `pip uninstall memu-cli` (or `pipx uninstall memu-cli` — match how it was
  installed).

### ✅ Done

Report to the user exactly what was removed and what was deliberately kept:
the schedule (gone, or never existed for a retrieval-only integration), the
instruction (removed from which files), the store (kept where, or deleted),
the package (kept or uninstalled). If the store was kept, say so explicitly:
reinstalling later picks it right back up — memory survives an uninstall by
design.
