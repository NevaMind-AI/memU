"""Windows Job Object ownership for a gated query-extraction runner.

The calling hook assigns the runner before allowing it to launch the CLI.
Explicit cleanup terminates Job members and waits up to two seconds for their
exits. Hook process exit closes its sole Job handle, triggering termination
without executing the explicit cleanup wait.
"""

from __future__ import annotations

import ctypes
import subprocess
import sys
import time
from contextlib import ExitStack
from ctypes import wintypes

_JOB_OBJECT_BASIC_PROCESS_ID_LIST = 3
_JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
_JOB_OBJECT_LIMIT_ACTIVE_PROCESS = 0x8
_JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000


class _BasicLimitInformation(ctypes.Structure):
    _fields_ = (
        ("PerProcessUserTimeLimit", ctypes.c_int64),
        ("PerJobUserTimeLimit", ctypes.c_int64),
        ("LimitFlags", ctypes.c_uint32),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", ctypes.c_uint32),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", ctypes.c_uint32),
        ("SchedulingClass", ctypes.c_uint32),
    )


class _IoCounters(ctypes.Structure):
    _fields_ = (
        ("ReadOperationCount", ctypes.c_uint64),
        ("WriteOperationCount", ctypes.c_uint64),
        ("OtherOperationCount", ctypes.c_uint64),
        ("ReadTransferCount", ctypes.c_uint64),
        ("WriteTransferCount", ctypes.c_uint64),
        ("OtherTransferCount", ctypes.c_uint64),
    )


class _ExtendedLimitInformation(ctypes.Structure):
    _fields_ = (
        ("BasicLimitInformation", _BasicLimitInformation),
        ("IoInfo", _IoCounters),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    )


def _last_error() -> OSError:
    if sys.platform == "win32":
        return ctypes.WinError(ctypes.get_last_error())
    return OSError("Windows extraction jobs are unavailable on this platform")


class WindowsExtractionJob:
    """Own the extraction runner and its descendants in a Windows Job Object."""

    def __init__(self) -> None:
        self._handle: int | None = None
        self._kernel32: ctypes.CDLL
        if sys.platform != "win32":
            raise _last_error()

        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        self._kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        self._kernel32.SetInformationJobObject.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
        ]
        self._kernel32.SetInformationJobObject.restype = wintypes.BOOL
        self._kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        self._kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
        self._kernel32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
        self._kernel32.TerminateJobObject.restype = wintypes.BOOL
        self._kernel32.QueryInformationJobObject.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.c_void_p,
        ]
        self._kernel32.QueryInformationJobObject.restype = wintypes.BOOL
        self._kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        self._kernel32.OpenProcess.restype = wintypes.HANDLE
        self._kernel32.IsProcessInJob.argtypes = [wintypes.HANDLE, wintypes.HANDLE, ctypes.POINTER(wintypes.BOOL)]
        self._kernel32.IsProcessInJob.restype = wintypes.BOOL
        self._kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        self._kernel32.WaitForSingleObject.restype = wintypes.DWORD
        self._kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        self._kernel32.CloseHandle.restype = wintypes.BOOL

        # NULL security attributes keep the sole Job handle out of descendants.
        self._handle = self._kernel32.CreateJobObjectW(None, None)
        if not self._handle:
            raise _last_error()
        limits = _ExtendedLimitInformation()
        limits.BasicLimitInformation.LimitFlags = _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self._kernel32.SetInformationJobObject(
            self._handle,
            _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
            ctypes.byref(limits),
            ctypes.sizeof(limits),
        ):
            error = _last_error()
            self.close()
            raise error

    def assign(self, process: subprocess.Popen[bytes]) -> None:
        """Assign the gated runner before the caller permits it to start a CLI."""
        if self._handle is None:
            msg = "extraction job is closed"
            raise OSError(msg)
        # Popen retains ownership of its handle; never reopen a potentially reused PID.
        process_handle = process._handle  # type: ignore[attr-defined]
        if not self._kernel32.AssignProcessToJobObject(self._handle, process_handle):
            raise _last_error()

    def _process_ids(self) -> list[int]:
        capacity = 16
        while True:
            # JOBOBJECT_BASIC_PROCESS_ID_LIST: two DWORD counts, then ULONG_PTR PIDs.
            buffer = ctypes.create_string_buffer(8 + capacity * ctypes.sizeof(ctypes.c_size_t))
            if self._kernel32.QueryInformationJobObject(
                self._handle, _JOB_OBJECT_BASIC_PROCESS_ID_LIST, buffer, ctypes.sizeof(buffer), None
            ):
                count = wintypes.DWORD.from_buffer(buffer, 4).value
                return list((ctypes.c_size_t * count).from_buffer(buffer, 8))
            error = _last_error()
            if getattr(error, "winerror", None) != 234:  # ERROR_MORE_DATA
                raise error
            capacity = max(capacity * 2, wintypes.DWORD.from_buffer(buffer).value)

    def _open_members(self, resources: ExitStack) -> list[int]:
        handles = []
        for pid in self._process_ids():
            # SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION
            handle = self._kernel32.OpenProcess(0x100000 | 0x1000, False, pid)
            if not handle:
                error = _last_error()
                if getattr(error, "winerror", None) == 87:  # ERROR_INVALID_PARAMETER: process already exited.
                    continue
                raise error
            resources.callback(self._close_handle, handle)
            member = wintypes.BOOL()
            if not self._kernel32.IsProcessInJob(handle, self._handle, ctypes.byref(member)):
                raise _last_error()
            if member.value:  # A snapshot PID may have been reused by an unrelated process.
                handles.append(handle)
        return handles

    def _close_handle(self, handle: int) -> None:
        if not self._kernel32.CloseHandle(handle):
            raise _last_error()

    def close(self) -> None:
        """Terminate Job members and wait up to two seconds for their exits."""
        if self._handle is None:
            return
        try:
            with ExitStack() as resources:
                # Stop new descendants joining while we retain handles to the current members.
                limits = _ExtendedLimitInformation()
                limits.BasicLimitInformation.LimitFlags = (
                    _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE | _JOB_OBJECT_LIMIT_ACTIVE_PROCESS
                )
                if not self._kernel32.SetInformationJobObject(
                    self._handle, _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION, ctypes.byref(limits), ctypes.sizeof(limits)
                ):
                    raise _last_error()
                handles = self._open_members(resources)
                if not self._kernel32.TerminateJobObject(self._handle, 1):
                    raise _last_error()
                deadline = time.monotonic() + 2
                for handle in handles:
                    remaining_ms = max(0, int((deadline - time.monotonic()) * 1000))
                    result = self._kernel32.WaitForSingleObject(handle, remaining_ms)
                    if result == 258:  # WAIT_TIMEOUT
                        raise TimeoutError("extraction Job members did not exit within 2 seconds")  # noqa: TRY003
                    if result != 0:  # WAIT_OBJECT_0
                        raise _last_error()
        finally:
            # Keep kill-on-close as the fallback if termination or observation fails.
            self._close_handle(self._handle)
            self._handle = None
