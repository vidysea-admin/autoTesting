"""AT-996: a judge PASS whose own note describes a failure is never a PASS (fail closed, C12).

Uses the judge output recorded live in T-181 (qa/evidence/t181-live, reasons only, no keys): the
default rubric graded a seeded broken login PASS on both paths while the notes described the bug.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from autotester.providers.mock import MockProvider
from autotester.schema.enums import EvidenceKind, Outcome, Result
from autotester.schema.run import Evidence, RawResult
from autotester.schema.verdict import Criterion, Judgment, Rubric
from autotester.stages.grade import grade
from autotester.stages.grade_note_guard import failure_terms, note_guard

RECORDED = json.loads((Path(__file__).parent / "fixtures" / "t181_recorded_judge_output.json")
                      .read_text(encoding="utf-8"))


def _judge(row: dict) -> MockProvider:
    return MockProvider(responses={"judge": [Judgment(
        result=Result(row["result"]), scoreboard=row["scoreboard"],
        criteria_met=row["criteria_met"], criteria_total=row["criteria_total"],
        note=row["note"])]})


def _grade(row: dict):
    rubric = Rubric(id="rub_t", criteria=[Criterion(id="c1", text="x")])
    raw = RawResult(case_id="case_t", outcome=Outcome.COMPLETED, evidence=[
        Evidence(kind=EvidenceKind.DOM, path="url http://127.0.0.1/login.html", step_order=1)])
    return grade(rubric, raw, "run_1", _judge(row))


@pytest.mark.parametrize("row", [r for r in RECORDED if r["case"] == "login"],
                         ids=lambda r: r["path"])
def test_recorded_login_pass_with_a_bug_note_is_not_pass(row: dict) -> None:
    assert row["result"] == "PASS", "the fixture is the recorded wrong PASS"
    verdict = _grade(row)
    assert verdict.result is Result.INCONCLUSIVE
    assert "disagree" in (verdict.note or "") and row["note"] in (verdict.note or "")


@pytest.mark.parametrize("row", [r for r in RECORDED if r["case"] == "home"],
                         ids=lambda r: r["path"])
def test_recorded_clean_home_notes_still_pass(row: dict) -> None:
    assert _grade(row).result is Result.PASS


@pytest.mark.parametrize("note", [None, "", "The homepage loaded and the heading is visible.",
                                  "No errors were shown; the dashboard rendered.",
                                  "Login succeeded without any error message."])
def test_clean_or_negated_notes_do_not_trip_the_guard(note: str | None) -> None:
    assert failure_terms(note) == []
    assert note_guard(Result.PASS, note) == (Result.PASS, note)


@pytest.mark.parametrize("note", ["Reproduced the bug: invalid credentials error shown.",
                                  "Page loaded but the password field is missing.",
                                  "The login failed with a wrong-password message."])
def test_a_failure_note_downgrades_pass_but_not_fail_or_inconclusive(note: str) -> None:
    assert note_guard(Result.PASS, note)[0] is Result.INCONCLUSIVE
    assert note_guard(Result.FAIL, note) == (Result.FAIL, note)
    assert note_guard(Result.INCONCLUSIVE, note) == (Result.INCONCLUSIVE, note)
