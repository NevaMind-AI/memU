"""The bridging pipeline prompt, as data.

The scheduled bridging task is a headless agent run whose prompt is the four-step
prepare -> self-evolve -> commit pipeline. On Unix that prompt is pasted verbatim
into the crontab (see each host's ``BRIDGING_TASK.md``). The Windows ``schedule``
helper can't push a ~1000-character quoted string through Task Scheduler, so it
writes the prompt to a file the wrapper reads — which means the prompt has to
exist as a value here, not only inside the guide.

Parameterized by :class:`~memu.hosts.host_cli.HostSpec` (working tree + binary) so
one text serves every host. It mirrors the canonical prompt in each host's
``BRIDGING_TASK.md`` cron block; if you change one, change both. (A test asserting
the two agree is a good follow-up — today they are kept in sync by hand.)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from memu.hosts.host_cli import HostSpec


def bridging_pipeline_prompt(spec: HostSpec) -> str:
    """The fixed pipeline prompt for ``spec``'s host, machine paths filled in.

    Only two things vary per host: the working tree (``base``) and the binary the
    pipeline's own steps call. Everything else — the ordering, the leftover-first
    rule, the "do nothing is valid" caveat — is host-agnostic and stays verbatim.
    """
    base = spec.default_base_dir
    binary = spec.binary
    return (
        "Run the memU bridging pipeline. Do the four steps strictly in order; do "
        "not skip a step even if the previous one looks like it produced nothing.  "
        f"1. LEFTOVERS. If {base}/jobs/ already contains job files, they are "
        "unfinished work from an earlier run (a crash, or the install itself) — "
        f"process them exactly as step 3 describes, then run:  {binary} commit  — "
        "and only then continue.  "
        f"2. PREPARE. Run this exact command with bash:  {binary} prepare  — it "
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
        "Finish with a one-line summary: how many jobs ran (leftovers included) "
        "and what was committed."
    )
