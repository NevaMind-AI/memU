# Uninstall memU for Codex

> **Audience: the agent.** A user has pointed you at this file ("follow this
> guide to uninstall memU"). Work top to bottom. Each part ends with a
> **verify** gate — do not proceed until the current one passes.

Uninstalling is the install run in reverse, and it is three parts:

1. **Unregister the bridging task** — stop the scheduled job first, so nothing
   fires mid-teardown (the *record* seam).
2. **Unpatch `~/.codex/AGENTS.md`** — remove the standing retrieval
   instruction (the *inject* seam).
3. **Decide about the data and the package** — the store is the user's
   accumulated memory; deleting it is their call, never yours.

**One store, many hosts.** `~/.memu/config.env` and the store it names may be
shared by other memU host adapters on this machine (`memu-claude-code`,
`memu-cursor`, …). Removing *this* host's seams never requires touching the
shared store; Part 3 spells out when touching it is safe at all.

---

## Part 1 — Unregister the bridging (record) task

Find the Codex scheduled task that runs the memU bridging pipeline — it was
created at install time (named e.g. `memu-bridging`) with the three-step
prepare / self-evolve / commit prompt — and delete **that task only**, through
the same scheduled-task surface Codex used to create it. Any other scheduled
tasks the user has are theirs and stay.

### ✅ Verify Part 1

Codex's scheduled-task list no longer shows a memU bridging task.

---

## Part 2 — Remove the retrieval instruction

**Do not hand-edit the block out.** memU owns the text and removes it for you:

```
memu-codex remove-instruction
```

It deletes memU's marked block from `~/.codex/AGENTS.md` and prints the diff.
Everything outside the markers is the user's and survives; the previous
contents are backed up to `~/.codex/AGENTS.md.bak` before the rewrite.
`--dry-run` shows the diff without writing. Re-running is a clean no-op — a
file with no block left is already the desired end state.

### ✅ Verify Part 2

`cat ~/.codex/AGENTS.md` — no `memu:begin`/`memu:end` markers remain, and the
user's own content is intact. The session you are working in already loaded
the old file, so the instruction may still be in your own context; a fresh
session is what picks the removal up.

---

## Part 3 — The data, the config, and the package (ask first)

Everything in this part is **opt-in: ask the user, then act.** The safe
default is to keep data.

- **This host's working state** — Codex predates the per-host layout, so its
  run-scoped state sits directly under `~/.memu/`: the `jobs/`, `memory/`,
  `skill/`, and `resources/` directories and the `.session_manifest*` cursor
  files. Those are safe to delete once Parts 1–2 are done. **Never** sweep
  `~/.memu/` wholesale to get them — `config.env` and the store file live
  there too.
- **The store and `~/.memu/config.env`** — shared by every host adapter on
  the machine. Delete only if the user says so **and** no other host adapter
  is still integrated. Warn first, in plain words: the store *is* their
  accumulated memory, and deleting it is irreversible.
- **The package** — once no host on this machine uses memU any more:
  `pip uninstall memu-cli` (or `pipx uninstall memu-cli` — match how it was
  installed).

### ✅ Done

Report to the user exactly what was removed and what was deliberately kept:
the scheduled task (gone), the instruction (gone), the store (kept where, or
deleted), the package (kept or uninstalled). If the store was kept, say so
explicitly: reinstalling later picks it right back up — memory survives an
uninstall by design.
