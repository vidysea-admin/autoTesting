"""PARALLEL_RUN: fan N cases out across isolated browser contexts (T-173/D-041).

Today `stages/execute.py::run_case` drives one case at a time on one shared
`BrowserSession`. This module adds the fan-out: up to N cases run at once,
each in its OWN session (its own Playwright `BrowserContext`/storage state,
PR2), where N = min(`project.max_parallel`, a measured RAM/CPU budget, PR1) --
except a project whose `write_policy` is `ALLOW_WRITES` (a shared test
account writes can collide on), which always runs its cases serially (PR3).
A shared `RunBudget` (PR7) keeps `RunApproval` bounds applied to the whole
run, never multiplied per worker, and one case crashing is caught and
reported as that case's own `ERRORED` outcome without aborting its siblings
(PR6). New module, not an addition to `execute.py`: this is fan-out
orchestration, a different concern from running one case's own steps, and
`execute.py` already carries the step-dispatch table at close to its own
line budget (core-invariants C2/C3, parallel-run.md "How a unit is
verified").

Contract: qa/contracts/parallel-run.md PR1-PR7.
"""

from __future__ import annotations

import ctypes
import os
import platform
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from autotester.schema.approval import RunApproval
from autotester.schema.case import Case
from autotester.schema.enums import Outcome, WritePolicy
from autotester.schema.project import Project
from autotester.schema.run import RawResult

DEFAULT_PER_CONTEXT_MB = 512.0
"""Conservative estimate of one Chromium `BrowserContext`'s resident memory --
the divisor in the RAM budget below. Deliberately not tuned to this host: a
precise per-context figure is explicitly out of scope (parallel-run.md
"Explicit no-fire list") -- what must be real is that a *measured* number
participates in the `min()`, not this constant's exact value."""

_RAM_FLOOR_MB = 2048.0
"""Never spend the last ~2GB of free RAM on browser contexts -- reserved for
the OS and everything else already running on the host."""


@dataclass(frozen=True)
class ParallelPlan:
    """PR1's recorded binding: the chosen N and which term decided it."""

    config_ceiling: int
    measured_budget: int
    n: int
    bound_by: str  # "config" | "budget" | "write_policy"
    free_ram_mb: float
    cpu_count: int


def _free_ram_mb() -> float:
    """Real, measured free RAM in MB -- Windows via `GlobalMemoryStatusEx`,
    POSIX via `/proc/meminfo`'s `MemAvailable` (falling back to sysconf).
    Callers that want a deterministic value for a test inject one instead of
    calling this (`plan_parallel_run(..., free_ram_mb=...)`) -- this function
    is never exercised by a test that asserts a specific number, only by the
    live host path."""
    if platform.system() == "Windows":
        return _free_ram_mb_windows()
    return _free_ram_mb_posix()


def _free_ram_mb_windows() -> float:
    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    stat = MEMORYSTATUSEX()
    stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))  # type: ignore[attr-defined]
    return stat.ullAvailPhys / (1024 * 1024)


def _free_ram_mb_posix() -> float:
    try:
        with open("/proc/meminfo") as fh:
            for line in fh:
                if line.startswith("MemAvailable:"):
                    return float(line.split()[1]) / 1024
    except OSError:
        pass
    try:
        pages = os.sysconf("SC_AVPHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        return (pages * page_size) / (1024 * 1024)
    except (ValueError, OSError, AttributeError):
        return 0.0


def plan_parallel_run(
    project: Project, *, cpu_count: int | None = None,
    free_ram_mb: float | None = None, per_context_mb: float = DEFAULT_PER_CONTEXT_MB,
) -> ParallelPlan:
    """PR1 + PR3: decide N and record which term bound it.

    `cpu_count`/`free_ram_mb` are injected by tests so the decision is
    reproducible on constructed numbers, never on this host's live state
    (parallel-run.md: "never falsify by running against the live tree" --
    the same principle applied to a measurement, not just an edit)."""
    cpu = cpu_count if cpu_count is not None else (os.cpu_count() or 1)
    measured_free = free_ram_mb if free_ram_mb is not None else _free_ram_mb()
    ram_slots = max(0, int((measured_free - _RAM_FLOOR_MB) // per_context_mb))
    measured_budget = max(1, min(ram_slots, cpu)) if ram_slots > 0 else 1
    config_ceiling = max(1, project.max_parallel)

    if project.write_policy is WritePolicy.ALLOW_WRITES:
        return ParallelPlan(config_ceiling, measured_budget, 1, "write_policy",
                             measured_free, cpu)

    n = min(config_ceiling, measured_budget)
    bound_by = "budget" if measured_budget < config_ceiling else "config"
    return ParallelPlan(config_ceiling, measured_budget, n, bound_by, measured_free, cpu)


class RunBudget:
    """PR7: one shared, thread-safe consent budget for the whole run -- never
    one per worker, so N-way concurrency can never spend up to N times what
    `RunApproval` granted. `None` means no approval was supplied (unlimited);
    the aggregate is checked-and-reserved atomically so two workers racing to
    spend the last few actions can never both succeed."""

    def __init__(self, approval: RunApproval | None) -> None:
        self._approval = approval
        self._lock = threading.Lock()
        self._actions_used = 0
        self._probes_used = 0
        self._start = time.monotonic()

    def try_consume(self, *, actions: int = 0, probes: int = 0) -> bool:
        approval = self._approval
        if approval is None:
            return True
        with self._lock:
            if approval.wall_clock_s and (time.monotonic() - self._start) > approval.wall_clock_s:
                return False
            actions_after = self._actions_used + actions
            probes_after = self._probes_used + probes
            if approval.max_actions and actions_after > approval.max_actions:
                return False
            if approval.max_probes and probes_after > approval.max_probes:
                return False
            self._actions_used = actions_after
            self._probes_used = probes_after
            return True

    @property
    def actions_used(self) -> int:
        return self._actions_used


def action_cost(case: Case) -> int:
    """One case's cost against the aggregate action budget -- one unit per
    declared step, the system's own vocabulary for "an action" (`Action` in
    `schema/enums.py`); a step-less case still costs at least 1."""
    return max(1, len(case.steps))


SessionFactory = Callable[[Case], object]
RunFn = Callable[[Case, object], RawResult]


def _run_one(
    case: Case, session_factory: SessionFactory, run_fn: RunFn, budget: RunBudget | None,
) -> RawResult:
    """One case, isolated: its own session (PR2), its own try/except so a
    crash is reported as ITS outcome and never propagates to a sibling (PR6).

    AT-565: `session_factory(case)` itself can raise -- a real
    `BrowserSession.start()` failing under N-way concurrency, not just
    `run_fn`'s body -- so it must be INSIDE the guarded region too. Before
    this fix it sat above the `try`, and an unguarded raise there propagated
    out of `run_cases`' `[f.result() for f in futures]`, discarding every
    sibling's already-finished result instead of reporting just this case
    as ERRORED."""
    if budget is not None and not budget.try_consume(actions=action_cost(case)):
        return RawResult(case_id=case.id, outcome=Outcome.ERRORED,
                          error="run budget exhausted before this case could start")
    session: object | None = None
    try:
        session = session_factory(case)
        return run_fn(case, session)
    except Exception as exc:  # PR6: reported per case, never aborts the run
        return RawResult(case_id=case.id, outcome=Outcome.ERRORED,
                          error=f"{type(exc).__name__}: {exc}")
    finally:
        if session is not None:
            close = getattr(session, "close", None)
            if callable(close):
                close()


def run_cases(
    cases: list[Case], plan: ParallelPlan, session_factory: SessionFactory, run_fn: RunFn,
    *, approval: RunApproval | None = None,
) -> list[RawResult]:
    """Run `cases` at concurrency `plan.n` (PR1/PR3: `n=1` is exactly the
    serial baseline PR4/PR5 compare against -- one function, two widths, not
    two code paths, C3). Results come back in `cases` order regardless of
    completion order, so a caller can diff parallel vs serial verdicts by
    position without re-sorting."""
    budget = RunBudget(approval)
    n = max(1, plan.n)
    with ThreadPoolExecutor(max_workers=n) as pool:
        futures = [pool.submit(_run_one, case, session_factory, run_fn, budget) for case in cases]
        return [f.result() for f in futures]


def default_session_factory(
    project: Project, secrets: object, run_dir: object,
    session_cls: Callable[..., object] | None = None,
) -> SessionFactory:
    """PR2, the real (non-fake) integration: each case gets its OWN
    `BrowserSession` against its OWN profile directory (`case.id`-scoped), so
    no case run alongside a sibling ever observes that sibling's
    cookies/storage state. Deliberately different from `ui/routes_runs.py`'s
    single shared, persistent profile a normal (serial) run reuses for login
    continuity across cases -- that reuse is correct there because nothing
    runs alongside it; here siblings run at the same time, so isolation, not
    continuity, is the property that must hold.

    AT-572: every session still shares the same `run_dir` (screenshots stay
    reachable at the run's own directory, which `grade()`/the run view
    already resolve) -- but each case's `SessionState.evidence_prefix` is set
    to its own `case.id` here, so `BrowserSession.screenshot()` nests every
    file under `run_dir/<case.id>/` instead of restarting the same `01-...`
    filename directly in the shared `run_dir`, where two siblings used to
    collide on the identical path."""
    from autotester.browser.session import BrowserSession
    from autotester.core.paths import ProjectPaths

    build = session_cls or BrowserSession

    def _factory(case: Case) -> object:
        paths = ProjectPaths(f"{project.slug}-parallel-{case.id[:12]}")
        session = build(project, secrets, run_dir, paths)
        state = getattr(session, "state", None)
        if state is not None:
            state.evidence_prefix = case.id
        start = getattr(session, "start", None)
        return start() if callable(start) else session

    return _factory
