"""The judge's structured `defect_observed` decides a PASS; the clause-scoped note guard backs it.

Misfire phrases are the real PathLynks run's (T-169): 7 of 8 judge PASSes were held by the old
3-word negation lookback although the judge said there was no defect.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from autotester.providers.mock import MockProvider
from autotester.schema.enums import EvidenceKind, Outcome, Result
from autotester.schema.run import Evidence, RawResult
from autotester.schema.verdict import Criterion, Judgment, Rubric
from autotester.stages.grade import grade
from autotester.stages.grade_note_guard import failure_terms

RECORDED = json.loads((Path(__file__).parent / "fixtures" / "t181_recorded_judge_output.json")
                      .read_text(encoding="utf-8"))

MISFIRES = [
    "The page is not evidence of a product defect.",
    "This is not evidence of a product defect or missing element.",
    "No error, rejection, wrong result, or missing element is evidenced.",
    "The flow ended as intended rather than a product failure.",
    "No error or rejection is evidenced after submission.",
    "No evidence of a failure after submission.",
]
# negated by the guard's clause rule; the "errors appeared" sentence is the accepted held case
GUARD_CLEAN = MISFIRES


REAL_NOTES = json.loads((Path(__file__).parent / "fixtures" / "t169_real_judge_notes.json")
                        .read_text(encoding="utf-8"))
# 7a978722a38c says "validation errors appeared" on a negative case: the accepted held case.
ACCEPTED_HELD = {"case_7a978722a38c"}
MUST_HOLD = [
    "no spinner and an error message is shown",
    "The login showed no spinner and an error message is shown",
    "No data was saved and the error banner is displayed",
    "There is no confirmation, error message shown",
    "No redirect happened and an error is shown",
    "The page did not load and the form is broken",
    "No error, but the page crashed",
    "No crash, error shown",
    "no error, broken layout",
    "no errors, wrong value",
    "no error, 500",
    "no issues, crash on submit",
    "no problems, unable to submit",
    "Not blocked, missing field",
    "no error, unexpected redirect",
    "no error, invalid total shown",
]


@pytest.mark.parametrize("case", sorted(set(REAL_NOTES) - ACCEPTED_HELD))
def test_verbatim_real_notes_are_not_held(case: str) -> None:
    assert failure_terms(REAL_NOTES[case]) == [], case
    assert _grade(_j(REAL_NOTES[case])).result is Result.PASS


def test_accepted_negative_case_note_is_still_held() -> None:
    assert failure_terms(REAL_NOTES["case_7a978722a38c"])


@pytest.mark.parametrize("note", MUST_HOLD)
def test_negator_does_not_hide_a_later_defect(note: str) -> None:
    assert failure_terms(note), note
    assert _grade(_j(note)).result is Result.INCONCLUSIVE


def _grade(judgment: Judgment):
    rubric = Rubric(id="rub_t", criteria=[Criterion(id="c1", text="x")])
    raw = RawResult(case_id="case_t", outcome=Outcome.COMPLETED, evidence=[
        Evidence(kind=EvidenceKind.DOM, path="url http://127.0.0.1/x.html", step_order=1)])
    return grade(rubric, raw, "run_1", MockProvider(responses={"judge": [judgment]}))


def _j(note: str | None, **kw) -> Judgment:
    return Judgment(result=Result.PASS, scoreboard="Criteria 1/1 met.", criteria_met=1,
                    criteria_total=1, note=note, **kw)


@pytest.mark.parametrize("note", MISFIRES)
def test_defect_observed_false_keeps_a_misfire_note_pass(note: str) -> None:
    assert _grade(_j(note, defect_observed=False)).result is Result.PASS


@pytest.mark.parametrize("note", [*MUST_HOLD, REAL_NOTES["case_7a978722a38c"]])
def test_defect_observed_false_never_overrides_a_defect_note(note: str) -> None:
    assert _grade(_j(note, defect_observed=False)).result is Result.INCONCLUSIVE


@pytest.mark.parametrize("note", GUARD_CLEAN)
def test_clause_scoped_guard_no_longer_misfires(note: str) -> None:
    assert failure_terms(note) == [], note
    assert _grade(_j(note)).result is Result.PASS  # field absent: the backstop alone


def test_defect_observed_true_with_pass_is_inconclusive() -> None:
    verdict = _grade(_j("Looks fine.", defect_observed=True, defect_summary="login rejected"))
    assert verdict.result is Result.INCONCLUSIVE
    assert "login rejected" in (verdict.note or "")


def test_non_boolean_field_fails_closed_at_parse() -> None:
    with pytest.raises(ValidationError):
        _j("ok", defect_observed="maybe")
    assert _j("ok", defect_observed="false").defect_observed is False
    assert _j("ok", defect_observed="Yes").defect_observed is True


def test_field_false_does_not_override_inconclusive() -> None:
    verdict = _grade(Judgment(result=Result.INCONCLUSIVE, scoreboard="x", criteria_met=0,
                              criteria_total=1, defect_observed=False, note="thin evidence"))
    assert verdict.result is Result.INCONCLUSIVE


@pytest.mark.parametrize("row", [r for r in RECORDED if r["case"] == "login"],
                         ids=lambda r: r["path"])
def test_recorded_broken_login_still_caught_without_the_field(row: dict) -> None:
    assert _grade(_j(row["note"])).result is Result.INCONCLUSIVE


@pytest.mark.parametrize("note", [
    "the page did not load and the form is broken", "Login was not possible; access was blocked.",
    "No errors elsewhere, but the login failed.", "login did not succeed",
])
def test_negator_does_not_leak_across_a_defect(note: str) -> None:
    assert failure_terms(note), note
