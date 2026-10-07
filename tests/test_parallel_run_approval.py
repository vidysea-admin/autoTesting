"""PARALLEL_RUN's consent seam: the run budget fails CLOSED (AT-570, AT-660).

Contract: qa/contracts/parallel-run.md PR7 plus core-invariants C12(b) --
"nothing supplied" must mean nothing granted, never everything granted, and a
zero bound is a measured zero rather than an absent one. Split out of
`tests/test_parallel_run.py`, which sits within a few lines of the 300 cap;
PR7's two existing budget tests moved here with the new rows so every assertion
about `RunBudget` and `RunApproval` lives in one file. `RunBudget` itself moved to
`stages/run_budget.py` in the same change, for the same cap.

Fakes only -- no real Playwright browser (RAM RULE). The shared project/case
fakes are imported from `test_parallel_run` rather than copied (C3), the same
way `test_ui_runs_parallel_trace.py` imports from `test_ui_runs`.
"""

from __future__ import annotations

import threading

import pytest
from test_parallel_run import _approval, _case, _isolated_factory, _project

from autotester.core.consent import ApprovalRequired, require_approval
from autotester.schema.case import Case
from autotester.schema.enums import ApprovalKind, Outcome
from autotester.schema.run import RawResult
from autotester.stages.parallel_run import plan_parallel_run, run_cases
from autotester.stages.run_budget import RunBudget, action_cost


def _ok(case: Case, session: object) -> RawResult:
    return RawResult(case_id=case.id, outcome=Outcome.COMPLETED)


def _plan(n: int):
    return plan_parallel_run(_project(max_parallel=n), cpu_count=8, free_ram_mb=1e9)


def _exhausted(r: RawResult) -> bool:
    return r.outcome is Outcome.ERRORED and "budget exhausted" in (r.error or "")


# -- AT-570: the absence of an approval is a refusal, never a permission -----

def test_a_run_budget_cannot_be_built_without_an_approval() -> None:
    """`RunBudget(None)` used to return True from `try_consume` forever."""
    with pytest.raises(ValueError, match="unapproved"):
        RunBudget(None)  # type: ignore[arg-type]


def test_run_cases_offers_no_approval_default_a_caller_can_omit() -> None:
    """The delivery mechanism, not only the branch: AT-570's real fail-open was
    `approval: RunApproval | None = None` at the `run_cases` seam -- a caller
    reached unlimited by passing nothing. With no default there is nothing to
    omit, so a future caller cannot re-acquire it by silence."""
    with pytest.raises(TypeError, match="approval"):
        run_cases([_case(0)], _plan(1), _isolated_factory([]), _ok)  # type: ignore[call-arg]


# -- AT-660: one field, one meaning -- 0 grants nothing on every axis --------

def test_the_gate_and_the_budget_agree_that_zero_bounds_grant_nothing() -> None:
    """The defect this closes was not that either side was wrong on its own:
    `core/consent.py:56` has no falsy guard, so it read `max_actions=0` as a
    ZERO budget and refused; `RunBudget` had one, so it read the same 0 as
    UNLIMITED and enforced nothing. One field, two opposite meanings, and the
    permissive side was the one that governed the run once it started. Both
    sides in one test, because two tests each checking one side is exactly how
    this survived."""
    approval = _approval(max_actions=0, wall_clock_s=0.0)
    cost = action_cost(_case(0))
    assert cost >= 1

    with pytest.raises(ApprovalRequired, match="narrower than this run"):
        require_approval([approval], project="p1", kind=ApprovalKind.LIVE_CASE,
                         target="https://p1.test", actions=cost, wall_clock_s=1.0)
    assert RunBudget(approval).try_consume(actions=cost) is False


def test_an_approval_granting_zero_actions_bounds_the_run_to_zero() -> None:
    """`max_actions=0` is `RunApproval`'s own field default AND `cli_crawl.py:241`
    `approve --max-actions`'s default, so the truthiness guard this replaces made
    the DEFAULT approval unbounded -- reachable by granting, not constructed in a
    test. (The three rows on disk in `projects/pathlynks/approvals.jsonl` carry
    40/150/200000 actions, so this axis is not zero THERE; `max_probes` is the one
    that is 0 on every row. The defect is in the code either way.)"""
    cases = [_case(i) for i in range(3)]
    results = run_cases(cases, _plan(3), _isolated_factory([]), _ok,
                        approval=_approval(max_actions=0))
    assert [r.case_id for r in results] == [c.id for c in cases]
    assert all(_exhausted(r) for r in results)


def test_an_approval_granting_zero_probes_refuses_a_probe() -> None:
    budget = RunBudget(_approval(max_actions=100, max_probes=0))
    assert budget.try_consume(probes=1) is False
    assert budget.try_consume(actions=1) is True


def test_an_approval_granting_zero_wall_clock_grants_no_time() -> None:
    """Deliberately an explicit `<= 0` refusal rather than `elapsed > granted`:
    `time.monotonic()` has ~15 ms resolution on Windows, so a strict comparison
    against 0.0 would pass or fail depending on how fast the machine was -- a
    fail-closed rule that is only usually closed is not one."""
    budget = RunBudget(_approval(max_actions=100, wall_clock_s=0.0))
    assert budget.try_consume(actions=1) is False
    assert RunBudget(_approval(max_actions=100, wall_clock_s=60.0)).try_consume(actions=1) is True


def test_the_shape_the_approve_command_writes_with_no_bound_flags_grants_nothing() -> None:
    """The CLI grant path, verbatim: `cli_crawl.py:241-243` defaults
    `--max-actions` to 0, `--max-probes` to 0 and `--wall-clock` to 0.0, with no
    `min=` on any of them, so `autotester approve --project X --kind live_case`
    with no bound flags writes a row that is zero on EVERY axis. Under the old
    truthiness guards that row ran unbounded on every axis. The disk evidence is
    narrower than the defect (the UI form carries `min='1'` on two of the three,
    so a UI-granted row cannot zero them) and must not be read as shrinking it.

    Note the asymmetry this pins: the command whose job is to SET a bound
    defaults to unbounded (`approve`, 0/0/0.0) while the command it bounds
    defaults to bounded (`crawl`, `cli_crawl.py:60-61`, 200 actions / 600s).
    Changing those defaults is out of this unit's scope -- see Disclosures."""
    cli_grant_row = _approval(max_actions=0, max_probes=0, wall_clock_s=0.0)
    budget = RunBudget(cli_grant_row)
    assert budget.try_consume(actions=1) is False
    assert budget.try_consume(probes=1) is False
    assert budget.try_consume() is False  # not even a zero-cost consume


# -- PR7: consent bounds apply to the whole run, never widened per worker ----

def test_pr7_aggregate_budget_is_not_multiplied_by_concurrency() -> None:
    """CN10: the bound and the MARGIN are named, so the refusal is demonstrably
    the bound firing rather than a number chosen large enough that exceeding it
    was arranged. Granted 10 actions; the run wants 12 (4 cases x 3 steps), so
    it is over by 2 -- and the last case to ask must be refused."""
    cases = [_case(i, n_steps=3) for i in range(4)]  # cost 3 each -> 12 if ungated
    naive_total = sum(action_cost(c) for c in cases)
    approval = _approval(max_actions=10)  # a REAL non-zero bound, narrower than the run
    assert (approval.max_actions, naive_total, naive_total - approval.max_actions) == (10, 12, 2)
    results = run_cases(cases, _plan(4), _isolated_factory([]), _ok, approval=approval)

    assert any(_exhausted(r) for r in results), "at least one case refused by the shared budget"
    ran_cost = sum(action_cost(c) for c, r in zip(cases, results, strict=True)
                   if not _exhausted(r))
    assert ran_cost <= approval.max_actions < naive_total


def test_pr7_run_budget_try_consume_is_thread_safe_under_race() -> None:
    budget = RunBudget(_approval(max_actions=50))
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


@pytest.mark.parametrize("axis", ["actions", "probes"])
@pytest.mark.parametrize("amount", [-1, 0.5, float("nan"), float("inf"), True])
def test_budget_spends_cannot_replenish_or_bypass(axis, amount):
    budget = RunBudget(_approval(max_actions=2, max_probes=2))
    assert budget.try_consume(actions=1, probes=1)
    with pytest.raises(ValueError):
        budget.try_consume(**{axis: amount})
    assert budget.try_consume(actions=1, probes=1)
    assert not budget.try_consume(**{axis: 1})
    with pytest.raises(RuntimeError, match=f"max_{axis}"):
        budget.check()  # a tripped live brake forbids even zero-spend continuation


def test_budget_exact_deadline_and_positive_timeout(monkeypatch):
    from autotester.stages import run_budget

    clock = [10.0]
    monkeypatch.setattr(run_budget.time, "monotonic", lambda: clock[0])
    budget = RunBudget(_approval(wall_clock_s=1.0))
    clock[0] = 10.75
    assert 0 < budget.remaining_ms() <= 250
    clock[0] = 11.0
    assert not budget.try_consume()
    assert budget.stop_reason == "wall_clock_s"
    with pytest.raises(RuntimeError, match="wall_clock_s"):
        budget.check()


def test_explicit_budget_has_no_reservation_and_must_match_approval():
    approval = _approval(max_actions=1)
    budget = RunBudget(approval)
    def spend(case, session):
        assert session.budget is budget
        assert budget.try_consume(actions=1)
        return _ok(case, session)
    results = run_cases([_case(0)], _plan(1), _isolated_factory([]), spend,
                        approval=approval, budget=budget)
    assert results[0].outcome is Outcome.COMPLETED and budget.actions_used == 1
    with pytest.raises(ValueError, match="approval"):
        run_cases([], _plan(1), _isolated_factory([]), _ok,
                  approval=_approval(max_actions=2), budget=budget)


def test_probe_contention_has_one_aggregate_last_slot():
    budget = RunBudget(_approval(max_probes=2))
    barrier = threading.Barrier(4)
    accepted = []
    def spend():
        barrier.wait(timeout=5)
        accepted.append(budget.try_consume(probes=1))
    threads = [threading.Thread(target=spend) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)
    assert all(not thread.is_alive() for thread in threads)
    assert sorted(accepted) == [False, False, True, True] and budget.probes_used == 2
