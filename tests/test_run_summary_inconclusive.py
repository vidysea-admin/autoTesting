"""Bug 2026-10-28 (feedback-inbox item 1): a run's headline may say `passed` only when at least one
case was judged and none failed, errored, was inconclusive or went unjudged.

`run_service.report_for` is the one place the headline and exit code are derived (the CLI, the MCP
tools and `run-report` all read it), so the rule is tested there against stored runs.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from autotester.core.exit_codes import ExitCode
from autotester.schema.enums import Outcome, Result
from autotester.schema.project import Project
from autotester.schema.run import RawResult, Run
from autotester.schema.verdict import Verdict
from autotester.stages import run_service
from autotester.store.project_store import ProjectStore

P, F, I, B = Result.PASS, Result.FAIL, Result.INCONCLUSIVE, Result.BLOCKED   # noqa: E741


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ProjectStore:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    s = ProjectStore("demo", tmp_path)
    s.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test",
                           allowed_domains=["demo.test"]))
    return s


def stored_run(s: ProjectStore, cases: list[tuple[Outcome, Result | None]]) -> str:
    """One run; each case is (what the executor saw, the grader's verdict or None = ungraded)."""
    run = Run(project="demo", case_ids=[f"c{n}" for n in range(len(cases))])
    s.save_run(run)
    for n, (outcome, result) in enumerate(cases):
        s.save_result(run.id, RawResult(case_id=f"c{n}", outcome=outcome))
        if result is not None:
            s.save_verdict(run.id, Verdict(run_id=run.id, case_id=f"c{n}", result=result))
    return run.id


def headline(s: ProjectStore, cases: list[tuple[Outcome, Result | None]]):
    return run_service.report_for("demo", stored_run(s, cases))


def test_errored_inconclusive_case_is_not_passed(store) -> None:      # the reported bug
    report = headline(store, [(Outcome.ERRORED, I)])
    assert report.status == "inconclusive" and report.status != "passed"
    assert report.exit_code == ExitCode.INCONCLUSIVE != 0
    assert "1 inconclusive" in (report.message or "") and "1 errored" in (report.message or "")


def test_all_pass_still_passes(store) -> None:
    report = headline(store, [(Outcome.COMPLETED, P), (Outcome.COMPLETED, P)])
    assert (report.status, report.exit_code, report.message) == ("passed", 0, None)


def test_a_fail_is_still_failed(store) -> None:
    report = headline(store, [(Outcome.COMPLETED, P), (Outcome.COMPLETED, F)])
    assert (report.status, report.exit_code) == ("failed", ExitCode.TEST_FAILED)


def test_fail_outranks_inconclusive(store) -> None:
    report = headline(store, [(Outcome.ERRORED, I), (Outcome.COMPLETED, F)])
    assert (report.status, report.exit_code) == ("failed", ExitCode.TEST_FAILED)


def test_one_pass_plus_one_inconclusive_is_not_passed(store) -> None:
    report = headline(store, [(Outcome.COMPLETED, P), (Outcome.COMPLETED, I)])
    assert (report.status, report.exit_code) == ("inconclusive", ExitCode.INCONCLUSIVE)


@pytest.mark.parametrize("cases", [
    [(Outcome.COMPLETED, B)],                         # blocked is not a pass
    [(Outcome.ERRORED, None)],                        # errored and never graded
    [(Outcome.COMPLETED, P), (Outcome.NOT_RUN, None)],   # a case that did not run
    [(Outcome.COMPLETED, None)],                      # executed, no verdict on disk
    [],                                               # nothing judged at all
])
def test_unjudged_cases_never_read_as_passed(store, cases) -> None:
    report = headline(store, cases)
    assert (report.status, report.exit_code) == ("inconclusive", ExitCode.INCONCLUSIVE)


def test_exit_code_table_names_the_new_code() -> None:
    from autotester.core.exit_codes import exit_code_table

    assert f"{ExitCode.INCONCLUSIVE.value} " in exit_code_table()
