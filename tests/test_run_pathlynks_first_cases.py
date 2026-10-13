"""T-050 runner script. Contract: qa/contracts/pathlynks-first-run.md F1-F5.

Pure-logic tests only (case shape, rubric shape, run ordering) -- no live
browser, no live provider call. See qa/manifests/t050-*.md for the real run's
evidence, captured by actually executing this script against Pathlynks.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import run_pathlynks_first_cases as runner_mod

from autotester.core.redact import PLACEHOLDER_RE
from autotester.schema.enums import CaseClass, CaseKind

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
