"""Bounded, traced browser teardown: the one place a session's context and driver are closed.

One job: close a `BrowserSession`'s Playwright context and driver without letting an idle,
lingering Chromium hold the run (stall diagnosis 2026-10-28: `context.close()` blocked 90-900 s on
a memory-starved host, un-traced, with that time charged to the run's wall clock).

Playwright's sync API is thread-bound (a call from another thread raises "Cannot switch to a
different thread"), so a step cannot be moved to a worker and abandoned. It runs in the CALLING
thread while a timer thread watches it; past `TEARDOWN_TIMEOUT_S` the timer cancels the in-flight
request on Playwright's own event loop (a client-side cancel -- measured to leave the connection
usable). The step raises `CancelledError` in the caller, which treats it as an abandoned step:
a failed `PhaseSpan` is recorded and teardown continues. No process is killed (B9): a Chromium
that outlives the cancel is released when the driver is stopped.
"""

from __future__ import annotations

import asyncio
import contextlib
import threading
import time
from collections.abc import Callable
from typing import Any

from autotester.core.trace import TraceWriter, traced_phase

TEARDOWN_TIMEOUT_S = 20.0
"""Seconds one teardown step (`context.close()`, `playwright.stop()`) may take."""

_DISPATCHER = "Connection.run_as_sync"  # Playwright's own loop task; others are requests


def cancel_inflight(owner: Any) -> None:
    """Cancel the request `owner` (a Playwright sync object) is blocked on; thread-safe."""
    loop = getattr(owner, "_loop", None)
    if not isinstance(loop, asyncio.AbstractEventLoop) or loop.is_closed():
        return

    def _cancel() -> None:
        for task in asyncio.all_tasks(loop):
            if getattr(task.get_coro(), "__qualname__", "") != _DISPATCHER:
                task.cancel()

    with contextlib.suppress(RuntimeError):
        loop.call_soon_threadsafe(_cancel)


def bounded_call(step: Callable[[], object], *, timeout_s: float,
                 abort: Callable[[], None]) -> bool:
    """Run `step()` here; if it is still running after `timeout_s`, call `abort()` from a timer
    thread. True when it finished in time; False when it was abandoned (its cancellation, or any
    later outcome, is swallowed). An ordinary exception inside the window propagates."""
    fired, done = threading.Event(), threading.Event()

    def _fire() -> None:
        if done.is_set():  # the step finished as the timer fired: never cancel its successor
            return
        fired.set()
        with contextlib.suppress(Exception):
            abort()

    timer = threading.Timer(timeout_s, _fire)
    timer.daemon = True
    timer.start()
    try:
        step()
    except BaseException:
        if not fired.is_set():
            raise
    finally:
        done.set()
        timer.cancel()
    return not fired.is_set()


def _teardown_step(owner: Any, method: str, phase: str, trace: TraceWriter | None,
                   case_id: str | None, timeout_s: float) -> None:
    step = getattr(owner, method, None)
    if not callable(step):
        return
    started = time.monotonic()
    ok, note = False, None
    try:
        ok = bounded_call(step, timeout_s=timeout_s, abort=lambda: cancel_inflight(owner))
        note = None if ok else f"abandoned after {timeout_s:.0f}s"
    except Exception as exc:  # one failed step skips none (B9): still recorded, never raised
        note = f"{type(exc).__name__}"
    if trace is not None:
        trace.record_phase(phase=phase, started_mono=started, case_id=case_id, ok=ok, note=note)


def close_session(context: Any, driver: Any, *, trace: TraceWriter | None = None,
                  budget: Any = None, case_id: str | None = None,
                  sweep: Callable[[], None] | None = None,
                  timeout_s: float = TEARDOWN_TIMEOUT_S) -> None:
    """Close the context then the driver (each bounded and traced as `session_close.context` /
    `.driver`), then run `sweep` (`session_close.sweep`). Housekeeping time: never charged to the
    approval clock beyond the budget's allowance."""
    housekeeping = getattr(budget, "housekeeping", None)
    with housekeeping() if callable(housekeeping) else contextlib.nullcontext():
        _teardown_step(context, "close", "session_close.context", trace, case_id, timeout_s)
        _teardown_step(driver, "stop", "session_close.driver", trace, case_id, timeout_s)
        if sweep is not None:
            with contextlib.suppress(Exception), traced_phase(trace, case_id,
                                                              "session_close.sweep"):
                sweep()
