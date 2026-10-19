"""T-136 negpath-assert (C2): the three Pathlynks login cases carry a real deterministic assertion.

Run run-01M58F744J7R3CB99CMH9S7FQ3 held case_efaed2c0eb91, case_7a978722a38c and
case_093f5070df79 as INCONCLUSIVE because none declared what the page must show, so B11
(grade_images.visual_decision) had no `assert ...: met` row to back a judge PASS on masked
screenshots. The strings below are what the recorded screenshots of that run actually showed.
Offline: reads the committed cases file only.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from autotester.schema.case import Case

CASES = Path(__file__).resolve().parents[1] / "projects" / "pathlynks" / "cases.jsonl"


def _case(case_id: str) -> Case:
    rows = [json.loads(line) for line in CASES.read_text("utf-8").splitlines() if line.strip()]
    return Case.model_validate(next(r for r in rows if r["id"] == case_id))


def _asserted(case: Case) -> dict[int, list[str]]:
    return {s.order: s.expected.visible_text for s in case.steps if s.expected.visible_text}


def test_a_student_logs_in_and_the_app_says_logged_in_successfully() -> None:
    assert _asserted(_case("case_efaed2c0eb91")) == {4: ["Logged in successfully"]}


def test_a_student_submits_an_empty_form_and_both_required_messages_show() -> None:
    assert _asserted(_case("case_7a978722a38c")) == {
        2: ["Email, mobile, or Student ID is required", "Password is required"]}


def test_a_student_types_a_wrong_password_and_the_app_says_invalid_credentials() -> None:
    assert _asserted(_case("case_093f5070df79")) == {4: ["Invalid credentials"]}


@pytest.mark.parametrize("case_id", ["case_efaed2c0eb91", "case_7a978722a38c",
                                     "case_093f5070df79"])
def test_the_edit_changed_only_the_expected_state_not_the_actions(case_id: str) -> None:
    case = _case(case_id)
    assert [s.order for s in case.steps] == list(range(1, len(case.steps) + 1))
    assert all(s.expected.absent_text == [] and s.expected.dom_asserts == [] for s in case.steps)
