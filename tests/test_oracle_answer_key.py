"""T-215 (multi-role-platform.md MP24, MPI2, MPI6): answer-key scoring.

A synthetic quiz product scores itself from the answers it was given; the key is derived from its
(synthetic) documentation. All-correct answers must show the documented 7/10; a product that shows
anything else is a finding. A key that cannot show a documentation source is refused.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from autotester.schema.answer_key import AnswerKey, AnswerKeySource, AnswerSourceKind
from autotester.schema.cross_role_assertion import CrossRoleAssertion, Observation
from autotester.schema.multi_role_enums import FindingClass, OracleName
from autotester.schema.oracle_context import OracleContext, OracleState
from autotester.schema.role_step import RoleStep
from autotester.stages.oracle_answer_key import KEYS_FILE, check_key, parse_score, run
from autotester.stages.oracle_registry import run_oracles

POINTS = {"q1": 3, "q2": 2, "q3": 1, "q4": 1}   # sums to 7; the quiz is out of 10
SOURCE = {"kind": "product_doc", "ref": "docs/product/quiz-scoring.md",
          "title": "How scoring works"}


def make_key(**over) -> AnswerKey:
    items = [{"id": k, "answer_action": f"select #{k} B", "points": v} for k, v in POINTS.items()]
    data = {"id": "quiz1", "platform_id": "portal", "role_id": "student",
            "url_template": "/quiz/{id}", "source": SOURCE, "open_action": "goto /quiz/{id}",
            "items": items, "submit_action": "click #submit", "score_selector": "#score",
            "documented_score": 7, "max_score": 10}
    return AnswerKey(**{**data, **over})


class QuizPort:
    """The quiz: remembers what was selected and shows a score. `show` overrides the display."""

    def __init__(self, *, show=None, ignore_weights=False, hide=False) -> None:
        self.selected: list[str] = []
        self.performed: list[tuple[str, str]] = []
        self.show, self.ignore_weights, self.hide = show, ignore_weights, hide

    def perform(self, step: RoleStep) -> None:
        self.performed.append((step.role_id, step.action))
        if step.action.startswith("select "):
            self.selected.append(step.action.split("#")[1].split()[0])

    def observe(self, assertion: CrossRoleAssertion) -> Observation:
        if self.hide:
            return Observation(matched=False)
        if self.show is not None:
            return Observation(matched=True, detail=self.show)
        key = make_key()
        right = {i.id for i in key.items if i.is_correct}
        got = sum(1 if self.ignore_weights else POINTS[q] for q in self.selected if q in right)
        return Observation(matched=True, detail=f"Your score: {got}/10")


def test_mp24_all_correct_answers_yield_the_documented_score_so_no_finding():
    port = QuizPort()
    assert check_key(make_key(), port) == []
    assert make_key().expected_score() == 7 and make_key().documented_score == 7


def test_answers_are_given_as_the_key_role_in_order_then_submitted():
    port = QuizPort()
    check_key(make_key(), port)
    assert port.performed[0] == ("student", "goto /quiz/{id}")
    assert [a for _, a in port.performed[1:5]] == [f"select #{k} B" for k in POINTS]
    assert port.performed[-1] == ("student", "click #submit")


def test_mp24_a_product_showing_the_wrong_score_is_an_answer_mismatch():
    found = check_key(make_key(), QuizPort(ignore_weights=True))   # 4/10 instead of 7/10
    assert len(found) == 1
    f = found[0]
    assert f.finding_class is FindingClass.ANSWER_MISMATCH and f.oracle is OracleName.ANSWER_KEY
    assert "7/10" in f.title and "4/10" in f.title and f.count == 3
    assert f.steps[0] == "login student" and f.role == "student"


@pytest.mark.parametrize("shown", ["Your score: 6/10", "8/10", "7/9", "7 of 12", "no score today"])
def test_each_off_by_one_display_is_a_mismatch(shown):
    assert len(check_key(make_key(), QuizPort(show=shown))) == 1


@pytest.mark.parametrize("shown", ["7/10", "Score 7 / 10", "7 of 10", "7"])
def test_equivalent_displays_of_the_documented_score_pass(shown):
    assert check_key(make_key(), QuizPort(show=shown)) == []


def test_a_score_that_is_not_shown_is_a_mismatch_not_a_pass():
    found = check_key(make_key(), QuizPort(hide=True))
    assert len(found) == 1 and "no readable score" in found[0].title and found[0].count == 1


def test_a_deliberately_wrong_answer_lowers_the_expected_score():
    items = [{"id": "q1", "answer_action": "select #q1 B", "points": 3},
             {"id": "q2", "answer_action": "select #q2 A", "points": 4, "is_correct": False}]
    key = make_key(items=items, documented_score=7)
    assert key.expected_score() == 3
    assert check_key(key, QuizPort(show="3/10")) == []
    assert len(check_key(key, QuizPort(show="7/10"))) == 1


@pytest.mark.parametrize("ref", [
    "CEO benchmark finding 12", "AT-731", ".work/ceo-list.md", "known_bugs corpus",
    "bug_events/2026", "acceptance comparison row", "atomic finding 4",
])
def test_mp24_a_key_citing_a_benchmark_finding_is_refused(ref):
    with pytest.raises(ValidationError):
        make_key(source={**SOURCE, "ref": ref})
    with pytest.raises(ValidationError):
        make_key(source={**SOURCE, "title": ref})


def test_a_key_with_no_source_is_refused():
    data = make_key().model_dump(mode="json")
    del data["source"]
    with pytest.raises(ValidationError):
        AnswerKey(**data)
    with pytest.raises(ValidationError):
        AnswerKeySource(kind=AnswerSourceKind.PRODUCT_DOC, ref="", title="x")


def test_product_docs_sources_are_accepted():
    assert make_key().source.ref == "docs/product/quiz-scoring.md"


@pytest.mark.parametrize("bad", [
    {"documented_score": 6}, {"documented_score": 7, "max_score": 5}, {"items": []},
    {"submit_action": "teleport #x"}, {"url_template": "/quiz/12345"}, {"extra": 1},
])
def test_a_key_that_disagrees_with_itself_is_refused(bad):
    with pytest.raises((ValidationError, ValueError, TypeError)):
        make_key(**bad)


def test_duplicate_item_ids_are_refused():
    item = {"id": "q1", "answer_action": "select #q1 B", "points": 7}
    with pytest.raises(ValidationError):
        make_key(items=[item, item])


@pytest.mark.parametrize(("text", "parsed"), [
    ("7/10", (7, 10)), ("Score: 7 out of 10", (7, 10)), ("7", (7, None)), ("none", None),
])
def test_parse_score(text, parsed):
    assert parse_score(text) == parsed


def _write_keys(run_dir: Path, *keys: dict) -> None:
    path = run_dir / KEYS_FILE
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(list(keys)), "utf-8")


def _context(run_dir: Path, port) -> OracleContext:
    return OracleContext(project_slug="demo", run_dir=str(run_dir), scenario_id="s1",
                         role_ids=["student"], platform_ids=["portal"], port=port)


def test_run_reads_the_keys_file(tmp_path):
    _write_keys(tmp_path, make_key().model_dump(mode="json"))
    assert run(_context(tmp_path, QuizPort())) == []
    assert len(run(_context(tmp_path, QuizPort(show="4/10")))) == 1


def test_run_with_no_keys_declared_finds_nothing(tmp_path):
    assert run(_context(tmp_path, None)) == []


def test_a_key_file_that_cites_a_finding_makes_the_oracle_errored_not_clean(tmp_path):
    bad = make_key().model_dump(mode="json")
    bad["source"]["ref"] = "benchmark finding 3"
    _write_keys(tmp_path, bad)
    summary, found = run_oracles(_context(tmp_path, QuizPort()), [OracleName.ANSWER_KEY])
    row = next(s for s in summary.statuses if s.oracle is OracleName.ANSWER_KEY)
    assert row.state is OracleState.ERRORED and found == []


def test_through_the_registry_a_mismatch_is_counted(tmp_path):
    _write_keys(tmp_path, make_key().model_dump(mode="json"))
    summary, found = run_oracles(_context(tmp_path, QuizPort(show="6/10")), [OracleName.ANSWER_KEY])
    row = next(s for s in summary.statuses if s.oracle is OracleName.ANSWER_KEY)
    assert (row.state, row.finding_count, len(found)) == (OracleState.RAN, 1, 1)
