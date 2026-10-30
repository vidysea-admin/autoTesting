"""Serial and parallel case-execution helpers for a triggered run.

Split out of `ui/routes_runs.py` (AT-567 -- the file sat at the C2 300-line
cap with no headroom) into its own module: `_run_cases_serially` and
`_run_cases_in_parallel` are the two execution strategies `_execute_with_
trace` (still in `routes_runs.py`) picks between by `ParallelPlan.n`, and
`_run_entry_case`/`_run_and_grade_resilient` are helpers only they use.
Nothing here is itself a FastAPI route.
"""

from __future__ import annotations

import contextlib
from contextlib import AbstractContextManager, nullcontext
from pathlib import Path

from autotester.browser.entry_reset import reset_to_logged_out
from autotester.browser.profiles import MAIN_ACCOUNT, restore_session
from autotester.browser.profiles import wipe_entry_profile as _wipe_entry_profile
from autotester.browser.secrets import SecretStore
from autotester.browser.session import BrowserSession
from autotester.core.paths import ProjectPaths
from autotester.core.trace import traced_phase
from autotester.providers.base import Provider
from autotester.schema.approval import RunApproval
from autotester.schema.case import Case
from autotester.schema.enums import Outcome, Result
from autotester.schema.project import Project
from autotester.schema.run import RawResult
from autotester.schema.verdict import Verdict
from autotester.stages.browser_recovery import BrowserRecovery, closed_verdict, is_browser_closed
from autotester.stages.parallel_run import ParallelPlan, default_session_factory, run_cases
from autotester.stages.run_budget import RunBudget
from autotester.stages.run_case_pipeline import (
    grade_errored_result,
    run_and_grade_case_resilient,
)
from autotester.store.project_store import ProjectStore
from autotester.ui.entry_browser import EntryBrowserPool, order_entry_cases


def _trace_of(judge: Provider):
    """The run's `TraceWriter` (attached to the judge by `run_cases_traced`), or None."""
    return getattr(judge, "trace", None)


def _housekeeping(budget: RunBudget) -> AbstractContextManager[object]:
    """The budget's housekeeping scope (non-browser time, held off the approval clock); a
    budget stand-in without one costs nothing."""
    scope = getattr(budget, "housekeeping", None)
    return scope() if callable(scope) else nullcontext()


def _save_case(store: ProjectStore, run_id: str, result: RawResult, verdict: Verdict,
               judge: Provider) -> None:
    """Persist one graded case as the traced `save_result` phase."""
    with traced_phase(_trace_of(judge), result.case_id, "save_result"):
        store.save_result(run_id, result)
        store.save_verdict(run_id, verdict)


def _start_session(session: BrowserSession, judge: Provider, budget: RunBudget,
                   case_id: str | None) -> None:
    """Launch the browser as the traced `session_start` phase. Waiting for Chromium to come up
    is not the browser acting on the target, so it is housekeeping time, not approval clock."""
    session.trace = _trace_of(judge)
    with traced_phase(session.trace, case_id, "session_start"), _housekeeping(budget):
        session.start()


def _run_and_grade_resilient(
    case: Case, session: BrowserSession, judge: Provider, run_id: str,
    store: ProjectStore,
) -> tuple[RawResult, Verdict]:
    """Never let one case take the whole run down (AT-574). `run_and_grade_
    case_resilient` already keeps a real COMPLETED result when only grading
    fails after execution (AT-573); this adds the outer guard for an
    exception in `run_case` itself -- the same shape `stages/parallel_run.py
    ::_run_one` already applies on the parallel path, expressed here for
    callers that run one case at a time, so every case still gets a saved
    result+verdict through `grade_errored_result` (AT-568), never a bare
    exception."""
    try:
        budget = getattr(session, "budget", None)
        if budget is not None:
            budget.check_start()
        with traced_phase(_trace_of(judge), case.id, "case_pipeline"):
            return run_and_grade_case_resilient(case, session, judge, run_id, store)
    except Exception as exc:  # AT-574: reported as this case's own ERRORED result
        result = RawResult(case_id=case.id, outcome=Outcome.ERRORED,
                            error=f"{type(exc).__name__}: {exc}")
        verdict = grade_errored_result(case, result, judge, run_id, store)
        return result, verdict


def _entry_pool(
    project: Project, secrets: SecretStore, run_dir: Path, slug: str, judge: Provider,
    budget: RunBudget,
) -> EntryBrowserPool:
    """The run's entry browser pool (D-115): a launch is a wiped-profile browser (AT-733 / RU5,
    fail closed), a reuse is a logged-out reset; both are traced, non-case time."""
    entry_paths = ProjectPaths(f"{slug}-entry-test")

    def open_session(case: Case) -> BrowserSession:
        wipe = traced_phase(_trace_of(judge), case.id, "entry_profile_wipe")
        with wipe, _housekeeping(budget):
            _wipe_entry_profile(entry_paths.profile_dir)
        session = BrowserSession(project, secrets, run_dir, entry_paths, record_video=True)
        session.state.evidence_prefix = case.id
        session.budget = budget
        budget.check_start()
        _start_session(session, judge, budget, case.id)
        return session

    def reset(session: BrowserSession, case: Case) -> None:
        with traced_phase(_trace_of(judge), case.id, "entry_reset"), _housekeeping(budget):
            reset_to_logged_out(session)

    return EntryBrowserPool(project, open_session=open_session, reset=reset)


def _run_entry_case(
    case: Case, project: Project, secrets: SecretStore, run_dir: Path, slug: str,
    judge: Provider, run_id: str, store: ProjectStore,
    *, budget: RunBudget, pool: EntryBrowserPool | None = None,
) -> tuple[RawResult, Verdict]:
    """An entry-screen case starts from a genuinely logged-out state -- order- and cross-run-
    independent: a wiped-profile launch, or (D-115) a logged-out reset of the run's one entry
    browser (`pool`). With no `pool` the case owns a private one and closes it, exactly the
    pre-D-115 launch-run-close.

    AT-577 cycle 2: shares `run_dir` with the shared session; unprefixed, both number screenshots
    from 01 and collide. The pool sets `evidence_prefix = case.id` (AT-572's mechanism), nesting
    this case's files under `run_dir/<case.id>/`."""
    own = pool is None
    pool = pool or _entry_pool(project, secrets, run_dir, slug, judge, budget)
    session: BrowserSession | None = None
    outcome: tuple[RawResult, Verdict] | None = None
    try:
        try:
            session = pool.acquire(case)
            outcome = _run_and_grade_resilient(case, session, judge, run_id, store)
        except Exception as exc:
            result = RawResult(case_id=case.id, outcome=Outcome.ERRORED,
                               error=secrets.redactor().scrub(f"{type(exc).__name__}: {exc}"))
            outcome = result, grade_errored_result(case, result, judge, run_id, store)
        _save_case(store, run_id, *outcome, judge)  # durable BEFORE teardown can stall (RTS-3)
        return outcome
    finally:
        if session is not None:
            passed = outcome is not None and outcome[1].result is Result.PASS
            pool.release(case, session, outcome[0] if outcome else None, passed=passed)
        if own:
            pool.close()


def _run_normal_cases(
    cases: list[Case], pool: EntryBrowserPool, project: Project, secrets: SecretStore,
    run_dir: Path, paths: ProjectPaths, judge: Provider, run_id: str, store: ProjectStore,
    *, budget: RunBudget,
) -> None:
    """The logged-in cases of a serial tier (AT-576). They run in the entry login's session when a
    login just passed (D-115: no second launch, no re-login), else in the shared-profile session.
    The lent session stays in the pool for the next tier; a shared-profile one is closed here."""
    lent = pool.lend()
    if lent is not None:
        lent.state.evidence_prefix = ""  # ordinary cases keep the shared-run layout
    else:
        pool.close()  # one live driver at a time
    session = lent or BrowserSession(project, secrets, run_dir, paths, record_video=True)
    session.budget = budget
    startup_error = None
    try:
        try:
            budget.check_start()
            if lent is None:
                _start_session(session, judge, budget, None)
                restore_session(session, project, MAIN_ACCOUNT)  # U12: store on only (never entry)
            budget.check()
        except Exception as exc:
            startup_error = secrets.redactor().scrub(f"{type(exc).__name__}: {exc}")
        recovery = BrowserRecovery(session)
        for case in cases:
            relaunched = False
            if recovery.stop_reason is not None:
                startup_error = recovery.stop_reason
            if startup_error is None:
                result, verdict = _run_and_grade_resilient(case, session, judge, run_id, store)
                if is_browser_closed(result):  # AT-888: only this case is lost; relaunch, go on
                    verdict = closed_verdict(result, run_id)
                    relaunched = recovery.recover()
            else:
                result = RawResult(case_id=case.id, outcome=Outcome.ERRORED, error=startup_error)
                verdict = grade_errored_result(case, result, judge, run_id, store)
            _save_case(store, run_id, result, verdict, judge)
            if lent is not None:
                pool.note_shared(result)
                if relaunched:  # the login died with the browser: replay it before the next case
                    startup_error = pool.relogin(
                        lambda c, s: _run_and_grade_resilient(c, s, judge, run_id, store)[1],
                        may_relaunch=recovery.spend)  # a login fallback launch is a relaunch too
                    session = recovery.session = pool.live() or session  # it may have replaced it
    finally:
        if lent is None:
            with contextlib.suppress(Exception):
                session.close()


def _run_cases_serially(
    cases: list[Case], entry_flags: list[bool], project: Project, secrets: SecretStore,
    run_dir: Path, paths: ProjectPaths, slug: str, judge: Provider,
    run_id: str, store: ProjectStore,
    *, budget: RunBudget, pool: EntryBrowserPool | None = None,
) -> None:
    """Entry cases first on the run's one entry browser (`pool`, kept across tiers by
    `run_cases_traced`; a private one is closed here), then the logged-in cases (AT-576)."""
    own = pool is None
    pool = pool or _entry_pool(project, secrets, run_dir, slug, judge, budget)
    try:
        entry_cases = [c for c, is_entry in zip(cases, entry_flags, strict=True) if is_entry]
        _run_entry_cases(entry_cases, project, secrets, run_dir, slug, judge, run_id, store,
                         budget=budget, pool=pool)
        normal = [c for c, is_entry in zip(cases, entry_flags, strict=True) if not is_entry]
        if normal:
            _run_normal_cases(normal, pool, project, secrets, run_dir, paths, judge, run_id,
                              store, budget=budget)
    finally:
        if own:
            pool.close()


def _run_entry_cases(
    entry_cases: list[Case], project: Project, secrets: SecretStore, run_dir: Path,
    slug: str, judge: Provider, run_id: str, store: ProjectStore,
    *, budget: RunBudget, pool: EntryBrowserPool | None = None,
) -> None:
    """The serial entry-case leg of both run shapes: the cases that need a logged-out page first,
    the login last (`order_entry_cases`), on one entry browser (D-115). Given a `pool` the caller
    owns it (the serial path keeps the login for what follows); otherwise it is closed here, before
    the fan-out. Extracted so `_run_cases_in_parallel` stays inside the 50-line design cap (C2);
    the ordering guarantee is asserted by `tests/test_ui_runs_serial_entry_order.py`."""
    own = pool is None
    pool = pool or _entry_pool(project, secrets, run_dir, slug, judge, budget)
    try:
        for case in order_entry_cases(entry_cases, project):
            _run_entry_case(case, project, secrets, run_dir, slug, judge, run_id, store,
                            budget=budget, pool=pool)  # saves its own result before any close
    finally:
        if own:
            pool.close()


def _run_cases_in_parallel(
    cases: list[Case], entry_flags: list[bool], plan: ParallelPlan, project: Project,
    secrets: SecretStore, run_dir: Path, slug: str, judge: Provider,
    run_id: str, store: ProjectStore, approval: RunApproval,
    *, budget: RunBudget,
) -> None:
    """Run entry cases serially, then isolate siblings under the SAME budget.

    The budget must be the one this approval bound, checked before ANY entry-leg
    effect: an entry-only tier never reaches `run_cases`' own check (T-125)."""
    if not budget.matches(approval):
        raise ValueError("shared budget does not match approval")
    entry_cases = [c for c, is_entry in zip(cases, entry_flags, strict=True) if is_entry]
    normal_cases = [c for c, is_entry in zip(cases, entry_flags, strict=True) if not is_entry]
    _run_entry_cases(entry_cases, project, secrets, run_dir, slug, judge, run_id, store,
                     budget=budget)
    if not normal_cases:
        return
    case_by_id = {c.id: c for c in normal_cases}
    verdicts: dict[str, Verdict] = {}

    def _run_and_grade(case: Case, session: object) -> RawResult:
        # AT-573: run_and_grade_case_resilient captures the real RawResult
        # BEFORE grading, so a grader/provider exception (caught inside it)
        # never discards a COMPLETED run's evidence -- it only downgrades
        # the verdict to INCONCLUSIVE, naming the grader failure.
        result, verdict = _run_and_grade_resilient(case, session, judge, run_id, store)
        verdicts[case.id] = verdict
        return result

    session_factory = default_session_factory(project, secrets, run_dir, record_video=True,
                                               budget=budget, trace=_trace_of(judge))
    for result in run_cases(normal_cases, plan, session_factory, _run_and_grade,
                            approval=approval, budget=budget):
        # AT-568/PR6: a session_factory crash, or any exception BEFORE
        # run_and_grade_case_resilient captures its own result, means
        # `_run_and_grade` above never ran to completion for this case, so
        # `verdicts` has no entry for it — `run_cases` still reports the
        # case as its own ERRORED RawResult (PR6), and that ERRORED outcome
        # is always safe to grade directly (grade_errored_result never
        # calls the judge for it).
        verdict = verdicts.get(result.case_id)
        if verdict is None:
            verdict = grade_errored_result(
                case_by_id[result.case_id], result, judge, run_id, store
            )
        _save_case(store, run_id, result, verdict, judge)
