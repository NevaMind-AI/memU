"""Turn each prepared transcript into a self-evolve job-instruction file.

The middle step of the pipeline is not a script — it is real agent work (reading
transcripts, making judgement calls, writing markdown). These templates are how
prepare hands that work over: each emitted job is self-contained and already
carries the concrete paths it needs, so the agent does no path reasoning.
"""

from __future__ import annotations

from pathlib import Path

# Both templates share the same shape — read input, read what exists, decide,
# write — differing only in what they mine for. `{input_path}` is the transcript
# to learn from; `{track_dir}` is where existing files of that kind live and
# where new/patched ones are written.
MEMORY_JOB_TEMPLATE = """\
You are the **self-evolve** pass for an agent's workspace. Your job is to mine
what the agent recently *did* in one session into durable, reusable **user
memory** — small markdown files that record stable facts about the user, their
projects, and how they like to work.

## The session to learn from

The transcript (the user/assistant messages of the session) is at:

    {input_path}

Read it with `bash` (e.g. `cat`).

## Step 1 — read what already exists

Existing user-memory files live under:

    {track_dir}

Read the **file names first**. Only read a memory's full body if its name looks
related to what the session covers — skip the rest.

## Step 2 — decide what (if anything) to do

For the session as a whole, pick ONE of:

  a. **Do nothing.** The session records nothing durable worth keeping (it just
     followed known preferences, or is too task-specific to reuse). Emit no files
     and finish. A no-op is a perfectly good outcome — do not invent a memory to
     justify the run.

  b. **Patch existing memory file(s).** The session refines or extends something
     an existing memory already covers. Rewrite that file in place with the
     merged content.

  c. **Create a new memory file.** The session surfaced a genuinely new, durable
     fact no existing memory covers. Write a new file.

You may combine (b) and (c) if the session warrants it.

## Step 3 — write the memory files

Write each memory file you create or patch to a path under `{track_dir}` with a
meaningful kebab-case name (last write wins when patching). Every file you write
must start with this front-matter head, followed by the memory body:

    ---
    name: <short kebab-case name>
    description: <one-line summary of the memory>
    ---
    <the memory content>
"""

SKILL_JOB_TEMPLATE = """\
You are the **self-evolve** pass for an agent's workspace. Your job is to mine
what the agent recently *did* in one session — including the tools it ran — into
durable, reusable **skills**: markdown files that capture a repeatable workflow
for a task family so the agent can do it better next time.

## The session to learn from

The full transcript (user/assistant messages plus the tool calls the agent made)
is at:

    {input_path}

Read it with `bash` (e.g. `cat`).

## Step 1 — read what already exists

Existing skill files live under:

    {track_dir}

Read the **file names first**. Only read a skill's full body if its name looks
related to what the session covers — skip the rest.

## Step 2 — decide what (if anything) to do

For the session as a whole, pick ONE of:

  a. **Do nothing.** The session just followed an existing skill's instructions
     and fulfilled the request — nothing new worth recording. Emit no files and
     finish. A no-op is a perfectly good outcome — do not invent a skill to
     justify the run.

  b. **Patch existing skill(s).** The session introduces a new
     solution/branch/edge-case within a task type an existing skill already
     covers. Grow that skill in place (e.g. add a "case X, do ..." branch). A
     skill is an organic collection for related tasks, not one rigid workflow —
     branching it is preferred over spawning near-duplicate skills.

  c. **Create a new skill.** The session developed a workflow for a genuinely new
     task type no existing skill covers. Write a new file.

You may combine (b) and (c) if the session warrants it.

## Step 3 — write the skills

Write each skill file you create or patch to a path under `{track_dir}` with a
meaningful kebab-case name that describes the task family — not a placeholder
(last write wins when patching). Every file you write must start with this
front-matter head, followed by the skill body:

    ---
    name: <short kebab-case name>
    description: <one-line summary of what the skill is for>
    ---
    <the skill instructions>

## Step 4 — log the files the session touched

This step is separate from the skill work above and always runs, regardless of
which choice you made in Step 2.

Scan the transcript for files the assistant itself **created or updated** during
the session (look at the tool calls it made — writes, edits, patches, etc.).
For each such file, append its full path as one line to this log:

    {resource_log}

Append only — never overwrite or reorder it. One path per line. The simplest
way is a shell append, e.g.:

    echo "<full path>" >> {resource_log}

If the session created or updated no files, leave the log untouched.
"""


def prepare_instruction_jobs(
    job_dir: Path,
    session_dir: Path,
    memory_dir: Path,
    skill_dir: Path,
    resource_log: Path,
    num_sessions: int,
) -> None:
    """Write per-session job-instruction files under ``job_dir``.

    For each of the ``num_sessions`` transcripts, fill the templates with
    concrete paths: a user-memory job (mining ``<idx>.jsonl``) and a skill job
    (mining ``<idx>_full.jsonl``). Memory jobs are numbered first (1..N), skill
    jobs after them (N+1..2N) — ordering is load-bearing, since the skill jobs
    are what populate ``resource_log`` for the resource job that comes last.
    """
    job_dir.mkdir(parents=True, exist_ok=True)
    for stale in job_dir.glob("*.txt"):
        stale.unlink()

    for idx in range(1, num_sessions + 1):
        instruction = MEMORY_JOB_TEMPLATE.format(
            input_path=session_dir / f"{idx}.jsonl",
            track_dir=memory_dir,
        )
        (job_dir / f"{idx}.txt").write_text(instruction, encoding="utf-8")

    for idx in range(1, num_sessions + 1):
        instruction = SKILL_JOB_TEMPLATE.format(
            input_path=session_dir / f"{idx}_full.jsonl",
            track_dir=skill_dir,
            resource_log=resource_log,
        )
        (job_dir / f"{num_sessions + idx}.txt").write_text(instruction, encoding="utf-8")
