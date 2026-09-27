"""AT-573 (fix cycle 3): `run_and_grade_case_resilient` must keep a case's
real, COMPLETED `RawResult` (and its evidence) when only the GRADER fails
after execution -- never discard it the way `stages.parallel_run.run_cases`
discards a result when the callable it drives raises. Split from
`test_run_case_pipeline.py` at the 300-line cap. Contract:
qa/contracts/run-case-pipeline.md, qa/contracts/parallel-run.md PR6.
"""

from __future__ import annotations

from pathlib import Path

from test_run_case_pipeline import _case, _project, _session

from autotester.providers.mock import MockProvider
from autotester.schema.enums import Outcome, Result
from autotester.stages.run_case_pipeline import run_and_grade_case_resilient
from autotester.store.project_store import ProjectStore

__all__ = ["_case", "_project", "_session"]


def test_run_and_grade_case_resilient_keeps_the_real_result_when_grading_raises(
    tmp_path: Path,
) -> None:
    """AT-573: before this fix, `stages.parallel_run.run_cases` caught ANY
    exception from the case-runner callable -- including one raised by the
    JUDGE, after `run_case` already produced a real COMPLETED result with
    real screenshots -- and replaced it with a synthetic ERRORED `RawResult`
    carrying none of that evidence. `run_and_grade_case_resilient` captures
    the real result FIRST, so a grader failure only ever downgrades the
    VERDICT, never discards the result or its evidence. A `MockProvider` with
    no queued "judge" response raises exactly the way a real provider error
    would."""
    store = ProjectStore("demo", tmp_path)
    store.save_project(_project())
    case = _case()
    judge = MockProvider(responses={})  # .judge() raises: no queued response

    result, verdict = run_and_grade_case_resilient(
        case, _session(tmp_path), judge, "run_1", store
    )

    assert result.outcome is Outcome.COMPLETED
    assert result.evidence  # the real screenshot evidence, never discarded
    assert verdict.result is Result.INCONCLUSIVE
    assert verdict.grader_provider == "rule"
    assert "the grader failed after execution completed" in (verdict.scoreboard or "")
    assert "ProviderError" in (verdict.note or "")


def test_run_and_grade_case_resilient_matches_the_plain_path_when_grading_succeeds(
    tmp_path: Path,
) -> None:
    """No behavior change on the happy path: a successful grade looks exactly
    like `run_and_grade_case` would have produced."""
    from autotester.schema.verdict import Judgment

    store = ProjectStore("demo", tmp_path)
    store.save_project(_project())
    case = _case()
    judge = MockProvider(responses={"judge": [
        Judgment(result=Result.PASS, criteria_met=1, criteria_total=1, scoreboard="1/1 met")
    ]})

    result, verdict = run_and_grade_case_resilient(
        case, _session(tmp_path), judge, "run_1", store
    )

    assert result.outcome is Outcome.COMPLETED
    assert verdict.result is Result.PASS
    assert verdict.grader_provider == "mock"
