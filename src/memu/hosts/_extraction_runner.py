"""Run one query-extraction CLI on Windows, Linux, and macOS using only stdlib.

The caller supplies an ASCII JSON argv line followed by the extractor's raw
stdin. On Linux/macOS, a lifetime pipe monitors the calling hook. This runner
kills the extractor's process group when the hook or extractor exits;
descendants that leave that group are outside this cleanup boundary.

On Windows, the caller assigns this gated runner to a kill-on-close Job Object
before sending the command. The Job owns the runner and its descendants.
"""

from __future__ import annotations

import errno
import json
import os
import select
import signal
import subprocess
import sys
from contextlib import suppress


def _owner_exited(lifetime_fd: int, timeout: float = 0) -> bool:
    readable, _, _ = select.select([lifetime_fd], [], [], timeout)
    return bool(readable) and not os.read(lifetime_fd, 1)


def _read_command(lifetime_fd: int) -> list[str] | None:
    # Read exactly through the newline: buffered reads could steal prompt bytes
    # that the extractor must subsequently inherit on its own stdin.
    input_fd = sys.stdin.fileno()
    header = bytearray()
    while True:
        if lifetime_fd >= 0:
            readable, _, _ = select.select([input_fd, lifetime_fd], [], [])
            if lifetime_fd in readable and not os.read(lifetime_fd, 1):
                return None
            if input_fd not in readable:
                continue
        character = os.read(input_fd, 1)
        if not character:
            msg = "Incomplete extraction command header"
            raise ValueError(msg)
        if character == b"\n":
            break
        header.extend(character)
    command = json.loads(header.decode("ascii"))
    if not isinstance(command, list) or not command or any(not isinstance(part, str) for part in command):
        msg = "Extraction command must be a nonempty JSON array of strings"
        raise ValueError(msg)
    return command


def _group_has_only_zombies(group_id: int) -> bool:
    result = subprocess.run(
        ["/bin/ps", "-axo", "pgid=,stat="],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=1,
        check=False,
    )
    if result.returncode:
        return False
    states = [
        columns[1]
        for line in result.stdout.splitlines()
        if len(columns := line.split()) == 2 and columns[0] == str(group_id).encode("ascii")
    ]
    return all(state.startswith(b"Z") for state in states)


if sys.platform == "darwin":

    def _wait_darwin(process_id: int, lifetime_fd: int) -> None:
        queue = select.kqueue()
        try:
            queue.control([select.kevent(lifetime_fd, filter=select.KQ_FILTER_READ, flags=select.KQ_EV_ADD)], 0, 0)
            try:
                queue.control(
                    [
                        select.kevent(
                            process_id,
                            filter=select.KQ_FILTER_PROC,
                            flags=select.KQ_EV_ADD | select.KQ_EV_ONESHOT,
                            fflags=select.KQ_NOTE_EXIT,
                        )
                    ],
                    0,
                    0,
                )
            except ProcessLookupError:
                return  # The unreaped child exited before registration.
            while True:
                for event in queue.control(None, 2, None):
                    if event.filter == select.KQ_FILTER_PROC or not os.read(lifetime_fd, 1):
                        return
        finally:
            queue.close()


def _wait_posix(process: subprocess.Popen[bytes], lifetime_fd: int) -> int:
    try:
        if sys.platform == "darwin":
            _wait_darwin(process.pid, lifetime_fd)
        else:
            while os.waitid(os.P_PID, process.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is None:
                if _owner_exited(lifetime_fd, 0.025):
                    break
    finally:
        # Neither exit observer reaps the leader. Retain its PID through group
        # cleanup so a late kill cannot target a reused, unrelated PID.
        with suppress(ProcessLookupError):
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except PermissionError:
                # XNU skips zombies when signalling a group and reports EPERM
                # when none remain alive. Real permission failures propagate.
                if sys.platform != "darwin" or not _group_has_only_zombies(process.pid):
                    raise
    return process.wait()


def _run(lifetime_fd: int, flags: int) -> dict[str, int | str | None]:
    if sys.platform == "win32":
        import msvcrt

        msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    else:
        if lifetime_fd < 0:
            msg = "POSIX extraction requires an owner lifetime descriptor"
            raise ValueError(msg)
        primitives = (
            ("kqueue", "kevent", "KQ_NOTE_EXIT")
            if sys.platform == "darwin"
            else ("waitid", "WEXITED", "WNOHANG", "WNOWAIT", "P_PID")
        )
        platform_module = select if sys.platform == "darwin" else os
        if any(not hasattr(platform_module, name) for name in primitives):
            msg = "Extraction lifetime requires a non-reaping POSIX exit observer"
            raise OSError(errno.ENOSYS, msg)
        os.set_inheritable(lifetime_fd, False)
        # A caller may ignore SIGCHLD; the runner must retain its own child
        # until it has cleaned the owned process group.
        signal.signal(signal.SIGCHLD, signal.SIG_DFL)
    command = _read_command(lifetime_fd)
    if command is None or (lifetime_fd >= 0 and _owner_exited(lifetime_fd)):
        return {"errno": None, "error": "Extraction owner exited before launch"}
    source = None
    if os.name == "nt":
        # Windows communicate() writes synchronously: drain the owner's bounded
        # request before a non-reading extractor can block that write forever.
        source = sys.stdin.buffer.read()
    process = subprocess.Popen(  # noqa: S603
        command,
        stdin=subprocess.PIPE if os.name == "nt" else None,
        stderr=subprocess.DEVNULL,
        start_new_session=os.name != "nt",
        creationflags=flags,
    )
    if os.name == "nt":
        process.communicate(source)
        returncode = process.returncode
    else:
        returncode = _wait_posix(process, lifetime_fd)
    return {"returncode": returncode}


def main() -> None:
    try:
        lifetime_fd, flags = map(int, sys.argv[1:])
        status = _run(lifetime_fd, flags)
    except (OSError, ValueError) as exc:
        status = {"errno": getattr(exc, "errno", None), "error": getattr(exc, "strerror", None) or str(exc)}
    # The owner can disappear before receiving the cleanup acknowledgement.
    with suppress(BrokenPipeError):
        os.write(sys.stderr.fileno(), (json.dumps(status) + "\n").encode("ascii"))


if __name__ == "__main__":
    main()
