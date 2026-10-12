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
import os
import shutil
import stat
import time
from pathlib import Path

from autotester.browser.secrets import SecretStore
from autotester.browser.session import BrowserSession
from autotester.core.paths import ProjectPaths
from autotester.providers.base import Provider
from autotester.schema.approval import RunApproval
from autotester.schema.case import Case
from autotester.schema.enums import Outcome
from autotester.schema.project import Project
from autotester.schema.run import RawResult
from autotester.schema.verdict import Verdict
from autotester.stages.parallel_run import ParallelPlan, default_session_factory, run_cases
from autotester.stages.run_budget import RunBudget
from autotester.stages.run_case_pipeline import (
    grade_errored_result,
    run_and_grade_case_resilient,
)
from autotester.store.project_store import ProjectStore


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
        return run_and_grade_case_resilient(case, session, judge, run_id, store)
    except Exception as exc:  # AT-574: reported as this case's own ERRORED result
        result = RawResult(case_id=case.id, outcome=Outcome.ERRORED,
                            error=f"{type(exc).__name__}: {exc}")
        verdict = grade_errored_result(case, result, judge, run_id, store)
        return result, verdict


_WIPE_ATTEMPTS = 3
_WIPE_PAUSE_S = 0.3


def _clear_readonly(profile: Path) -> None:
    """Drop the read-only bit on everything under `profile` (Windows refuses to delete it)."""
    for root, dirs, files in os.walk(profile):
        for name in (*dirs, *files):
            with contextlib.suppress(OSError):
                os.chmod(Path(root) / name, stat.S_IWRITE | stat.S_IREAD)


def _wipe_entry_profile(profile: Path) -> None:
    """Remove the entry profile and positively establish it is gone (RU5, C12).
    An already-absent directory is success. A failed removal, a directory still
    present, or an existence check that itself raises all propagate as `OSError`
    (never `ignore_errors`, never `os.path.lexists`, which reads an error as
    'absent'), so the caller never starts a browser on a logged-in profile."""
    try:
        for attempt in range(_WIPE_ATTEMPTS):  # AT-733: Windows read-only bits / lingering handles
            try:
                with contextlib.suppress(FileNotFoundError):
                    shutil.rmtree(profile)
                break
            except OSError:
                _clear_readonly(profile)
                if attempt == _WIPE_ATTEMPTS - 1:
                    raise
                time.sleep(_WIPE_PAUSE_S)
        present = profile.exists()
    except OSError as exc:
        cause = f"{type(exc).__name__}: {exc}"
        raise OSError(f"entry profile not removed: {profile} ({cause})") from exc
    if present:
        raise OSError(f"entry profile not removed: {profile} (still present after removal)")


def _run_entry_case(
    case: Case, project: Project, secrets: SecretStore, run_dir: Path, slug: str,
    judge: Provider, run_id: str, store: ProjectStore,
    *, budget: RunBudget,
) -> tuple[RawResult, Verdict]:
    """A dedicated, wiped-before-every-run profile so an entry-screen case is
    always exercised from a genuinely logged-out state -- order- and
    cross-run-independent.

    AT-577 cycle 2: shares `run_dir` with the shared session; unprefixed,
    both number screenshots from 01 and collide. `evidence_prefix = case.id`
    (AT-572's mechanism) nests this case's files under `run_dir/<case.id>/`."""
    entry_paths = ProjectPaths(f"{slug}-entry-test")
    session: BrowserSession | None = None
    try:
        _wipe_entry_profile(entry_paths.profile_dir)  # AT-733 / RU5: fail closed, no browser
        session = BrowserSession(project, secrets, run_dir, entry_paths, record_video=True)
        session.state.evidence_prefix = case.id
        session.budget = budget
        budget.check_start()
        session.start()
        return _run_and_grade_resilient(case, session, judge, run_id, store)
    except Exception as exc:
        result = RawResult(case_id=case.id, outcome=Outcome.ERRORED,
                           error=secrets.redactor().scrub(f"{type(exc).__name__}: {exc}"))
        return result, grade_errored_result(case, result, judge, run_id, store)
    finally:
        if session is not None:
            with contextlib.suppress(Exception):
                session.close()


def _run_cases_serially(
    cases: list[Case], entry_flags: list[bool], project: Project, secrets: SecretStore,
    run_dir: Path, paths: ProjectPaths, slug: str, judge: Provider,
    run_id: str, store: ProjectStore,
    *, budget: RunBudget,
) -> None:
    """Run isolated entry cases first, then reuse one login session (AT-576)."""
    for case, is_entry in zip(cases, entry_flags, strict=True):
        if not is_entry:
            continue
        result, verdict = _run_entry_case(case, project, secrets, run_dir, slug, judge, run_id,
                                          store, budget=budget)
        store.save_result(run_id, result)
        store.save_verdict(run_id, verdict)

    normal_cases = [c for c, is_entry in zip(cases, entry_flags, strict=True) if not is_entry]
    if not normal_cases:
        return
    session = BrowserSession(project, secrets, run_dir, paths, record_video=True)
    session.budget = budget
    startup_error = None
    try:
        try:
            budget.check_start()
            session.start()
            budget.check()
        except Exception as exc:
            startup_error = secrets.redactor().scrub(f"{type(exc).__name__}: {exc}")
        for case in normal_cases:
            if startup_error is None:
                result, verdict = _run_and_grade_resilient(case, session, judge, run_id, store)
            else:
                result = RawResult(case_id=case.id, outcome=Outcome.ERRORED, error=startup_error)
                verdict = grade_errored_result(case, result, judge, run_id, store)
            store.save_result(run_id, result)
            store.save_verdict(run_id, verdict)
    finally:
        with contextlib.suppress(Exception):
            session.close()


def _run_entry_cases(
    entry_cases: list[Case], project: Project, secrets: SecretStore, run_dir: Path,
    slug: str, judge: Provider, run_id: str, store: ProjectStore,
    *, budget: RunBudget,
) -> None:
    """The serial entry-case leg of a parallel run: each entry case keeps its
    dedicated wiped profile (AT-044) and they always run one at a time, before
    the fan-out. Extracted from `_run_cases_in_parallel` so that function stays
    inside the 50-line design cap (core-invariants C2); the ordering guarantee
    it carries is asserted by `tests/test_ui_runs_serial_entry_order.py`."""
    for case in entry_cases:
        result, verdict = _run_entry_case(case, project, secrets, run_dir, slug, judge, run_id,
                                          store, budget=budget)
        store.save_result(run_id, result)
        store.save_verdict(run_id, verdict)


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
                                               budget=budget)
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
        store.save_result(run_id, result)
        store.save_verdict(run_id, verdict)
