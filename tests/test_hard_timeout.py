"""The hard watchdog (crawl-live-hang): a blocked body fails fast instead of holding the suite."""

from __future__ import annotations

import subprocess
import sys
import time

import hard_timeout as hard_timeout_module
import pytest
from hard_timeout import WatchdogTripped, hard_timeout

BOUND_S = 2.0
SLACK_S = 120.0  # child lookup runs PowerShell on Windows, slow on a busy host


def test_a_body_that_finishes_in_time_is_untouched() -> None:
    with hard_timeout(30.0, "quick body"):
        value = 1 + 1
    assert value == 2


def test_an_error_inside_the_bound_propagates_unchanged() -> None:
    with pytest.raises(ValueError, match="plain"), hard_timeout(30.0, "raising body"):
        raise ValueError("plain")


def test_a_sleeping_body_is_interrupted_and_fails_within_the_bound() -> None:
    started = time.monotonic()
    bound = hard_timeout(BOUND_S, "sleeping body")
    with pytest.raises(WatchdogTripped, match="sleeping body"), bound:
        time.sleep(10**6)
    assert time.monotonic() - started < BOUND_S + SLACK_S


def _spawn_sleeper() -> subprocess.Popen:
    return subprocess.Popen([sys.executable, "-c", "import time; time.sleep(10**6)"])


def test_a_body_blocked_on_a_child_started_after_arming_is_freed_by_killing_it() -> None:
    children: list[subprocess.Popen] = []
    try:
        with pytest.raises(WatchdogTripped), hard_timeout(BOUND_S, "child wait"):
            children.append(_spawn_sleeper())
            children[0].wait()
        assert children[0].poll() is not None, "the watchdog must kill the child it is blocked on"
    finally:
        for child in children:
            child.kill()
            child.wait(timeout=30)


def test_a_child_started_before_arming_survives_the_trip() -> None:
    bystander = _spawn_sleeper()
    try:
        with pytest.raises(WatchdogTripped), hard_timeout(BOUND_S, "sleeping body"):
            time.sleep(10**6)
        assert bystander.poll() is None, "a child that predates the watchdog is not ours to kill"
    finally:
        bystander.kill()
        bystander.wait(timeout=30)


def test_the_main_thread_still_wakes_when_the_kill_step_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(_pid: int) -> None:
        raise OSError("taskkill unavailable")

    monkeypatch.setattr(hard_timeout_module, "_kill_tree", boom)
    started = time.monotonic()
    child_holder: list[subprocess.Popen] = []
    try:
        with pytest.raises(WatchdogTripped), hard_timeout(BOUND_S, "kill raises"):
            child_holder.append(_spawn_sleeper())  # a victim exists, so _kill_tree is reached
            time.sleep(10**6)
        assert time.monotonic() - started < BOUND_S + SLACK_S
    finally:
        for child in child_holder:
            child.kill()
            child.wait(timeout=30)
