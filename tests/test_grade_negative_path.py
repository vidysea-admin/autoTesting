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


# ---- T-136 negpath-assert (C1): the live run-01M58F744J7R3CB99CMH9S7FQ3 a5ea57c0961a hold ----

from autotester.schema.case import Case  # noqa: E402
from autotester.schema.enums import CaseClass, CaseKind  # noqa: E402
from autotester.schema.flowspec import ExpectedState, Step  # noqa: E402
from autotester.stages.run_case_pipeline import rubric_for_case  # noqa: E402

LIVE_A5EA_NOTE = ("Account with wrong password was correctly rejected with an invalid "
                  "credentials assertion.")
MET = "assert visible_text: met (expected to contain 'Invalid credentials')"


class _Store:
    """Just the two rubric calls `rubric_for_case` makes."""

    def __init__(self, rubric: Rubric | None) -> None:
        self.rubric, self.saved = rubric, None

    def load_rubric(self, rubric_id: str) -> Rubric | None:
        return self.rubric

    def save_rubric(self, rubric: Rubric) -> None:
        self.saved = rubric


def _wrong_password_case(kind: CaseKind = CaseKind.WORST) -> Case:
    step = Step(order=1, action="click", target="button",
                expected=ExpectedState(visible_text=["Invalid credentials"]))
    return Case(project="p", flow_id="flow_login", kind=kind, case_class=CaseClass.AUTH_WRONG_CREDS,
                title="Login with correct email, wrong password",
                rationale="a real account with a deliberately wrong password must be rejected",
                steps=[step])


def _grade_backed(note: str, *, expects_error: bool, evidence_row: str | None,
                  defect_observed: bool | None):
    rubric = Rubric(id="rub_t", criteria=[Criterion(id="c1", text="x")],
                    expects_error=expects_error)
    rows = [Evidence(kind=EvidenceKind.DOM, path="url http://127.0.0.1/x.html", step_order=1)]
    if evidence_row:
        rows.append(Evidence(kind=EvidenceKind.DOM, path=evidence_row, step_order=4))
    raw = RawResult(case_id="case_t", outcome=Outcome.COMPLETED, evidence=rows)
    judged = Judgment(result=Result.PASS, scoreboard="1/1", criteria_met=1, criteria_total=1,
                      note=note, defect_observed=defect_observed)
    return grade(rubric, raw, "run_1", MockProvider(responses={"judge": [judged]}))


def test_a_rubric_saved_before_expects_error_existed_still_gets_the_case_expectation() -> None:
    """A student types a wrong password; the app says 'Invalid credentials'. The rubric file on
    disk predates `expects_error`, so it loads as False; the case itself says rejection is the
    correct outcome, so the grader must be told (root cause of the a5ea hold)."""
    stored = Rubric(id="rub_case_x", criteria=[Criterion(id="c1", text="x")])
    assert stored.expects_error is False
    assert rubric_for_case(_wrong_password_case(), _Store(stored)).expects_error is True


def test_a_positive_path_case_never_gains_expects_error() -> None:
    stored = Rubric(id="rub_case_x", criteria=[Criterion(id="c1", text="x")])
    case = _wrong_password_case(CaseKind.BEST)
    assert rubric_for_case(case, _Store(stored)).expects_error is False


def test_wrong_password_rejected_with_met_assertion_passes_even_without_defect_field() -> None:
    """The judge omitted `defect_observed`, but the page assertion 'Invalid credentials' was met
    on a worst-path case: the rejection is the expected result, so PASS stands."""
    verdict = _grade_backed(LIVE_A5EA_NOTE, expects_error=True, evidence_row=MET,
                            defect_observed=None)
    assert verdict.result is Result.PASS


def test_without_a_met_assertion_the_missing_defect_field_still_holds_the_pass() -> None:
    verdict = _grade_backed(LIVE_A5EA_NOTE, expects_error=True, evidence_row=None,
                            defect_observed=None)
    assert verdict.result is Result.INCONCLUSIVE


def test_a_positive_path_login_whose_note_says_rejected_is_still_downgraded() -> None:
    """A student logs in with the right password and the judge's note says it was rejected: a
    positive-path case, so even a met assertion and a missing defect field cannot save it."""
    verdict = _grade_backed("The login was rejected with an invalid credentials error.",
                            expects_error=False, evidence_row="assert visible_text: met (x)",
                            defect_observed=None)
    assert verdict.result is Result.INCONCLUSIVE


def test_negative_path_note_with_a_contrary_marker_is_still_held_despite_met_assertion() -> None:
    verdict = _grade_backed("The wrong password was correctly rejected, but the page crashed.",
                            expects_error=True, evidence_row=MET, defect_observed=None)
    assert verdict.result is Result.INCONCLUSIVE
