"""The bridging prompts, as data.

The scheduled bridging task is a headless agent run whose prompt is the four-step
prepare -> self-evolve -> commit pipeline. Neither scheduler can carry the
~1200-character quoted prompt on its command line — cron truncates crontab lines
around 1 KB, and Task Scheduler's ``/TR`` splits on the first space — so on both
platforms the prompt lives in a file the scheduled wrapper reads (Unix:
``bridge-prompt.txt`` + ``bridge.sh``, see each host's ``BRIDGING_TASK.md``;
Windows: the ``schedule`` helper writes a job-only prompt and owns prepare/commit
itself) — which means both prompts have to exist as values here, not only inside
the guide.

Parameterized by :class:`~memu.hosts.host_cli.HostSpec` (working tree + binary) so
one text serves every host. It mirrors the canonical prompt in each host's
``BRIDGING_TASK.md`` prompt-file block; if you change one, change both — a test
in ``test_scheduling_windows.py`` asserts the two agree.
"""

from __future__ import annotations

import shlex
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from memu.hosts.host_cli import HostSpec


def bridging_pipeline_prompt(spec: HostSpec, *, prepare_session_dir: str | Path | None = None) -> str:
    """The fixed pipeline prompt for ``spec``'s host, machine paths filled in.

    The working tree and binary vary per host. A scheduler may also bake in a
    resolved session-store path when the host's default moves with its runtime
    home; quoting it here keeps the prompt's PREPARE command one shell-safe unit.
    Everything else stays verbatim across hosts.
    """
    base = spec.default_base_dir
    binary = spec.binary
    prepare = f"{binary} prepare"
    if prepare_session_dir is not None:
        prepare += f" --session-dir {shlex.quote(str(prepare_session_dir))}"
    return (
        "Run the memU bridging pipeline. Do the four steps strictly in order; do "
        "not skip a step even if the previous one looks like it produced nothing.  "
        f"1. LEFTOVERS. If {base}/jobs/ already contains job files, they are "
        "unfinished work from an earlier run (a crash, or the install itself) — "
        f"process them exactly as step 3 describes, then run:  {binary} commit  — "
        "and only then continue.  "
        f"2. PREPARE. Run this exact command with bash:  {prepare}  — it "
        f"regenerates {base}/jobs/. If the command exits non-zero, stop and report "
        "the error.  "
        f"3. SELF-EVOLVE. List {base}/jobs/*.txt and process them in ascending "
        "numeric order (1.txt, then 2.txt, …). The count changes every run — "
        "always glob and sort. If there are no job files, skip to step 4. For each "
        "job file: read it and follow its instructions to the letter. Each job is "
        "self-contained and already carries the concrete paths it needs. Emitting "
        "no files for a job is a valid outcome; do not invent content.  "
        f"4. COMMIT. Run this exact command with bash:  {binary} commit  — it "
        "commits whatever the jobs created or changed. If it exits non-zero, "
        "report the error.  "
        "ON FAILURE. If step 2 or step 4 exited non-zero, run this once before "
        f'you stop:  {binary} report error --stage remember --detail "<a full '
        'account of what went wrong>"  — that detail is all a memU engineer gets '
        "to work out what is broken on this machine, so be generous: which step, "
        "what you ran, what happened instead, what you already tried, and what "
        "you think the cause is. Write it as prose for a human, not as a "
        "transcript — do not paste the traceback or raw command output, which the "
        "CLI already reports on its own, and keep credentials, absolute paths, "
        "and memory or transcript text out of it. Ignore any failure of that "
        "command; it is never part of the run.  "
        "Finish with a one-line summary: how many jobs ran (leftovers included) "
        "and what was committed."
    )


def bridging_jobs_prompt(spec: HostSpec, *, job_dir: str | Path, base_dir: str | Path) -> str:
    """Windows agent prompt for only the judgement-heavy job-processing stage.

    The PowerShell wrapper owns ``prepare`` and ``commit`` so their real process
    exit codes reach Task Scheduler.  A fresh completion nonce in the environment
    makes an agent exit code insufficient on its own: the final command records
    proof that the agent reached the end of every numbered job.
    """
    return (
        "Process the existing memU self-evolve job files. "
        f"List {job_dir}/*.txt and process every file in ascending numeric order "
        "(1.txt, then 2.txt, and so on); always discover the current set instead "
        "of assuming a count. Read each file and follow its instructions to the "
        "letter. Each job is self-contained and already contains the concrete "
        "paths it needs. Emitting no files for a job is a valid outcome; do not "
        "invent content. Use the current platform's native shell and commands. "
        "On Windows use PowerShell; do not invoke bash or WSL merely to translate "
        "a shell example. Do not run prepare or commit; the scheduler owns those "
        "stages. If any job fails, stop, explain the failure, and do not mark the "
        "batch complete. Only after every numbered job succeeds, run this exact "
        f'PowerShell command:  {spec.binary} complete-jobs --base-dir "{base_dir}"  '
        "The completion command must be last. Finish with a one-line summary of "
        "how many jobs ran."
    )
