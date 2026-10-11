"""T-199a: the pure lifecycle (TB1-TB4). Contract: qa/contracts/team-bug-loop.md.

Every (state, event) cell is asserted against an independent hand-written expectation, so a changed
table entry cannot pass by being compared with itself.
"""

from __future__ import annotations

import ast
import itertools
from pathlib import Path

import pytest
from bug_loop_fixture import CASE, CRIT, KEY, PROJECT, T0, at, bug, event, seed
from pydantic import ValidationError

import autotester.stages.bug_loop as bug_loop
from autotester.schema.enums import Result
from autotester.schema.tracked_bug import (
    SYSTEM_ACTOR,
    BugEvent,
    BugSeed,
    BugStatus,
    EventKind,
    case_bug_key,
)
from autotester.schema.verdict import Failure, Verdict
from autotester.stages.bug_loop import (
    TABLE,
    Effect,
    Move,
    Refusal,
    fold,
    judge,
    kind_of_verdict,
)

K = EventKind
S = BugStatus
LIVE = (S.OPEN, S.REOPENED)
UNJUDGED = (K.PASS_UNEVIDENCED, K.INCONCLUSIVE, K.BLOCKED, K.NOT_RUN, K.NO_VERDICT)
NONE = None

# (effect, reason, status, count, first_min, last_min, streak) after an event at minute 20
# on a bug first seen at 0 / last seen at 10 / count 2 / (streak 1 when live).
EXPECT: dict[tuple[BugStatus | None, EventKind], tuple] = {}
for kind in UNJUDGED:
    EXPECT[(NONE, kind)] = (Effect.UNCHANGED, Move.UNCHANGED, NONE, 0, 0, 0, 0)
    for st in LIVE:
        EXPECT[(st, kind)] = (Effect.UNCHANGED, Move.UNCHANGED, st, 2, 0, 10, 1)
    EXPECT[(S.FIXED, kind)] = (Effect.UNCHANGED, Move.UNCHANGED, S.FIXED, 2, 0, 10, 0)
    EXPECT[(S.STALE, kind)] = (Effect.UNCHANGED, Move.UNCHANGED, S.STALE, 2, 0, 10, 0)
EXPECT[(NONE, K.FAIL)] = (Effect.APPLIED, Move.OPEN, S.OPEN, 1, 20, 20, 0)
EXPECT[(NONE, K.PASS)] = (Effect.REFUSED, Refusal.NO_BUG, NONE, 0, 0, 0, 0)
EXPECT[(NONE, K.CASE_CHANGED)] = (Effect.REFUSED, Refusal.NO_BUG, NONE, 0, 0, 0, 0)
EXPECT[(NONE, K.ASSIGN)] = (Effect.REFUSED, Refusal.NO_BUG, NONE, 0, 0, 0, 0)
for st in LIVE:
    EXPECT[(st, K.FAIL)] = (Effect.APPLIED, Move.REFAIL, st, 3, 0, 20, 0)
    EXPECT[(st, K.PASS)] = (Effect.APPLIED, Move.PASS_STEP, S.FIXED, 2, 0, 10, 0)
    EXPECT[(st, K.CASE_CHANGED)] = (Effect.APPLIED, Move.MARK_STALE, S.STALE, 2, 0, 10, 0)
    EXPECT[(st, K.ASSIGN)] = (Effect.APPLIED, Move.ASSIGN, st, 2, 0, 10, 1)
EXPECT[(S.FIXED, K.FAIL)] = (Effect.APPLIED, Move.REOPEN, S.REOPENED, 3, 0, 20, 0)
EXPECT[(S.FIXED, K.PASS)] = (Effect.UNCHANGED, Move.UNCHANGED, S.FIXED, 2, 0, 10, 0)
EXPECT[(S.FIXED, K.CASE_CHANGED)] = (Effect.REFUSED, Refusal.CLOSED_RECORD, S.FIXED, 2, 0, 10, 0)
EXPECT[(S.FIXED, K.ASSIGN)] = (Effect.APPLIED, Move.ASSIGN, S.FIXED, 2, 0, 10, 0)
EXPECT[(S.STALE, K.FAIL)] = (Effect.REFUSED, Refusal.STALE_BUG, S.STALE, 2, 0, 10, 0)
EXPECT[(S.STALE, K.PASS)] = (Effect.REFUSED, Refusal.STALE_BUG, S.STALE, 2, 0, 10, 0)
EXPECT[(S.STALE, K.CASE_CHANGED)] = (Effect.REFUSED, Refusal.ALREADY_STALE, S.STALE, 2, 0, 10, 0)
EXPECT[(S.STALE, K.ASSIGN)] = (Effect.APPLIED, Move.ASSIGN, S.STALE, 2, 0, 10, 0)

CELLS = list(itertools.product((NONE, *S), K))


def _start(state: BugStatus | None):
    return None if state is None else bug(state, streak=1 if state in LIVE else 0)


def _incoming(kind: EventKind):
    return event(kind, 20, key=KEY, minutes=20, assignee="Priya" if kind is K.ASSIGN else None)


def test_tb2_the_table_covers_the_full_cross_product() -> None:
    assert set(TABLE) == set(CELLS) and len(TABLE) == 5 * 9
    assert all(isinstance(rule, (Move, Refusal)) for rule in TABLE.values())
    assert set(EXPECT) == set(CELLS)


@pytest.mark.parametrize(("state", "kind"), CELLS, ids=lambda x: str(getattr(x, "value", x)))
def test_tb2_every_cell_of_the_table(state, kind) -> None:
    effect, reason, status, count, first, last, streak = EXPECT[(state, kind)]
    result = judge(_start(state), _incoming(kind), close_passes=2)
    assert (result.effect, result.reason) == (effect, reason)
    if status is None:
        assert result.bug is None
        return
    now = result.bug
    assert now is not None
    assert (now.status, now.count, now.first_seen, now.last_seen, now.pass_streak) == (
        status, count, at(first), at(last), streak)


def test_tb2_a_refusal_or_unchanged_cell_returns_the_bug_it_was_given() -> None:
    start = bug(S.STALE)
    assert judge(start, _incoming(K.FAIL), close_passes=2).bug == start
    assert judge(start, _incoming(K.INCONCLUSIVE), close_passes=2).bug == start


@pytest.mark.parametrize(("n", "expected"), [(1, S.FIXED), (2, S.FIXED), (3, S.OPEN)])
def test_tb2_n_consecutive_passes_close_the_bug_and_k_below_n_do_not(n, expected) -> None:
    events = [event(K.FAIL, 1), event(K.PASS, 10), event(K.PASS, 11)]
    assert fold(events, close_passes=n)[KEY].status is expected


def test_tb2_default_n_is_two_and_one_pass_leaves_it_open() -> None:
    assert bug_loop.DEFAULT_CLOSE_PASSES == 2
    one = fold([event(K.FAIL, 1), event(K.PASS, 2)])[KEY]
    two = fold([event(K.FAIL, 1), event(K.PASS, 2), event(K.PASS, 3)])[KEY]
    assert (one.status, one.pass_streak) == (S.OPEN, 1)
    assert two.status is S.FIXED


def test_tb2_a_fail_between_passes_breaks_the_run_but_an_unjudged_result_does_not() -> None:
    broken = fold([event(K.FAIL, 1), event(K.PASS, 2), event(K.FAIL, 3), event(K.PASS, 4)])[KEY]
    assert (broken.status, broken.pass_streak, broken.count) == (S.OPEN, 1, 2)
    kept = fold([event(K.FAIL, 1), event(K.PASS, 2), event(K.INCONCLUSIVE, 3),
                 event(K.BLOCKED, 4), event(K.NOT_RUN, 5), event(K.PASS, 6)])[KEY]
    assert kept.status is S.FIXED


def test_tb2_a_run_that_could_not_judge_neither_opens_nor_closes() -> None:
    for kind in UNJUDGED:
        assert fold([event(kind, 1)]) == {}
    still = fold([event(K.FAIL, 1), event(K.PASS, 2), event(K.PASS_UNEVIDENCED, 3)])[KEY]
    assert (still.status, still.pass_streak) == (S.OPEN, 1)


def test_tb2_first_and_last_seen_follow_the_failures_even_out_of_order() -> None:
    bugs = fold([event(K.FAIL, 1, minutes=30), event(K.FAIL, 2, minutes=5),
                 event(K.FAIL, 3, minutes=50), event(K.PASS, 4, minutes=99)])
    got = bugs[KEY]
    assert (got.first_seen, got.last_seen, got.count) == (at(5), at(50), 3)


def test_tb4_a_fixed_bug_lists_the_runs_and_verdicts_that_closed_it() -> None:
    got = fold([event(K.FAIL, 1), event(K.PASS, 2), event(K.PASS, 3)])[KEY]
    assert got.status is S.FIXED
    assert got.closed_by_runs == ["run2", "run3"]
    assert got.closed_by_verdicts == [f"run2/{CASE}", f"run3/{CASE}"]
    reopened = fold([event(K.FAIL, 1), event(K.PASS, 2), event(K.PASS, 3), event(K.FAIL, 4)])[KEY]
    assert (reopened.status, reopened.closed_by_runs, reopened.count) == (S.REOPENED, [], 2)


def test_tb4_a_changed_case_makes_an_open_bug_stale_and_it_can_never_become_fixed() -> None:
    events = [event(K.FAIL, 1), event(K.PASS, 2), event(K.CASE_CHANGED, 3, with_seed=False),
              event(K.PASS, 4), event(K.PASS, 5)]
    assert fold(events)[KEY].status is S.STALE


def test_tb4_a_closed_bug_is_not_swept_to_stale() -> None:
    events = [event(K.FAIL, 1), event(K.PASS, 2), event(K.PASS, 3), event(K.CASE_CHANGED, 4)]
    assert fold(events)[KEY].status is S.FIXED


def test_tb1_the_key_never_holds_a_run_a_time_or_a_secret() -> None:
    three = fold([event(K.FAIL, n, minutes=n * 7, run=f"run-{n}-{'x' * n}") for n in (1, 2, 3)])
    assert list(three) == [KEY] and three[KEY].count == 3
    other = case_bug_key(PROJECT, CASE, "C2")
    assert other != KEY
    secret = seed(title="password hunter2-SECRET in the case text")
    assert "hunter2" not in secret.bug_key and secret.bug_key == KEY


@pytest.mark.parametrize("bad", ["bug_deadbeef0000", "run_1234", "x"])
def test_tb1_a_seed_whose_key_is_not_its_parts_is_refused(bad) -> None:
    with pytest.raises(ValidationError):
        BugSeed(bug_key=bad, project=PROJECT, case_id=CASE, criterion_id=CRIT, title="t")


def test_tb1_a_video_key_must_be_the_issue_fingerprint_shape() -> None:
    BugSeed(bug_key="iss_0123456789ab", project=PROJECT, title="t")
    with pytest.raises(ValidationError):
        BugSeed(bug_key=KEY, project=PROJECT, title="t")


def test_the_id_is_stable_while_status_count_and_assignee_change() -> None:
    steps = [event(K.FAIL, 1), event(K.FAIL, 2), event(K.ASSIGN, 3, assignee="Priya"),
             event(K.PASS, 4), event(K.PASS, 5), event(K.FAIL, 6)]
    for i in range(1, len(steps) + 1):
        assert list(fold(steps[:i])) == [KEY]
    last = fold(steps)[KEY]
    assert (last.status, last.assignee, last.bug_key) == (S.REOPENED, "Priya", KEY)


@pytest.mark.parametrize("kind", list(K))
def test_only_the_bug_loop_may_move_a_status_and_only_a_user_may_assign(kind) -> None:
    ok = SYSTEM_ACTOR if kind is not K.ASSIGN else "user:umesh"
    wrong = "user:umesh" if kind is not K.ASSIGN else SYSTEM_ACTOR
    base = bug(S.OPEN, streak=1)
    who = "x" if kind is K.ASSIGN else None
    allowed = judge(base, event(kind, 9, actor=ok, with_seed=False, assignee=who), close_passes=2)
    assert allowed.reason is not Refusal.ACTOR_NOT_ALLOWED
    refused = judge(base, event(kind, 9, actor=wrong, with_seed=False,
                                assignee="x" if kind is K.ASSIGN else None), close_passes=2)
    assert (refused.effect, refused.reason) == (Effect.REFUSED, Refusal.ACTOR_NOT_ALLOWED)
    assert refused.bug == base


def test_a_first_fail_without_a_seed_is_refused_not_invented() -> None:
    result = judge(None, event(K.FAIL, 1, with_seed=False), close_passes=2)
    assert (result.effect, result.reason) == (Effect.REFUSED, Refusal.SEED_MISSING)


def test_an_event_already_seen_is_a_duplicate() -> None:
    first = event(K.FAIL, 1)
    again = event(K.FAIL, 1)
    dup = judge(None, again, close_passes=2, seen=frozenset({first.event_id}))
    assert dup.effect is Effect.DUPLICATE
    as_pass = event(K.PASS, 1, ref=first.ref)
    assert as_pass.event_id == first.event_id


@pytest.mark.parametrize("bad", [
    {"actor": ""}, {"actor": "x" * 81}, {"actor": "bad\nactor"}, {"actor": "-lead"},
    {"ref": ""}, {"ref": "a\x00b"}, {"kind": K.PASS, "run_id": None},
    {"kind": K.PASS, "seed": seed()}, {"assignee": "x"},
])
def test_an_event_with_an_invalid_field_is_refused_by_the_schema(bad) -> None:
    good = dict(bug_key=KEY, kind=K.FAIL, ref="r/1", at=T0, actor=SYSTEM_ACTOR, run_id="r")
    with pytest.raises(ValidationError):
        BugEvent(**{**good, **bad})
    with pytest.raises(ValidationError):
        BugEvent(**{**good, "at": T0.replace(tzinfo=None)})
    with pytest.raises(ValidationError):
        BugEvent(**{**good, "surprise": 1})


def _verdict(result: Result, *, met: int = 2, total: int = 2, seen: int = 0, asked: int = 0,
             failures: int = 0) -> Verdict:
    return Verdict(run_id="r1", case_id=CASE, result=result, criteria_met=met, criteria_total=total,
                   images_seen=seen, images_requested=asked,
                   failures=[Failure(criterion_id=CRIT, reason="x")] * failures)


@pytest.mark.parametrize(("verdict", "expected"), [
    (None, K.NO_VERDICT),
    (_verdict(Result.FAIL, met=1, failures=1), K.FAIL),
    (_verdict(Result.FAIL, met=1, failures=0), K.INCONCLUSIVE),
    (_verdict(Result.PASS), K.PASS),
    (_verdict(Result.PASS, met=1), K.PASS_UNEVIDENCED),
    (_verdict(Result.PASS, met=0, total=0), K.PASS_UNEVIDENCED),
    (_verdict(Result.PASS, seen=1, asked=2), K.PASS_UNEVIDENCED),
    (_verdict(Result.BLOCKED), K.BLOCKED),
    (_verdict(Result.INCONCLUSIVE), K.INCONCLUSIVE),
])
def test_tb3_a_verdict_maps_to_one_event_kind_none_changes_nothing(verdict, expected) -> None:
    assert kind_of_verdict(verdict) is expected


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            names |= {node.module or "", *(f"{node.module}.{a.name}" for a in node.names)}
        elif isinstance(node, ast.Import):
            names |= {a.name for a in node.names}
    return names


def test_tb3_the_loop_reads_verdicts_and_never_a_raw_result() -> None:
    root = Path(bug_loop.__file__).resolve().parents[1]
    for rel in ("stages/bug_loop.py", "schema/tracked_bug.py", "store/bug_store.py"):
        found = _imports(root / rel)
        raw = {n for n in found if n.endswith("RawResult") or n == "autotester.schema.run"}
        assert not raw, rel
    assert "autotester.store.project_store" not in _imports(root / "stages/bug_loop.py")


def test_a_later_fail_without_a_run_id_keeps_the_evidence_run() -> None:
    named = event(K.FAIL, 1)
    bare = event(K.FAIL, 2).model_copy(update={"run_id": None})
    got = fold([named, bare])[KEY]
    assert (got.count, got.evidence_run_id) == (2, "run1")


def test_assign_sets_the_assignee_in_every_status() -> None:
    for state in S:
        result = judge(bug(state), _incoming(K.ASSIGN), close_passes=2)
        assert result.bug.assignee == "Priya" and result.bug.status is state
