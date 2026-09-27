"""Contract: qa/contracts/run-case-pipeline.md RP1-RP4."""

from __future__ import annotations

from pathlib import Path

from autotester.browser.secrets import SecretStore
from autotester.browser.session import BrowserSession
from autotester.core.paths import ProjectPaths
from autotester.providers.mock import MockProvider
from autotester.schema.case import Case
from autotester.schema.enums import Action, CaseClass, CaseKind, Outcome, Result
from autotester.schema.flowspec import Step
from autotester.schema.project import Project
from autotester.schema.run import RawResult
from autotester.schema.verdict import Judgment
from autotester.stages.run_case_pipeline import (
    default_rubric,
    grade_errored_result,
    run_and_grade_case,
)
from autotester.store.project_store import ProjectStore


class _FakePage:
    """Just enough of a Playwright page for execute.py::run_case's NAVIGATE step."""

    def __init__(self, url: str) -> None:
        self.url = url

    def add_style_tag(self, content: str) -> None:
        pass

    def screenshot(self, path: str, full_page: bool = False) -> None:
        Path(path).write_bytes(b"png")

    def goto(self, url: str, wait_until: str = "") -> None:
        self.url = url


def _project() -> Project:
    return Project(slug="demo", name="Demo", base_url="https://demo.test",
                    allowed_domains=["demo.test"])


def _case(rationale: str | None = "the page shows a welcome message") -> Case:
    return Case(project="demo", flow_id="flow-home", kind=CaseKind.BEST,
                case_class=CaseClass.HAPPY, title="Homepage loads", rationale=rationale,
                steps=[Step(order=1, action=Action.NAVIGATE, target="https://demo.test/")])


def _session(tmp_path: Path) -> BrowserSession:
    paths = ProjectPaths("demo", tmp_path)
    secrets = SecretStore.load(_project(), paths.env_file, strict=False)
    s = BrowserSession(_project(), secrets, tmp_path / "run", paths)
    s._page = _FakePage("https://demo.test/")
    s.state.run_dir.mkdir(parents=True, exist_ok=True)
    return s


def test_default_rubric_is_grounded_in_the_cases_own_rationale() -> None:
    rubric = default_rubric(_case(), "rub_x")
    assert "welcome message" in rubric.criteria[0].text
    assert rubric.criteria[0].id == "c1"


def test_default_rubric_falls_back_to_title_when_no_rationale() -> None:
    rubric = default_rubric(_case(rationale=None), "rub_x")
    assert "Homepage loads" in rubric.criteria[0].text


def test_run_and_grade_case_builds_and_persists_a_default_rubric_when_none_exists(
    tmp_path: Path,
) -> None:
    store = ProjectStore("demo", tmp_path)
    store.save_project(_project())
    case = _case()
    judge = MockProvider(responses={"judge": [
        Judgment(result=Result.PASS, criteria_met=1, criteria_total=1, scoreboard="1/1 met")
    ]})

    result, verdict = run_and_grade_case(case, _session(tmp_path), judge, "run_1", store)

    assert result.outcome is Outcome.COMPLETED
    assert verdict.result is Result.PASS
    persisted = store.load_rubric(f"rub_{case.id}")
    assert persisted is not None
    assert persisted.criteria[0].id == "c1"


def test_run_and_grade_case_passes_the_runs_real_screenshots_to_the_judge(
    tmp_path: Path,
) -> None:
    """AT-049: the judge must actually see the real screenshot files this
    run produced, not just their filenames -- run_and_grade_case is the one
    path a UI Run button or CLI script calls, so this is where the wiring
    has to be real, not just present in grade.py's own signature."""
    store = ProjectStore("demo", tmp_path)
    store.save_project(_project())
    case = _case()
    judge = MockProvider(responses={"judge": [
        Judgment(result=Result.PASS, criteria_met=1, criteria_total=1, scoreboard="1/1 met")
    ]})
    paths = ProjectPaths("demo", tmp_path)
    run_dir = paths.run_dir("run_1")
    secrets = SecretStore.load(_project(), paths.env_file, strict=False)
    session = BrowserSession(_project(), secrets, run_dir, paths)
    session._page = _FakePage("https://demo.test/")
    session.state.run_dir.mkdir(parents=True, exist_ok=True)

    run_and_grade_case(case, session, judge, "run_1", store)

    assert judge.judge_images == [[run_dir / "01-step01-navigate.png"]]
    assert (run_dir / "01-step01-navigate.png").exists()


def test_run_and_grade_case_reuses_an_existing_rubric_instead_of_overwriting_it(
    tmp_path: Path,
) -> None:
    store = ProjectStore("demo", tmp_path)
    store.save_project(_project())
    case = _case()
    hand_written = default_rubric(case, f"rub_{case.id}")
    hand_written.criteria[0].text = "a hand-tuned criterion, not the default"
    store.save_rubric(hand_written)
    judge = MockProvider(responses={"judge": [
        Judgment(result=Result.PASS, criteria_met=1, criteria_total=1, scoreboard="1/1 met")
    ]})

    run_and_grade_case(case, _session(tmp_path), judge, "run_1", store)

    reloaded = store.load_rubric(f"rub_{case.id}")
    assert reloaded is not None
    assert reloaded.criteria[0].text == "a hand-tuned criterion, not the default"


# -- AT-059: a stale auto-generated rubric must not grade forever -------------

def test_a_case_whose_rationale_changed_gets_a_regenerated_default_rubric(
    tmp_path: Path,
) -> None:
    """The bug, exactly: `Case.compute_id()` excludes `rationale`, so correcting
    a rationale keeps the SAME case id and therefore the same `rub_<case_id>`
    file — which used to mean the OLD claim graded forever. Observed live: a
    fixed case still FAILed against the stale claim on a screenshot that plainly
    showed what it asked for, and deleting the file by hand was the only cure."""
    store = ProjectStore("demo", tmp_path)
    store.save_project(_project())
    old = _case(rationale="added by hand from the UI")
    new = _case(rationale=None)
    assert old.id == new.id, "precondition: rationale is not part of the case id"
    store.save_rubric(default_rubric(old, f"rub_{old.id}"))
    judge = MockProvider(responses={"judge": [
        Judgment(result=Result.PASS, criteria_met=1, criteria_total=1, scoreboard="1/1 met")
    ]})

    run_and_grade_case(new, _session(tmp_path), judge, "run_1", store)

    reloaded = store.load_rubric(f"rub_{new.id}")
    assert reloaded is not None
    assert "added by hand from the UI" not in reloaded.criteria[0].text
    assert "Homepage loads" in reloaded.criteria[0].text


def test_an_unchanged_generated_rubric_is_left_alone(tmp_path: Path) -> None:
    """Regenerating on every run would churn the file and lose any future
    hand-edit window — only a genuinely stale claim triggers a rewrite."""
    store = ProjectStore("demo", tmp_path)
    store.save_project(_project())
    case = _case()
    original = default_rubric(case, f"rub_{case.id}")
    store.save_rubric(original)
    judge = MockProvider(responses={"judge": [
        Judgment(result=Result.PASS, criteria_met=1, criteria_total=1, scoreboard="1/1 met")
    ]})

    run_and_grade_case(case, _session(tmp_path), judge, "run_1", store)

    assert store.load_rubric(f"rub_{case.id}").criteria == original.criteria


def test_a_hand_edited_generated_rubric_survives_a_rationale_change(
    tmp_path: Path,
) -> None:
    """The dangerous edge: the rubric carries this generator's provenance, and
    the claim IS stale, but a human has since rewritten the criterion. A grading
    contract someone tuned by hand is never overwritten on a guess."""
    store = ProjectStore("demo", tmp_path)
    store.save_project(_project())
    old = _case(rationale="the original claim")
    tuned = default_rubric(old, f"rub_{old.id}")
    tuned.criteria[0].text = "a hand-tuned criterion, not the default"
    store.save_rubric(tuned)
    judge = MockProvider(responses={"judge": [
        Judgment(result=Result.PASS, criteria_met=1, criteria_total=1, scoreboard="1/1 met")
    ]})

    run_and_grade_case(_case(rationale="a completely different claim"),
                       _session(tmp_path), judge, "run_1", store)

    reloaded = store.load_rubric(f"rub_{old.id}")
    assert reloaded.criteria[0].text == "a hand-tuned criterion, not the default"


def test_a_rubric_with_no_provenance_is_treated_as_hand_authored(
    tmp_path: Path,
) -> None:
    """Rubrics written before this stamping existed carry no provenance and are
    indistinguishable from hand-written ones, so they keep their claim rather
    than being silently rewritten."""
    store = ProjectStore("demo", tmp_path)
    store.save_project(_project())
    old = _case(rationale="a legacy claim")
    legacy = default_rubric(old, f"rub_{old.id}")
    legacy.provenance = None
    store.save_rubric(legacy)
    judge = MockProvider(responses={"judge": [
        Judgment(result=Result.PASS, criteria_met=1, criteria_total=1, scoreboard="1/1 met")
    ]})

    run_and_grade_case(_case(rationale="a new claim"), _session(tmp_path), judge,
                       "run_1", store)

    assert "a legacy claim" in store.load_rubric(f"rub_{old.id}").criteria[0].text


# -- AT-568: grading a result that never reached run_and_grade_case -----------

def test_grade_errored_result_never_calls_the_judge(tmp_path: Path) -> None:
    """AT-568: `stages.parallel_run.run_cases` reports a `session_factory`
    crash (or any exception before a caller captured its own verdict) as its
    own ERRORED `RawResult`, with no `run_and_grade_case` call ever having
    happened for that case. `grade_errored_result` must still produce a
    coherent `Verdict` for it -- and must be safe to call unconditionally,
    because `grade()`'s own ERRORED short-circuit never reaches the judge.
    A `MockProvider` with NO queued "judge" response proves this: if
    `grade_errored_result` ever called `judge.judge(...)`, `MockProvider`
    would raise `ProviderError('no queued response')` instead of returning."""
    store = ProjectStore("demo", tmp_path)
    store.save_project(_project())
    case = _case()
    judge = MockProvider(responses={})  # would raise if .judge() were ever called
    crashed = RawResult(case_id=case.id, outcome=Outcome.ERRORED,
                        error="RuntimeError: boom starting the session")

    verdict = grade_errored_result(case, crashed, judge, "run_1", store)

    assert verdict.case_id == case.id
    assert verdict.result is Result.INCONCLUSIVE
    assert verdict.note == crashed.error
    assert verdict.grader_provider == "rule"
    assert judge.prompts == []  # never reached: no prompt was ever built for it


def test_grade_errored_result_builds_and_persists_the_same_default_rubric(
    tmp_path: Path,
) -> None:
    """It goes through the exact same rubric seam as a normal run (`_rubric_
    for`), so an ERRORED case is gradeable against its real rubric -- and a
    later real run of the same case reuses the rubric this call persisted,
    rather than building a second, divergent one."""
    store = ProjectStore("demo", tmp_path)
    store.save_project(_project())
    case = _case()
    judge = MockProvider(responses={})
    crashed = RawResult(case_id=case.id, outcome=Outcome.ERRORED, error="boom")

    grade_errored_result(case, crashed, judge, "run_1", store)

    persisted = store.load_rubric(f"rub_{case.id}")
    assert persisted is not None
    assert persisted.criteria[0].id == "c1"
