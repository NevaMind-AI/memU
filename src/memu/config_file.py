"""Writing ``~/.memu/config.env`` — the one file every host shares (ADR 0017).

:mod:`memu.env` reads this file; this module is the only thing that writes it.
The asymmetry is deliberate and the reason is the file itself: it is shared by
every host on the machine, it carries a plaintext credential, and it holds an
invariant no single host can see — record and inject must agree on the backend,
or retrieval silently returns nothing (ADR 0009). A file with those properties
should not be produced by an agent following prose, and should not have two
producers inside memU either.

Three rules, and every caller gets all three for free:

* **Merge, never replace the document.** Only the named keys change. Every
  other logical line — another host's settings, the user's comments, a key this
  release has never heard of — keeps its text, order, and comments. Writes use
  canonical UTF-8; a legacy encoding is normalized on its first write, line
  endings follow the host text convention, and a missing final newline is added.
* **Atomic.** The new text lands in a temp file beside the target and replaces
  it with :func:`os.replace`, so a crash or a full disk leaves the old file
  intact rather than a half-written one that no longer parses.
* **Restricted.** ``0700`` on the directory it creates, ``0600`` on the file.

The read side here is *not* :func:`memu.env.env`, and that difference is
load-bearing rather than incidental. ``env()`` resolves the process environment
first, which is right for answering "what is this run configured with" and wrong
for answering "what does the file say" — the only question a writer and its
guards may ask. An exported ``MEMU_CLOUD_API_KEY`` must not make a *file* that
declares nothing look like a configured cloud install.
"""

from __future__ import annotations

import contextlib
import os
import tempfile
from collections.abc import Mapping
from pathlib import Path

from memu.env import CONFIG_ENV, read_config


def config_path() -> Path:
    """The config file this process reads and writes.

    ``MEMU_CONFIG_ENV`` is read from :data:`os.environ` alone, never through
    :func:`memu.env.env`: it names the file, so resolving it *from* that file
    would be circular.
    """
    return Path(os.path.expanduser(os.environ.get("MEMU_CONFIG_ENV", CONFIG_ENV)))


def read() -> dict[str, str]:
    """Parse the file. Uncached, and blind to the process environment.

    Deliberately not :func:`memu.env.env`. See the module docstring: this answers
    what is *on disk*, which is the only input a guard about existing memory may
    take. Parsing matches :func:`memu.env._file_values` — last assignment wins,
    surrounding quotes stripped — so what a guard sees and what a later run
    resolves cannot disagree.
    """
    try:
        text, _ = read_config(config_path())
    except OSError:
        return {}
    values: dict[str, str] = {}
    for raw in text.splitlines():
        key, value = _split(raw)
        if key:
            values[key] = value.strip().strip("\"'")
    return values


def write_values(updates: Mapping[str, str]) -> tuple[Path, bool]:
    """Merge ``updates`` into the file. Returns its path and whether it changed.

    Raises :class:`OSError` rather than swallowing one — every caller here has a
    user in front of it and a better answer than silence. :func:`memu.events.client_instance_id`
    is the exception and catches it itself, because telemetry may never fail a
    command.

    Called with nothing to set, this still enforces the permissions on an existing
    file, which is the cheap half of what it exists for.
    """
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        text, canonical = read_config(path)
    except FileNotFoundError:
        text, canonical = "", True
    merged = _merged(text, dict(updates))
    if merged == text and canonical and path.is_file():
        _restrict(path)
        return path, False

    # Same directory, so the replace is a rename within one filesystem — the
    # property the atomicity claim rests on. mkstemp already creates at 0600;
    # _restrict is belt-and-braces for the umask-independent guarantee.
    handle_fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=".config.env.")
    tmp = Path(tmp_name)
    try:
        with os.fdopen(handle_fd, "w", encoding="utf-8") as handle:
            handle.write(merged)
        _restrict(tmp)
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            tmp.unlink()
        raise
    return path, True


def permission_note() -> str:
    """What a command may truthfully claim it did to the file's permissions.

    ``chmod 600`` restricts nothing on Windows — :func:`os.chmod` there moves the
    read-only bit and touches no ACL — so a command that printed it anyway would
    replace a real instruction (today's guides tell the agent to restrict the file
    to the current user) with an assertion of protection that does not exist.
    Doing the real thing means shelling out to ``icacls``: a subprocess and a new
    failure mode on the install path, not worth it for a claim. So Windows says
    what is actually true instead.
    """
    return "chmod 600" if os.name == "posix" else "plaintext key; Windows ACLs inherited"


def _split(raw: str) -> tuple[str, str]:
    """``KEY``, ``value`` for an assignment line; ``""``, ``""`` for anything else."""
    line = raw.strip()
    if not line or line.startswith("#"):
        return "", ""
    key, sep, value = line.partition("=")
    if not sep:
        return "", ""
    return key.strip(), value


def _merged(text: str, updates: dict[str, str]) -> str:
    """``text`` with ``updates`` applied in place, everything else untouched.

    A key already present is rewritten *where it is*, so it keeps its position
    next to whatever comment explains it. A key present more than once — two
    first runs racing to append ``MEMU_CLIENT_ID`` is the real case — has every
    occurrence rewritten rather than one: the parser takes the last assignment,
    so leaving an earlier one behind would preserve a value that no longer
    resolves and confuse the next human to open the file.
    """
    lines = text.splitlines()
    written: set[str] = set()
    out: list[str] = []
    for raw in lines:
        key, _ = _split(raw)
        if key and key in updates:
            out.append(f"{key}={updates[key]}")
            written.add(key)
        else:
            out.append(raw)
    out.extend(f"{key}={value}" for key, value in updates.items() if key not in written)
    return "".join(f"{line}\n" for line in out)


def _restrict(path: Path) -> None:
    """Owner-only, where that means something. See :func:`permission_note`."""
    if os.name != "posix":
        return
    with contextlib.suppress(OSError):
        path.chmod(0o600)
