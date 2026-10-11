"""BUG LOOP: a tracked bug's lifecycle as one table and a fold over events (T-199a, TB1-TB4, TB6).

Contract: qa/contracts/team-bug-loop.md. Pure: no file, no provider, no network.

`TABLE` has one entry for every (state, event) pair, 5 x 9, and each is either a `Move` the loop
makes or a named `Refusal`, so no cell is decided by accident. `judge` applies one event to one bug;
`fold` replays a whole log through `judge`, and is the single interpreter: the store holds only
events, and a bug is whatever `fold` says (so history cannot be rewritten and a racing writer's
event is simply applied in file order, or skipped as a duplicate).

The loop reads `Verdict` and never a `RawResult` (TB3, R46): `kind_of_verdict` is the only door
from a grade to an event, and a result that could not judge changes nothing. Statuses are
machine-owned (R44): only the reserved `SYSTEM_ACTOR` may make a status event; only a named user
may `assign`. Whether that user may (`project.edit`) is T-204's check, not this module's.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from enum import StrEnum

from autotester.schema.enums import Result
from autotester.schema.tracked_bug import (
    DEFAULT_CLOSE_PASSES,
    SYSTEM_ACTOR,
    BugEvent,
    BugStatus,
    EventKind,
    TrackedBug,
)
from autotester.schema.verdict import Verdict

K = EventKind
S = BugStatus


class Move(StrEnum):
    OPEN = "open"
    REFAIL = "refail"
    REOPEN = "reopen"
    PASS_STEP = "pass_step"
    MARK_STALE = "mark_stale"
    ASSIGN = "assign"
    UNCHANGED = "unchanged"


class Refusal(StrEnum):
    NO_BUG = "no_bug"
    STALE_BUG = "stale_bug"
    CLOSED_RECORD = "closed_record"
    ALREADY_STALE = "already_stale"
    ACTOR_NOT_ALLOWED = "actor_not_allowed"
    SEED_MISSING = "seed_missing"
    KEY_MISMATCH = "key_mismatch"


class Effect(StrEnum):
    APPLIED = "applied"
    UNCHANGED = "unchanged"
    DUPLICATE = "duplicate"
    REFUSED = "refused"


Rule = Move | Refusal
_UNJUDGED = (K.PASS_UNEVIDENCED, K.INCONCLUSIVE, K.BLOCKED, K.NOT_RUN, K.NO_VERDICT)


def _row(fail: Rule, pass_: Rule, case_changed: Rule, assign: Rule) -> dict[EventKind, Rule]:
    """One state's nine cells. A result that could not judge is `unchanged` in every state (TB2)."""
    return {K.FAIL: fail, K.PASS: pass_, K.CASE_CHANGED: case_changed, K.ASSIGN: assign,
            **dict.fromkeys(_UNJUDGED, Move.UNCHANGED)}


_LIVE = _row(Move.REFAIL, Move.PASS_STEP, Move.MARK_STALE, Move.ASSIGN)
TABLE: dict[tuple[BugStatus | None, EventKind], Rule] = {
    (state, kind): rule
    for state, row in {
        None: _row(Move.OPEN, Refusal.NO_BUG, Refusal.NO_BUG, Refusal.NO_BUG),
        S.OPEN: _LIVE,
        S.REOPENED: _LIVE,
        S.FIXED: _row(Move.REOPEN, Move.UNCHANGED, Refusal.CLOSED_RECORD, Move.ASSIGN),
        S.STALE: _row(Refusal.STALE_BUG, Refusal.STALE_BUG, Refusal.ALREADY_STALE, Move.ASSIGN),
    }.items()
    for kind, rule in row.items()
}
"""The lifecycle. Traced cell by cell to the contract in qa/briefs/t199a-bug-loop-core.md."""


@dataclass(frozen=True)
class Applied:
    """What `judge` decided. `bug` is the new bug when APPLIED, else the bug it was given."""

    effect: Effect
    reason: Move | Refusal | None
    bug: TrackedBug | None


def kind_of_verdict(verdict: Verdict | None) -> EventKind:
    """The one door from a grade to an event. A PASS counts toward closing only when it cites
    evidence: every criterion met and no screenshot the judge was owed missing (TB3). A FAIL that
    names no criterion cannot be filed under a bug, so it is `inconclusive`, never a guess."""
    if verdict is None:
        return K.NO_VERDICT
    if verdict.result is Result.FAIL:
        return K.FAIL if verdict.is_actionable_failure else K.INCONCLUSIVE
    if verdict.result is Result.PASS:
        proven = (verdict.criteria_total > 0 and verdict.criteria_met == verdict.criteria_total
                  and not verdict.graded_on_partial_evidence)
        return K.PASS if proven else K.PASS_UNEVIDENCED
    return K.BLOCKED if verdict.result is Result.BLOCKED else K.INCONCLUSIVE


def _failed(bug: TrackedBug, ev: BugEvent, update: dict) -> TrackedBug:
    latest = ev.at >= bug.last_seen
    return bug.model_copy(update={
        "count": bug.count + 1, "first_seen": min(bug.first_seen, ev.at),
        "last_seen": max(bug.last_seen, ev.at), "pass_streak": 0, "streak_runs": [],
        "streak_refs": [], "evidence_run_id": ev.run_id if latest else bug.evidence_run_id,
        **update})


def _pass_step(bug: TrackedBug, ev: BugEvent, n: int) -> TrackedBug:
    runs, refs = [*bug.streak_runs, str(ev.run_id)], [*bug.streak_refs, ev.ref]
    if len(refs) < n:
        return bug.model_copy(update={"pass_streak": len(refs), "streak_runs": runs,
                                      "streak_refs": refs})
    return bug.model_copy(update={"status": S.FIXED, "pass_streak": 0, "streak_runs": [],
                                  "streak_refs": [], "closed_by_runs": runs,
                                  "closed_by_verdicts": refs})


def _open(ev: BugEvent) -> TrackedBug:
    seed = ev.seed
    assert seed is not None
    return TrackedBug(
        bug_key=seed.bug_key, project=seed.project, case_id=seed.case_id,
        criterion_id=seed.criterion_id, criterion_fp=seed.criterion_fp, title=seed.title,
        screen=seed.screen, severity=seed.severity, first_seen=ev.at, last_seen=ev.at,
        evidence_run_id=ev.run_id)


def _mover(move: Move) -> Callable[[TrackedBug, BugEvent, int], TrackedBug]:
    return {
        Move.REFAIL: lambda b, e, n: _failed(b, e, {}),
        Move.REOPEN: lambda b, e, n: _failed(b, e, {
            "status": S.REOPENED, "closed_by_runs": [], "closed_by_verdicts": []}),
        Move.PASS_STEP: lambda b, e, n: _pass_step(b, e, n),
        Move.MARK_STALE: lambda b, e, n: b.model_copy(update={
            "status": S.STALE, "pass_streak": 0, "streak_runs": [], "streak_refs": []}),
        Move.ASSIGN: lambda b, e, n: b.model_copy(update={"assignee": e.assignee}),
    }[move]


def _actor_allowed(ev: BugEvent) -> bool:
    machine = ev.actor.startswith("system:")
    return (not machine) if ev.kind is K.ASSIGN else ev.actor == SYSTEM_ACTOR


def judge(bug: TrackedBug | None, event: BugEvent, *, close_passes: int = DEFAULT_CLOSE_PASSES,
          seen: frozenset[str] | set[str] = frozenset()) -> Applied:
    """Apply one event to one bug. Pure; never raises for a legal-shaped event."""
    if bug is not None and bug.bug_key != event.bug_key:
        return Applied(Effect.REFUSED, Refusal.KEY_MISMATCH, bug)
    if event.event_id in seen:
        return Applied(Effect.DUPLICATE, None, bug)
    if not _actor_allowed(event):
        return Applied(Effect.REFUSED, Refusal.ACTOR_NOT_ALLOWED, bug)
    rule = TABLE[(bug.status if bug else None, event.kind)]
    if isinstance(rule, Refusal):
        return Applied(Effect.REFUSED, rule, bug)
    if rule is Move.UNCHANGED:
        return Applied(Effect.UNCHANGED, rule, bug)
    if rule is Move.OPEN:
        if event.seed is None:
            return Applied(Effect.REFUSED, Refusal.SEED_MISSING, bug)
        return Applied(Effect.APPLIED, rule, _open(event))
    assert bug is not None
    return Applied(Effect.APPLIED, rule, _mover(rule)(bug, event, close_passes))


def fold(events: Iterable[BugEvent], *, close_passes: int = DEFAULT_CLOSE_PASSES,
         ) -> dict[str, TrackedBug]:
    """Replay a log in order. The only way a `TrackedBug` comes to exist outside `judge`."""
    bugs: dict[str, TrackedBug] = {}
    seen: set[str] = set()
    for event in events:
        result = judge(bugs.get(event.bug_key), event, close_passes=close_passes, seen=seen)
        if result.effect is Effect.APPLIED and result.bug is not None:
            bugs[event.bug_key] = result.bug
            seen.add(event.event_id)
    return bugs
