"""Throwaway harness for the r2-B repair check (not part of the repo)."""
from __future__ import annotations

import glob
import json
import os
import socket
import statistics
import sys
import tempfile
import threading
import time
from pathlib import Path

import psutil

SRC = os.environ["R2B_SRC"]  # head/src or base/src
sys.path.insert(0, SRC)
sys.path.insert(1, str(Path(SRC).parent / "tests"))
import autotester  # noqa: E402

assert os.path.normcase(os.path.normpath(autotester.__file__)).startswith(os.path.normcase(os.path.normpath(SRC))), autotester.__file__

from test_browser import make_project, make_store  # noqa: E402

from autotester.browser import launch as L  # noqa: E402
from autotester.browser import session as S  # noqa: E402
from autotester.browser.session import BrowserSession  # noqa: E402
from autotester.core.paths import ProjectPaths  # noqa: E402

PROBE = {"dur": [], "ok": []}


def install_timers() -> None:
    real_url, real_ans = L.verified_cdp_url, L._answers_as

    def ans(port, path):
        t = time.monotonic()
        r = real_ans(port, path)
        PROBE["ok"].append(r)
        PROBE["ans_dur"] = PROBE.get("ans_dur", []) + [time.monotonic() - t]
        return r

    def url(profile_dir):
        t = time.monotonic()
        try:
            return real_url(profile_dir)
        finally:
            PROBE["dur"].append(time.monotonic() - t)

    L._answers_as = ans
    S.verified_cdp_url = url


def accepts(host, port, timeout=3):
    try:
        socket.create_connection((host, port), timeout=timeout).close()
        return True
    except OSError:
        return False


def mk(tmp: Path, expose=True) -> BrowserSession:
    return BrowserSession(make_project(headed=False), make_store(tmp), tmp / "run",
                          ProjectPaths("pathlynks", tmp), expose_cdp=expose)


def tree_pids():
    me = psutil.Process()
    return {p.pid: p.name() for p in me.children(recursive=True)}


def alive(pids):
    return [p for p in pids if psutil.pid_exists(p)]


def timers():
    return [t.name for t in threading.enumerate() if isinstance(t, threading.Timer)]


def tempdirs():
    return len(glob.glob(os.path.join(tempfile.gettempdir(), "playwright*")))
