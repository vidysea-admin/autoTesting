"""A hard per-test watchdog for tests that drive a real browser (crawl-live-hang).

Test-only helper (no `src/` module), same shape as `timing_scale.py`. pytest-timeout is not a
dependency, and a live-browser test that blocks inside Playwright (or a `join()` with no bound)
otherwise holds the whole suite until an outer `timeout` kills it.

`with hard_timeout(seconds, "label"):` arms a timer and snapshots the pytest process's direct
children. If the body is still running when it fires, the watchdog (1) dumps every thread's
traceback to stderr, (2) kills the direct children created after arming (the Playwright driver
and, under it, Chromium), so a call blocked on the browser raises; a child that predates arming
is spared, matched by PID plus creation time so a reused PID is not mistaken for it; the killed
PIDs are logged, and (3) interrupts the main thread, even if (1) or (2) failed, so a call
blocked in Python code (a `time.sleep`, a loop) raises too. A lock wait with no timeout
(`Thread.join()`) is not interruptible on Windows; (2) is what frees the browser-driven bodies
this exists for. The body then fails with `WatchdogTripped`, an AssertionError, instead of
hanging. A body that finishes in time pays one cancelled timer.
"""

from __future__ import annotations

import _thread
import contextlib
import faulthandler
import os
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from typing import Any

_CHILD_LOOKUP_S = 60.0
_JOIN_S = 90.0


class WatchdogTripped(AssertionError):
    """The body outlived its hard bound and was torn down."""


_Child = tuple[int, str]  # (pid, creation stamp): the pair identifies one process, not a reused PID


def _windows_children(pid: int) -> list[_Child]:
    """Direct children via a Toolhelp snapshot, each stamped with its creation time (no
    subprocess, so the lookup cannot itself hang)."""
    import ctypes
    from ctypes import wintypes

    class ProcessEntry(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.c_size_t),
            ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", wintypes.DWORD), ("szExeFile", ctypes.c_wchar * 260),
        ]

    kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel32.OpenProcess.restype = wintypes.HANDLE
    snap = kernel32.CreateToolhelp32Snapshot(0x2, 0)  # TH32CS_SNAPPROCESS
    entry, found = ProcessEntry(), []
    entry.dwSize = ctypes.sizeof(ProcessEntry)
    ok = kernel32.Process32FirstW(snap, ctypes.byref(entry))
    while ok:
        if entry.th32ParentProcessID == pid:
            child = int(entry.th32ProcessID)
            found.append((child, _windows_created(kernel32, child)))
        ok = kernel32.Process32NextW(snap, ctypes.byref(entry))
    kernel32.CloseHandle(snap)
    return found


def _windows_created(kernel32: Any, pid: int) -> str:
    import ctypes
    from ctypes import wintypes

    handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        return "unknown"
    created, other = wintypes.FILETIME(), wintypes.FILETIME()
    got = kernel32.GetProcessTimes(handle, ctypes.byref(created), ctypes.byref(other),
                                   ctypes.byref(other), ctypes.byref(other))
    kernel32.CloseHandle(handle)
    return f"{created.dwHighDateTime}:{created.dwLowDateTime}" if got else "unknown"


def _posix_children(pid: int) -> list[_Child]:
    def run(*argv: str) -> str:
        try:
            return subprocess.run(argv, capture_output=True, text=True, stdin=subprocess.DEVNULL,
                                  timeout=_CHILD_LOOKUP_S).stdout
        except (OSError, subprocess.SubprocessError):
            return ""

    return [(int(tok), run("ps", "-o", "lstart=", "-p", tok).strip() or "unknown")
            for tok in run("pgrep", "-P", str(pid)).split() if tok.isdigit()]


def _children(pid: int) -> list[_Child]:
    return _windows_children(pid) if os.name == "nt" else _posix_children(pid)


def _kill_tree(pid: int) -> None:
    nt = os.name == "nt"
    argv = ["taskkill", "/F", "/T", "/PID", str(pid)] if nt else ["kill", "-9", str(pid)]
    with contextlib.suppress(OSError, subprocess.SubprocessError):
        subprocess.run(argv, capture_output=True, stdin=subprocess.DEVNULL,
                       timeout=_CHILD_LOOKUP_S)


def _wake_main_thread() -> None:
    """Interrupt the main thread. On Windows `interrupt_main` alone does not wake a `time.sleep`
    that is already waiting; the interpreter's SIGINT event does."""
    _thread.interrupt_main()
    if os.name == "nt":
        import ctypes

        ctypes.pythonapi._PyOS_SigintEvent.restype = ctypes.c_void_p  # type: ignore[attr-defined]
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        kernel32.SetEvent.argtypes = [ctypes.c_void_p]
        kernel32.SetEvent(ctypes.pythonapi._PyOS_SigintEvent())  # type: ignore[attr-defined]


def _trip(label: str, seconds: float, state: dict[str, bool], before: set[_Child]) -> None:
    """Dump, kill only children born after arming, and always wake the main thread."""
    state["tripped"] = True
    try:
        print(f"\nWATCHDOG: {label} still running after {seconds:g}s; dumping threads, killing "
              "the browser driver tree, interrupting the test", file=sys.stderr, flush=True)
        faulthandler.dump_traceback(file=sys.stderr, all_threads=True)
        victims = [c for c in _children(os.getpid()) if c not in before]
        for pid, _stamp in victims:
            _kill_tree(pid)
        print(f"WATCHDOG: killed pids {[pid for pid, _ in victims]}; spared "
              f"{sorted(pid for pid, _ in before)} (started before arming)",
              file=sys.stderr, flush=True)
    except Exception as exc:  # the wake below must still run
        print(f"WATCHDOG: teardown step failed: {type(exc).__name__}: {exc}",
              file=sys.stderr, flush=True)
    finally:
        if not state["done"]:
            _wake_main_thread()


@contextlib.contextmanager
def hard_timeout(seconds: float, label: str) -> Iterator[None]:
    state = {"tripped": False, "done": False}
    try:
        before = set(_children(os.getpid()))  # these survive a trip: they are not ours to kill
    except Exception:
        before = set()
    timer = threading.Timer(seconds, _trip, args=(label, seconds, state, before))
    timer.daemon = True
    timer.start()
    try:
        yield
    except BaseException as exc:
        if state["tripped"]:
            raise WatchdogTripped(f"{label} exceeded its {seconds:g}s hard bound") from exc
        raise
    finally:
        state["done"] = True
        timer.cancel()
        if state["tripped"]:  # let the trip thread finish, and absorb a late interrupt
            with contextlib.suppress(KeyboardInterrupt):
                timer.join(_JOIN_S)
                time.sleep(0.05)
    if state["tripped"]:
        raise WatchdogTripped(f"{label} exceeded its {seconds:g}s hard bound")
