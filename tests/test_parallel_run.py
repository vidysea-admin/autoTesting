"""PARALLEL_RUN. Contract: qa/contracts/parallel-run.md PR1-PR7.

Fakes only -- no real Playwright browser (RAM RULE), and `plan_parallel_run`'s
RAM/CPU inputs are always injected so no test depends on this host's live
memory (never falsify against the live tree, applied to a measurement too).
"""

from __future__ import annotations

import itertools
import threading
import time

from autotester.schema.approval import RunApproval
from autotester.schema.case import Case
from autotester.schema.enums import (
    Action,
    ApprovalKind,
    CaseClass,
    CaseKind,
    Outcome,
    WritePolicy,
)
from autotester.schema.flowspec import Step
from autotester.schema.project import Project
from autotester.schema.run import RawResult
from autotester.stages.parallel_run import (
    DEFAULT_PER_CONTEXT_MB,
    RunBudget,
    action_cost,
    default_session_factory,
    plan_parallel_run,
    run_cases,
)


def _project(
    *, max_parallel: int = 1, write_policy: WritePolicy = WritePolicy.READ_ONLY,
) -> Project:
    return Project(slug="p1", name="P1", base_url="https://p1.test",
                    max_parallel=max_parallel, write_policy=write_policy)


def _case(idx: int, n_steps: int = 1) -> Case:
    # Case.id hashes (project, flow_id, case_class, steps) -- not title -- so
    # the target must carry `idx` or two cases collide onto the same id.
    steps = [Step(order=i, action=Action.CLICK, target=f"#c{idx}-{i}") for i in range(n_steps)]
    return Case(project="p1", flow_id="f1", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
                title=f"case-{idx}", steps=steps)


class FakeSession:
    """Identity + per-instance "storage" so leakage is checkable."""

    def __init__(self, owner: str) -> None:
        self.owner = owner
        self.storage: dict[str, str] = {}
        self.closed = False

    def close(self) -> None:
        self.closed = True


def _isolated_factory(created: list[FakeSession]):
    def factory(case: Case) -> FakeSession:
        session = FakeSession(case.id)
        created.append(session)
        return session
    return factory


# -- PR1: N is bounded and the bound is recorded -----------------------------

def test_pr1_n_is_min_of_config_ceiling_and_measured_budget() -> None:
    project = _project(max_parallel=8)
    free_ram_mb = 2048.0 + 3 * DEFAULT_PER_CONTEXT_MB  # exactly 3 RAM slots
    plan = plan_parallel_run(project, cpu_count=8, free_ram_mb=free_ram_mb)
    assert (plan.n, plan.bound_by, plan.config_ceiling, plan.measured_budget) == (3, "budget", 8, 3)

    cases = [_case(i) for i in range(6)]
    concurrent = peak = 0
    lock = threading.Lock()

    def run_fn(case: Case, session: object) -> RawResult:
        nonlocal concurrent, peak
        with lock:
            concurrent += 1
            peak = max(peak, concurrent)
        time.sleep(0.05)
        with lock:
            concurrent -= 1
        return RawResult(case_id=case.id, outcome=Outcome.COMPLETED)

    run_cases(cases, plan, _isolated_factory([]), run_fn)
    assert peak <= 3


def test_pr1_config_ceiling_binds_when_it_is_the_smaller_term() -> None:
    project = _project(max_parallel=2)
    plan = plan_parallel_run(project, cpu_count=8, free_ram_mb=2048.0 + 20 * DEFAULT_PER_CONTEXT_MB)
    assert (plan.n, plan.bound_by) == (2, "config")


# -- PR2: each case gets an isolated session, no shared session leak --------

def test_pr2_each_case_gets_its_own_session_no_shared_state() -> None:
    login_case, other_case = _case(0), _case(1)
    created: list[FakeSession] = []
    factory = _isolated_factory(created)

    def run_fn(case: Case, session: object) -> RawResult:
        assert isinstance(session, FakeSession)
        if case.id == login_case.id:
            session.storage["cookie"] = "secret-session-token"
        else:
            # never see the login case's storage, even in the same process
            assert "cookie" not in session.storage
        return RawResult(case_id=case.id, outcome=Outcome.COMPLETED)

    plan = plan_parallel_run(_project(max_parallel=2), cpu_count=8, free_ram_mb=1e9)
    run_cases([login_case, other_case], plan, factory, run_fn)
    assert len({id(s) for s in created}) == 2
    assert all(s.closed for s in created)


def test_pr2_default_session_factory_gives_each_case_a_distinct_profile() -> None:
    captured: list[object] = []

    class FakeBrowserSession:
        def __init__(
            self, project: Project, secrets: object, run_dir: object, paths: object,
        ) -> None:
            captured.append(paths)
            self.paths = paths

        def start(self) -> FakeBrowserSession:
            return self

    factory = default_session_factory(_project(), secrets=None, run_dir=None,
                                       session_cls=FakeBrowserSession)
    s1 = factory(_case(0))
    s2 = factory(_case(1))
    assert s1.paths.slug != s2.paths.slug  # type: ignore[attr-defined]
    assert s1.paths.profile_dir != s2.paths.profile_dir  # type: ignore[attr-defined]


# -- PR3: write-permitting projects run serially -----------------------------

def test_pr3_allow_writes_forces_serial_regardless_of_max_parallel() -> None:
    project = _project(max_parallel=4, write_policy=WritePolicy.ALLOW_WRITES)
    plan = plan_parallel_run(project, cpu_count=8, free_ram_mb=1e9)
    assert (plan.n, plan.bound_by) == (1, "write_policy")

    intervals: list[tuple[float, float]] = []
    lock = threading.Lock()

    def run_fn(case: Case, session: object) -> RawResult:
        start = time.monotonic()
        time.sleep(0.03)
        end = time.monotonic()
        with lock:
            intervals.append((start, end))
        return RawResult(case_id=case.id, outcome=Outcome.COMPLETED)

    run_cases([_case(i) for i in range(3)], plan, _isolated_factory([]), run_fn)
    intervals.sort()
    for (_, end), (next_start, _) in itertools.pairwise(intervals):
        assert end <= next_start  # never two in flight at once


# -- PR4: verdict parity, parallel == serial ---------------------------------

def _outcome_for(case: Case) -> Outcome:
    return Outcome.COMPLETED if int(case.title.split("-")[1]) % 2 == 0 else Outcome.ERRORED


_DURATIONS: dict[str, float] = {}


def _timed_run_fn(case: Case, session: object) -> RawResult:
    time.sleep(_DURATIONS[case.id])
    outcome = _outcome_for(case)
    return RawResult(case_id=case.id, outcome=outcome, error=None if outcome
                      is Outcome.COMPLETED else "boom")


def test_pr4_parallel_verdicts_equal_serial_verdicts() -> None:
    cases = [_case(i) for i in range(4)]  # varied durations so completion order != submit order
    for c, d in zip(cases, [0.05, 0.01, 0.03, 0.02], strict=True):
        _DURATIONS[c.id] = d

    serial_plan = plan_parallel_run(_project(max_parallel=1), cpu_count=8, free_ram_mb=1e9)
    parallel_plan = plan_parallel_run(_project(max_parallel=4), cpu_count=8, free_ram_mb=1e9)
    serial = run_cases(cases, serial_plan, _isolated_factory([]), _timed_run_fn)
    parallel = run_cases(cases, parallel_plan, _isolated_factory([]), _timed_run_fn)

    assert {r.case_id: r.outcome for r in serial} == {r.case_id: r.outcome for r in parallel}
    assert [r.case_id for r in parallel] == [c.id for c in cases]  # order survives concurrency


# -- PR5: parallel is faster for N>=2 ----------------------------------------

def test_pr5_parallel_is_faster_than_serial_for_n_ge_2() -> None:
    cases = [_case(i) for i in range(4)]

    def run_fn(case: Case, session: object) -> RawResult:
        time.sleep(0.15)
        return RawResult(case_id=case.id, outcome=Outcome.COMPLETED)

    serial_plan = plan_parallel_run(_project(max_parallel=1), cpu_count=8, free_ram_mb=1e9)
    parallel_plan = plan_parallel_run(_project(max_parallel=4), cpu_count=8, free_ram_mb=1e9)

    t0 = time.monotonic()
    run_cases(cases, serial_plan, _isolated_factory([]), run_fn)
    serial_s = time.monotonic() - t0

    t0 = time.monotonic()
    run_cases(cases, parallel_plan, _isolated_factory([]), run_fn)
    parallel_s = time.monotonic() - t0

    # strictly less (PR5), with a margin so ordinary scheduler jitter can never
    # flip this -- a real 4x concurrency win is nowhere near the noise floor
    assert parallel_s < serial_s * 0.7


# -- PR6: a crash in one case does not abort its siblings -------------------

def test_pr6_one_case_crashing_does_not_abort_siblings() -> None:
    cases = [_case(i) for i in range(3)]

    def run_fn(case: Case, session: object) -> RawResult:
        if case.title == "case-1":
            raise ValueError("boom mid-case")
        return RawResult(case_id=case.id, outcome=Outcome.COMPLETED)

    plan = plan_parallel_run(_project(max_parallel=3), cpu_count=8, free_ram_mb=1e9)
    by_id = {r.case_id: r for r in run_cases(cases, plan, _isolated_factory([]), run_fn)}

    crashed = by_id[cases[1].id]
    assert crashed.outcome is Outcome.ERRORED
    assert "ValueError" in (crashed.error or "")
    assert by_id[cases[0].id].outcome is Outcome.COMPLETED
    assert by_id[cases[2].id].outcome is Outcome.COMPLETED


# -- PR7: consent bounds apply to the whole run, never widened per worker ---

def test_pr7_aggregate_budget_is_not_multiplied_by_concurrency() -> None:
    cases = [_case(i, n_steps=3) for i in range(4)]  # cost 3 each -> 12 if ungated
    naive_total = sum(action_cost(c) for c in cases)
    assert naive_total == 12

    approval = RunApproval(
        project="p1", run_kind=ApprovalKind.CRAWL, target="https://p1.test", scope="test",
        max_actions=10, max_probes=0, wall_clock_s=0.0,
        granted_by="tester", granted_at="2026-09-25T00:00:00", expires_at="2099-01-01",
    )

    def run_fn(case: Case, session: object) -> RawResult:
        return RawResult(case_id=case.id, outcome=Outcome.COMPLETED)

    plan = plan_parallel_run(_project(max_parallel=4), cpu_count=8, free_ram_mb=1e9)
    results = run_cases(cases, plan, _isolated_factory([]), run_fn, approval=approval)

    def _exhausted(r: RawResult) -> bool:
        return r.outcome is Outcome.ERRORED and "budget exhausted" in (r.error or "")

    assert any(_exhausted(r) for r in results), "at least one case refused by the shared budget"
    ran_cost = sum(action_cost(c) for c, r in zip(cases, results, strict=True) if not _exhausted(r))
    assert ran_cost <= approval.max_actions < naive_total


def test_pr7_run_budget_try_consume_is_thread_safe_under_race() -> None:
    approval = RunApproval(
        project="p1", run_kind=ApprovalKind.CRAWL, target="https://p1.test", scope="test",
        max_actions=50, max_probes=0, wall_clock_s=0.0,
        granted_by="tester", granted_at="2026-09-25T00:00:00", expires_at="2099-01-01",
    )
    budget = RunBudget(approval)
    accepted = 0
    lock = threading.Lock()

    def worker() -> None:
        nonlocal accepted
        if budget.try_consume(actions=1):
            with lock:
                accepted += 1

    threads = [threading.Thread(target=worker) for _ in range(200)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert (accepted, budget.actions_used) == (50, 50)
