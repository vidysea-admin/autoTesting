"""T-136 grade-fix G3: the C12 note guard consults the case's expected outcome.

A negative-path case (worst/edge, `Rubric.expects_error`) whose judge says "correctly rejected" /
"appropriately blocked" / "rejected ... as expected" with defect_observed=false is a PASS; the
same wording on a positive-path case is still held (core-invariants C12, fail closed). Notes are
the real run-01M582T0GEWYH561PHSV8JANPX judge notes. Offline.
"""

from __future__ import annotations

import pytest

from autotester.providers.mock import MockProvider
from autotester.schema.enums import EvidenceKind, Outcome, Result
from autotester.schema.run import Evidence, RawResult
from autotester.schema.verdict import Criterion, Judgment, Rubric
from autotester.stages.grade import grade
from autotester.stages.grade_note_guard import failure_terms

LIVE_NOTES = [
    "The validation appropriately blocked the empty submission attempt.",
    "The attempt to login with invalid credentials was correctly rejected by the application.",
    "The product correctly rejected the login attempt with an incorrect password, displaying an "
    "error notification as expected.",
]


def _grade(note: str, *, expects_error: bool, defect_observed: bool | None = False):
    rubric = Rubric(id="rub_t", criteria=[Criterion(id="c1", text="x")],
                    expects_error=expects_error)
    raw = RawResult(case_id="case_t", outcome=Outcome.COMPLETED, evidence=[
        Evidence(kind=EvidenceKind.DOM, path="url http://127.0.0.1/x.html", step_order=1)])
    judged = Judgment(result=Result.PASS, scoreboard="1/1", criteria_met=1, criteria_total=1,
                      note=note, defect_observed=defect_observed)
    return grade(rubric, raw, "run_1", MockProvider(responses={"judge": [judged]}))


@pytest.mark.parametrize("note", LIVE_NOTES)
def test_g3_negative_path_rejection_note_passes(note: str) -> None:
    assert _grade(note, expects_error=True).result is Result.PASS


@pytest.mark.parametrize("note", LIVE_NOTES)
def test_g3_same_note_on_a_positive_path_case_is_held(note: str) -> None:
    assert _grade(note, expects_error=False).result is Result.INCONCLUSIVE
    assert failure_terms(note), note


@pytest.mark.parametrize("note", LIVE_NOTES)
def test_g3_without_the_structured_field_nothing_is_exempt(note: str) -> None:
    assert _grade(note, expects_error=True, defect_observed=None).result is Result.INCONCLUSIVE


@pytest.mark.parametrize("note", [
    "The login was correctly rejected, but the password field leaked.",
    "Correctly rejected the empty form, then the page crashed.",
    "Appropriately blocked the attempt; server returned 500.",
    "The wrong amount was correctly rejected.",
    "The invalid total was correctly rejected.",
    "Correctly rejected the valid card.",
    "The attempt was not correctly rejected.",
    "The empty form was correctly blocked and the record was saved anyway.",
    "Properly rejected, however the app froze.",
    "Login succeeded and the wrong password was accepted.",
])
def test_g3_contrary_or_unexpected_outcomes_are_still_held(note: str) -> None:
    assert _grade(note, expects_error=True).result is Result.INCONCLUSIVE, note


@pytest.mark.parametrize("note", [
    "invalid total shown correctly formatted",
    "denied access properly but data leaked",
    "Invalid total shown as expected.",
    "Error message shown.",
])
def test_g3_earlier_checker_false_pass_phrases_stay_held(note: str) -> None:
    assert _grade(note, expects_error=True).result is Result.INCONCLUSIVE, note
