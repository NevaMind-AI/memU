"""The resource pass: verify the touched-file log, then have the agent describe it.

The skill jobs append every file path a session touched to a raw log. That log is
untrusted — paths may be relative, duplicated, or already deleted — so
:func:`verify_resource_log` filters it down to files that still exist before the
agent is asked to spend a read on each one.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

MAX_RESOURCES = 50

# `{verify_command}` is the host CLI's verify subcommand (a stable PATH command,
# never a script path — a cron-embedded path rots the moment anything moves);
# `{resource_file}` is the file it emits, whose `description:` lines this job fills in.
RESOURCE_JOB_TEMPLATE = """\
You are the **resource-describe** pass for an agent's workspace. Your job is to
annotate a list of files the agent recently touched with short, human-readable
descriptions of what each file is.

## Step 1 — build the resource list

Run this command with `bash`:

    {verify_command}

It reads the raw log of touched files, keeps only the ones that still exist as
real files, dedups them, and writes the result to:

    {resource_file}

Read that file. It is a series of `---`-delimited records, each shaped like:

    ---
    path: <absolute path to a file>
    description:
    ---

The `description:` lines start empty — filling them in is your task.

## Step 2 — describe each file

For every record, read the file at its `path` (with `bash`, e.g. `cat`) and
write a **one to several sentence** description of what the file is and what it
contains onto its `description:` line.

This is **best-effort**. Put the literal value `null` on the `description:` line
instead when the file:

  - cannot be read (permission denied, broken, or gone),
  - is very large (don't try to read huge files), or
  - is an unknown, binary, or uncommon format you can't meaningfully summarize.

A `null` description is a perfectly good outcome — do not guess at content you
could not actually read.

## Step 3 — write the result back

Rewrite `{resource_file}` in place, keeping the exact same `---`-delimited
structure and every `path:` line unchanged, with each `description:` line now
holding either your summary or `null`. Keep each description on a single line.
"""


def verify_resource_log(log: Path, resource_file: Path, max_resources: int = MAX_RESOURCES) -> int:
    """Filter the raw touched-file log into the describe-me resource file.

    Keeps absolute paths that still resolve to a real file, deduped in first-seen
    order, capped at ``max_resources``. Returns how many survived.
    """
    valid: list[str] = []
    seen: set[str] = set()

    if log.is_file():
        for raw in log.read_text(encoding="utf-8").splitlines():
            path = raw.strip()
            # Absolute paths only: a relative path has no meaning here, since the
            # agent logged it from a working directory we no longer know.
            if not path.startswith(("/", "~")) or path in seen:
                continue
            seen.add(path)
            if os.path.isfile(os.path.expanduser(path)):
                valid.append(path)
            if len(valid) >= max_resources:
                break

    records = "".join(f"path: {path}\ndescription: \n---\n" for path in valid)
    resource_file.parent.mkdir(parents=True, exist_ok=True)
    resource_file.write_text(f"---\n{records}", encoding="utf-8")
    return len(valid)


def read_resources(resource_file: Path) -> list[dict[str, Any]]:
    """Parse the finalized resource file into ``{path, description}`` records.

    Records the agent left empty or marked with the literal ``null`` are dropped —
    that is the "couldn't describe it" outcome, not a failure.
    """
    if not resource_file.exists():
        return []

    records: list[dict[str, Any]] = []
    path: str | None = None
    for line in resource_file.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.partition(":")
        if not sep:
            continue
        key = key.strip()
        value = value.strip()
        if key == "path":
            path = value
        elif key == "description":
            if path and value and value.lower() != "null":
                records.append({"path": path, "description": value})
            path = None
    return records


def prepare_resource_job(job_dir: Path, verify_command: str, resource_file: Path, job_index: int) -> None:
    """Write the resource-describe job as ``<job_index>.txt`` under ``job_dir``."""
    instruction = RESOURCE_JOB_TEMPLATE.format(verify_command=verify_command, resource_file=resource_file)
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / f"{job_index}.txt").write_text(instruction, encoding="utf-8")
