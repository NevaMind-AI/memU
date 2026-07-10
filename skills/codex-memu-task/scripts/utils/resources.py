"""Step 4 — turn the verified resource list into a describe-the-files job."""

from pathlib import Path

# Job template for describing verified resource files. `{script_path}` is the
# absolute path to verify_resources.py; `{resource_file}` is the file it emits,
# whose `description:` lines this job fills in.
RESOURCE_JOB_TEMPLATE = """\
You are the **resource-describe** pass for an agent's workspace. Your job is to
annotate a list of files the agent recently touched with short, human-readable
descriptions of what each file is.

## Step 1 — build the resource list

Run this script with `bash`:

    python3 {script_path}

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


def read_resources(resource_file: Path) -> list[dict]:
    """Parse the finalized resource file into {path, description} records.

    Records are `---`-delimited with `path:` and `description:` lines (see
    RESOURCE_JOB_TEMPLATE). Records the agent left empty or marked with the
    literal `null` are dropped — they are the "couldn't describe" outcome.
    """
    if not resource_file.exists():
        return []

    records: list[dict] = []
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


def prepare_resource_job(
    job_dir: Path,
    script_path: Path,
    resource_file: Path,
    job_index: int,
) -> None:
    """Write the resource-describe job as `<job_index>.txt` under job_dir.

    Fills RESOURCE_JOB_TEMPLATE with the absolute path to verify_resources.py
    (`script_path`) and the resources file it produces (`resource_file`), so the
    emitted job needs no further path reasoning.
    """
    instruction = RESOURCE_JOB_TEMPLATE.format(
        script_path=script_path,
        resource_file=resource_file,
    )
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / f"{job_index}.txt").write_text(instruction, encoding="utf-8")
