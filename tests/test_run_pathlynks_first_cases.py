"""T-050 runner script. Contract: qa/contracts/pathlynks-first-run.md F1-F5.

Pure-logic tests only (case shape, rubric shape, run ordering) -- no live
browser, no live provider call. See qa/manifests/t050-*.md for the real run's
evidence, captured by actually executing this script against Pathlynks.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import run_pathlynks_first_cases as runner_mod

from autotester.core.redact import PLACEHOLDER_RE
from autotester.schema.enums import CaseClass, CaseKind, Outcome, Result
from autotester.schema.project import Project
from autotester.schema.run import RawResult
from autotester.schema.verdict import Verdict

BASE_URL = "https://pathlynks.vidysea.com/signin"


def test_build_cases_returns_one_per_kind() -> None:
    cases = runner_mod.build_cases("pathlynks", BASE_URL)
    kinds = {c.kind for c in cases}
    assert kinds == {CaseKind.BEST, CaseKind.WORST, CaseKind.EDGE}
    by_kind = {c.kind: c for c in cases}
    assert by_kind[CaseKind.BEST].case_class is CaseClass.HAPPY
    assert by_kind[CaseKind.WORST].case_class is CaseClass.AUTH_WRONG_CREDS
    assert by_kind[CaseKind.EDGE].case_class is CaseClass.INPUT_EMPTY


def test_no_case_step_carries_a_raw_secret_literal() -> None:
    cases = runner_mod.build_cases("pathlynks", BASE_URL)
    for case in cases:
        for step in case.steps:
            if step.value and "SECRET" in (step.value or ""):
                assert PLACEHOLDER_RE.search(step.value), (
                    f"{case.kind}: step {step.order} references a secret without a placeholder"
                )


def test_wrong_password_is_a_literal_not_a_placeholder() -> None:
    """The WORST case's password is deliberately wrong and not a real credential --
    it must NOT go through the {{SECRET:KEY}} mechanism (there is no such key)."""
    cases = runner_mod.build_cases("pathlynks", BASE_URL)
    worst = next(c for c in cases if c.kind == "worst")
    password_step = next(s for s in worst.steps if s.target == runner_mod.SIGNIN_PASSWORD)
    assert password_step.value == runner_mod.WRONG_PASSWORD
    assert not PLACEHOLDER_RE.search(password_step.value)


def test_navigate_steps_use_the_real_base_url_not_a_template_marker() -> None:
    cases = runner_mod.build_cases("pathlynks", BASE_URL)
    for case in cases:
        navigate = case.steps[0]
        assert navigate.target == BASE_URL


def test_make_rubric_links_case_id() -> None:
    case = runner_mod.build_cases("pathlynks", BASE_URL)[0]
    rubric = runner_mod.make_rubric(case)
    assert rubric.case_id == case.id
    assert len(rubric.criteria) == 1


def test_best_case_always_runs_last() -> None:
    """WORST/EDGE must run while genuinely logged out; BEST logs in and leaves the
    persistent profile authenticated for the rest of the process (found running
    this for real -- see the manifest)."""
    cases = runner_mod.build_cases("pathlynks", BASE_URL)
    ordered = sorted(cases, key=lambda c: 0 if c.kind != "best" else 1)
    assert ordered[-1].kind == "best"
    assert {c.kind for c in ordered[:-1]} == {"worst", "edge"}


def test_script_main_records_wall_clock_and_prints_run_id() -> None:
    src = (Path(__file__).resolve().parents[1] / "scripts"
           / "run_pathlynks_first_cases.py").read_text(encoding="utf-8")
    assert "record_run(" in src and "run_id_lines(" in src
    assert "Run(id=" not in src  # no un-timestamped Run construction left


class _FakeSession:
    """Enough of a BrowserSession for `main()`: the page has already left the sign-in page."""

    def __init__(self, project, secrets, run_dir, paths) -> None:
        self.project, self.secrets = project, secrets
        self.state = SimpleNamespace(evidence=[])
        self.page = SimpleNamespace(url="https://pathlynks.vidysea.com/dashboard",
                                    wait_for_timeout=lambda ms: None)

    def start(self):
        return self

    def close(self) -> None:
        pass

    def goto(self, url: str) -> None:
        pass

    def screenshot(self, label: str) -> None:
        pass

    def _record(self, *args, **kwargs) -> None:
        pass


def _stub_main_collaborators(monkeypatch, tmp_path: Path, project: Project) -> None:
    store = SimpleNamespace(load_project=lambda: project, add_case=lambda case: case,
                            save_result=lambda *a: None, save_verdict=lambda *a: None)
    paths = SimpleNamespace(env_file=tmp_path / ".env", run_dir=lambda run_id: tmp_path / run_id,
                            profile_dir=tmp_path / "profile")
    secrets = SimpleNamespace(redactor=lambda: SimpleNamespace(scrub=lambda text: text))
    monkeypatch.setattr(sys, "argv", ["run_pathlynks_first_cases.py"])
    monkeypatch.setattr(runner_mod, "load_dotenv", lambda *a, **k: None)
    monkeypatch.setattr(runner_mod, "ProjectStore", lambda slug: store)
    monkeypatch.setattr(runner_mod, "ProjectPaths", lambda slug: paths)
    monkeypatch.setattr(runner_mod.SecretStore, "load", lambda project, env_file: secrets)
    monkeypatch.setattr(runner_mod, "BrowserSession", _FakeSession)
    monkeypatch.setattr(runner_mod, "LangChainFallbackProvider",
                        lambda: SimpleNamespace(available=lambda: True))
    monkeypatch.setattr(runner_mod, "run_case", lambda case, session: RawResult(
        case_id=case.id, outcome=Outcome.COMPLETED))
    monkeypatch.setattr(runner_mod, "record_run", lambda *a, **k: None)


def test_pathlynks_first_run_script_grades_the_dashboard_with_the_project_limit(
        tmp_path: Path, monkeypatch) -> None:
    """AT-1384 F2: docs/ARCHITECTURE.md names this script as the Pathlynks first-run path. A
    `grade()` call here without the project's `image_mask_limit` judges the dashboard at the
    stricter default, withholds it, and the case reads INCONCLUSIVE. Every case must be graded
    with the project's own 0.85."""
    project = Project(slug="pathlynks", name="Pathlynks", base_url=BASE_URL,
                      allowed_domains=["vidysea.com"], headed=False, image_mask_limit=0.85)
    _stub_main_collaborators(monkeypatch, tmp_path, project)
    seen: list = []

    def fake_grade(rubric, result, run_id, judge, *args, **kwargs):
        seen.append(kwargs.get("mask_limit", "dropped"))
        return Verdict(run_id=run_id, case_id=result.case_id, result=Result.PASS,
                       grader_provider="mask-limit-probe")

    monkeypatch.setattr(runner_mod, "grade", fake_grade)
    runner_mod.main()
    assert seen == [0.85, 0.85, 0.85]
