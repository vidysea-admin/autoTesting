"""Serial and parallel case-execution helpers for a triggered run.

Split out of `ui/routes_runs.py` (AT-567 -- the file sat at the C2 300-line
cap with no headroom) into its own module: `_run_cases_serially` and
`_run_cases_in_parallel` are the two execution strategies `_execute_with_
trace` (still in `routes_runs.py`) picks between by `ParallelPlan.n`, and
`_run_entry_case`/`_run_and_grade_resilient` are helpers only they use.
Nothing here is itself a FastAPI route.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from autotester.browser.secrets import SecretStore
from autotester.browser.session import BrowserSession
from autotester.core.paths import ProjectPaths
from autotester.providers.langchain_fallback import LangChainFallbackProvider
from autotester.schema.case import Case
from autotester.schema.enums import Outcome
from autotester.schema.project import Project
from autotester.schema.run import RawResult
from autotester.schema.verdict import Verdict
from autotester.stages.parallel_run import ParallelPlan, default_session_factory, run_cases
from autotester.stages.run_case_pipeline import (
    grade_errored_result,
    run_and_grade_case_resilient,
)
from autotester.store.project_store import ProjectStore


def _run_and_grade_resilient(
    case: Case, session: BrowserSession, judge: LangChainFallbackProvider, run_id: str,
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
        return run_and_grade_case_resilient(case, session, judge, run_id, store)
    except Exception as exc:  # AT-574: reported as this case's own ERRORED result
        result = RawResult(case_id=case.id, outcome=Outcome.ERRORED,
                            error=f"{type(exc).__name__}: {exc}")
        verdict = grade_errored_result(case, result, judge, run_id, store)
        return result, verdict


def _run_entry_case(
    case: Case, project: Project, secrets: SecretStore, run_dir: Path, slug: str,
    judge: LangChainFallbackProvider, run_id: str, store: ProjectStore,
) -> tuple[RawResult, Verdict]:
    """A dedicated, wiped-before-every-run profile so an entry-screen case is
    always exercised from a genuinely logged-out state -- order- and
    cross-run-independent.

    AT-577 cycle 2: shares `run_dir` with the shared session; unprefixed,
    both number screenshots from 01 and collide. `evidence_prefix = case.id`
    (AT-572's mechanism) nests this case's files under `run_dir/<case.id>/`."""
    entry_paths = ProjectPaths(f"{slug}-entry-test")
    shutil.rmtree(entry_paths.profile_dir, ignore_errors=True)
    session = BrowserSession(project, secrets, run_dir, entry_paths)
    session.state.evidence_prefix = case.id
    session.start()
    try:
        return _run_and_grade_resilient(case, session, judge, run_id, store)
    finally:
        session.close()


def _run_cases_serially(
    cases: list[Case], entry_flags: list[bool], project: Project, secrets: SecretStore,
    run_dir: Path, paths: ProjectPaths, slug: str, judge: LangChainFallbackProvider,
    run_id: str, store: ProjectStore,
) -> None:
    """`plan.n <= 1` (the default, AT-562/PR1): one shared session reused
    across every non-entry case (login continuity across the whole run), one
    dedicated wiped profile per entry case (AT-044). Not routed through
    `run_cases`: that module's contract starts and closes one session per
    case (PR2's isolation), which would tear down this shared session after
    the first case.

    AT-574: each case goes through `_run_and_grade_resilient` -- before this
    fix, a grader/provider exception, or a `run_case` crash, propagated
    straight out of this loop, 500ing `trigger_run` before the remaining
    cases ran or the `Run` record was saved. Now a crash is reported as that
    case's own result+verdict and the loop, and the run, continue.

    AT-576: every entry case runs to completion first -- its own dedicated
    session, started and closed by `_run_entry_case` -- BEFORE the shared
    session below ever starts (same order `_run_cases_in_parallel` uses).
    Starting the shared session first and only THEN hitting an entry case
    used to start a SECOND sync Playwright driver on this thread while the
    shared one was still live -- Playwright raises "Sync API inside the
    asyncio loop" the moment that happens, 500ing the whole run. Entry
    cases first, one shared session started once, never nests two."""
    for case, is_entry in zip(cases, entry_flags, strict=True):
        if not is_entry:
            continue
        result, verdict = _run_entry_case(case, project, secrets, run_dir, slug, judge, run_id,
                                          store)
        store.save_result(run_id, result)
        store.save_verdict(run_id, verdict)

    normal_cases = [c for c, is_entry in zip(cases, entry_flags, strict=True) if not is_entry]
    if not normal_cases:
        return
    session = BrowserSession(project, secrets, run_dir, paths)
    session.start()
    try:
        for case in normal_cases:
            result, verdict = _run_and_grade_resilient(case, session, judge, run_id, store)
            store.save_result(run_id, result)
            store.save_verdict(run_id, verdict)
    finally:
        session.close()


def _run_cases_in_parallel(
    cases: list[Case], entry_flags: list[bool], plan: ParallelPlan, project: Project,
    secrets: SecretStore, run_dir: Path, slug: str, judge: LangChainFallbackProvider,
    run_id: str, store: ProjectStore,
) -> None:
    """`plan.n > 1` (T-173/AT-562): fan the non-entry cases out through the
    real `stages.parallel_run.run_cases` at the planned width, each in its
    own isolated browser context (PR2). Entry cases keep their dedicated
    wiped profile (AT-044) and always run serially, before the fan-out — an
    entry-screen assertion is about one logged-out state, not something
    concurrency helps."""
    entry_cases = [c for c, is_entry in zip(cases, entry_flags, strict=True) if is_entry]
    normal_cases = [c for c, is_entry in zip(cases, entry_flags, strict=True) if not is_entry]

    for case in entry_cases:
        result, verdict = _run_entry_case(case, project, secrets, run_dir, slug, judge, run_id,
                                          store)
        store.save_result(run_id, result)
        store.save_verdict(run_id, verdict)

    if not normal_cases:
        return
    case_by_id = {c.id: c for c in normal_cases}
    verdicts: dict[str, Verdict] = {}

    def _run_and_grade(case: Case, session: object) -> RawResult:
        # AT-573: run_and_grade_case_resilient captures the real RawResult
        # BEFORE grading, so a grader/provider exception (caught inside it)
        # never discards a COMPLETED run's evidence -- it only downgrades
        # the verdict to INCONCLUSIVE, naming the grader failure.
        result, verdict = run_and_grade_case_resilient(case, session, judge, run_id, store)
        verdicts[case.id] = verdict
        return result

    session_factory = default_session_factory(project, secrets, run_dir)
    for result in run_cases(normal_cases, plan, session_factory, _run_and_grade):
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
        store.save_result(run_id, result)
        store.save_verdict(run_id, verdict)
