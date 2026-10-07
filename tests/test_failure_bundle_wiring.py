"""AT-787 driver: the failure bundle is produced by the run pipeline (W1-W4).

Fully offline: a fake page whose `goto` raises on a chosen URL (an ERRORED run) or whose body
text lacks an expected string (an ASSERTION_FAILED run), a mock judge, and one planted secret
in the repo `.env`. Contract of the unit: qa/manifests/at787-bundle-wiring.md.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from autotester.browser.secrets import SecretStore
from autotester.browser.session import BrowserSession
from autotester.core.paths import ProjectPaths
from autotester.providers.mock import MockProvider
from autotester.schema.case import Case
from autotester.schema.enums import Action, CaseClass, CaseKind, Outcome, Result
from autotester.schema.flowspec import ExpectedState, Step
from autotester.schema.project import Project
from autotester.schema.verdict import Failure, Judgment
from autotester.stages import failure_bundle as fb
from autotester.stages.failure_bundle import load_bundle, recorded_failing_step
from autotester.stages.run_case_pipeline import run_and_grade_case, run_and_grade_case_resilient
from autotester.store.project_store import ProjectStore

SECRET = "Zq7-planted-Secret-9981"
BASE = "https://demo.test/"


class _Loc:
    def __init__(self, text: str) -> None:
        self._text = text

    def inner_text(self, **_: object) -> str:
        return self._text

    def count(self) -> int:
        return 0


class _Page:
    def __init__(self, broken_url: str | None, body: str, error: str) -> None:
        self.url, self._broken, self._body, self._error = BASE, broken_url, body, error

    def add_style_tag(self, content: str) -> None:
        pass

    def screenshot(self, path: str, full_page: bool = False, **_: object) -> None:
        Path(path).write_bytes(b"png")

    def goto(self, url: str, wait_until: str = "", **_: object) -> None:
        if url == self._broken:
            raise RuntimeError(self._error)
        self.url = url

    def locator(self, _sel: str) -> _Loc:
        return _Loc(self._body)

    def wait_for_timeout(self, _ms: int) -> None:
        pass


def _project() -> Project:
    return Project(slug="demo", name="Demo", base_url=BASE, allowed_domains=["demo.test"])


def _case(expect_text: str | None = None, note: str | None = None) -> Case:
    expected = ExpectedState(visible_text=[expect_text]) if expect_text else ExpectedState()
    steps = [Step(order=1, action=Action.NAVIGATE, target=BASE),
             Step(order=2, action=Action.NAVIGATE, target=BASE + "two", expected=expected,
                  note=note),
             Step(order=3, action=Action.NAVIGATE, target=BASE + "three")]
    return Case(project="demo", flow_id="f", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
                title="three pages", rationale="all three pages load", steps=steps)


def _env(tmp_path: Path, *, broken: str | None = None, body: str = "welcome",
         error: str = "boom") -> tuple[ProjectStore, BrowserSession]:
    store = ProjectStore("demo", tmp_path)
    store.save_project(_project())
    paths = ProjectPaths("demo", tmp_path)
    paths.env_file.parent.mkdir(parents=True, exist_ok=True)
    paths.env_file.write_text(f"DEMO_PW={SECRET}\n", encoding="utf-8")
    session = BrowserSession(_project(), SecretStore.load(_project(), paths.env_file, strict=False),
                             tmp_path / "run", paths)
    session._page = _Page(broken, body, error)
    session.state.run_dir.mkdir(parents=True, exist_ok=True)
    return store, session


def _judge(result: Result) -> MockProvider:
    failures = [Failure(criterion_id="c1", reason="not as described",
                        evidence_refs=["01-step01-navigate.png"])]
    failures = failures if result is Result.FAIL else []
    return MockProvider(responses={"judge": [Judgment(result=result, criteria_total=1,
                                                      scoreboard="x", failures=failures)]})


def _bundles(store: ProjectStore, run_id: str = "run_1") -> list[Path]:
    root = store.paths.bundles_dir(run_id)
    return sorted(root.iterdir()) if root.exists() else []


def _run(store, session, case, judge, fn=run_and_grade_case):
    return fn(case, session, judge, "run_1", store)


# -- W1 --------------------------------------------------------------------------------------

@pytest.mark.parametrize("fn", [run_and_grade_case, run_and_grade_case_resilient])
def test_an_errored_run_writes_a_complete_bundle(tmp_path: Path, fn) -> None:
    store, session = _env(tmp_path, broken=BASE + "two")
    result, _ = _run(store, session, _case(), _judge(Result.PASS), fn)
    assert result.outcome is Outcome.ERRORED
    (bundle,) = _bundles(store)
    assert load_bundle(bundle).run_id == "run_1"


@pytest.mark.parametrize("fn", [run_and_grade_case, run_and_grade_case_resilient])
def test_a_failed_verdict_writes_a_bundle(tmp_path: Path, fn) -> None:
    store, session = _env(tmp_path)
    _, verdict = _run(store, session, _case(), _judge(Result.FAIL), fn)
    assert verdict.result is Result.FAIL
    assert len(_bundles(store)) == 1


@pytest.mark.parametrize("fn", [run_and_grade_case, run_and_grade_case_resilient])
@pytest.mark.parametrize("graded", [Result.PASS, Result.INCONCLUSIVE])
def test_passing_and_inconclusive_runs_write_none(tmp_path: Path, fn, graded: Result) -> None:
    store, session = _env(tmp_path)
    _, verdict = _run(store, session, _case(), _judge(graded), fn)
    assert verdict.result is graded
    assert _bundles(store) == []


def test_a_grader_crash_after_a_completed_run_writes_none(tmp_path: Path) -> None:
    store, session = _env(tmp_path)
    judge = MockProvider(responses={"judge": []})  # nothing queued: grading raises
    _, verdict = run_and_grade_case_resilient(_case(), session, judge, "run_1", store)
    assert verdict.result is Result.INCONCLUSIVE
    assert _bundles(store) == []


# -- W2 --------------------------------------------------------------------------------------

def test_an_errored_bundle_names_the_step_that_raised_not_the_last_screenshot(
    tmp_path: Path,
) -> None:
    store, session = _env(tmp_path, broken=BASE + "two")
    _run(store, session, _case(), _judge(Result.PASS))
    manifest = load_bundle(_bundles(store)[0])
    assert manifest.failing_step == 2  # the heuristic (highest screenshot step) would say 1
    assert manifest.steps_included == [1, 2, 3]


def test_an_unmet_assertion_bundle_names_the_asserting_step(tmp_path: Path) -> None:
    store, session = _env(tmp_path, body="welcome")
    result, _ = _run(store, session, _case(expect_text="goodbye"), _judge(Result.FAIL))
    assert result.outcome is Outcome.ASSERTION_FAILED
    assert load_bundle(_bundles(store)[0]).failing_step == 2  # the heuristic would say 3


def test_recorded_failing_step_prefers_the_error_text_and_has_no_guess(tmp_path: Path) -> None:
    store, session = _env(tmp_path, broken=BASE + "two")
    result, _ = _run(store, session, _case(), _judge(Result.PASS))
    case = _case()
    assert recorded_failing_step(case, result) == 2
    named = result.model_copy(update={"error": "LocatorNotFound: step 3 (click): gone"})
    assert recorded_failing_step(case, named) == 3
    clean = result.model_copy(update={"outcome": Outcome.COMPLETED, "evidence": []})
    assert recorded_failing_step(case, clean) is None


# -- W3 --------------------------------------------------------------------------------------

def test_a_bundle_error_changes_no_verdict_and_is_logged_redacted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture,
) -> None:
    def boom(**_: object) -> Path:
        raise RuntimeError(f"disk exploded near {SECRET}")

    store, session = _env(tmp_path, broken=BASE + "two")
    control, control_verdict = _run(store, session, _case(), _judge(Result.PASS))
    store2, session2 = _env(tmp_path / "b", broken=BASE + "two")
    monkeypatch.setattr(fb, "build_failure_bundle", boom)
    with caplog.at_level(logging.WARNING, logger=fb.__name__):
        result, verdict = _run(store2, session2, _case(), _judge(Result.PASS))
    assert (result.outcome, verdict.result) == (control.outcome, control_verdict.result)
    assert verdict.scoreboard == control_verdict.scoreboard
    assert _bundles(store2) == []
    assert "disk exploded" in caplog.text and "[REDACTED]" in caplog.text
    assert SECRET not in caplog.text


# -- W4 --------------------------------------------------------------------------------------

def test_a_secret_in_the_case_or_error_never_reaches_a_pipeline_bundle(tmp_path: Path) -> None:
    store, session = _env(tmp_path, broken=BASE + "two", error=f"typed {SECRET} then timed out")
    _run(store, session, _case(note=f"fills {SECRET} into the field"), _judge(Result.PASS))
    files = [p for p in _bundles(store)[0].rglob("*") if p.is_file()]
    assert any(p.name == "case.json" for p in files)
    for path in files:
        assert SECRET.encode() not in path.read_bytes(), path.name
    assert b"[REDACTED]" in (_bundles(store)[0] / "case.json").read_bytes()


def test_an_unmasked_screenshot_in_the_window_means_no_bundle(
    tmp_path: Path, caplog: pytest.LogCaptureFixture,
) -> None:
    store, session = _env(tmp_path, broken=BASE + "two")
    real = session._record

    def unmasked(kind, path, **kw):  # type: ignore[no-untyped-def]
        ev = real(kind, path, **kw)
        ev.masked = False
        return ev

    session._record = unmasked  # type: ignore[method-assign]
    with caplog.at_level(logging.WARNING, logger=fb.__name__):
        result, _ = _run(store, session, _case(), _judge(Result.PASS))
    assert result.outcome is Outcome.ERRORED
    assert _bundles(store) == []
    assert "UnmaskedScreenshotError" in caplog.text
