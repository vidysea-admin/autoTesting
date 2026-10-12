"""Shared builders for the bug-loop tests: seeds, events and bugs in a given state."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from autotester.schema.enums import Severity
from autotester.schema.tracked_bug import (
    SYSTEM_ACTOR,
    BugEvent,
    BugSeed,
    BugStatus,
    EventKind,
    TrackedBug,
    case_bug_key,
)

T0 = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)
PROJECT = "demo"
CASE = "case_aaaaaaaaaaaa"
CRIT = "C1"
KEY = case_bug_key(PROJECT, CASE, CRIT)


def at(minutes: int) -> datetime:
    return T0 + timedelta(minutes=minutes)


def seed(case: str = CASE, crit: str = CRIT, title: str = "Checkout button does nothing",
         ) -> BugSeed:
    return BugSeed(bug_key=case_bug_key(PROJECT, case, crit), project=PROJECT, case_id=case,
                   criterion_id=crit, criterion_fp="fp1", title=title, screen="Checkout")


def event(kind: EventKind, n: int = 1, *, key: str = KEY, minutes: int | None = None,
          actor: str | None = None, with_seed: bool | None = None, ref: str | None = None,
          run: str | None = None, assignee: str | None = None,
          seed_obj: BugSeed | None = None) -> BugEvent:
    """Event number `n` (own ref and run id) of kind `kind`. A FAIL carries a seed by default."""
    wants_seed = (kind is EventKind.FAIL) if with_seed is None else with_seed
    if seed_obj is not None:
        key, wants_seed = seed_obj.bug_key, True
    return BugEvent(
        bug_key=key, kind=kind, ref=ref or f"run{n}/{CASE}",
        at=at(n if minutes is None else minutes),
        actor=actor or ("user:umesh" if kind is EventKind.ASSIGN else SYSTEM_ACTOR),
        run_id=run or f"run{n}", seed=(seed_obj or seed()) if wants_seed else None,
        assignee=assignee)


def bug(status: BugStatus, *, count: int = 2, streak: int = 0) -> TrackedBug:
    """A bug already in `status`: first seen at T0, last seen at T0+10min."""
    return TrackedBug(
        bug_key=KEY, project=PROJECT, case_id=CASE, criterion_id=CRIT, criterion_fp="fp1",
        title="Checkout button does nothing", screen="Checkout", severity=Severity.S2,
        status=status, count=count, first_seen=at(0), last_seen=at(10), evidence_run_id="run0",
        pass_streak=streak, streak_runs=[f"s{i}" for i in range(streak)],
        streak_refs=[f"s{i}/{CASE}" for i in range(streak)],
        closed_by_runs=["c1", "c2"] if status is BugStatus.FIXED else [],
        closed_by_verdicts=[f"c1/{CASE}", f"c2/{CASE}"] if status is BugStatus.FIXED else [])
