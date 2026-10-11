"""BUG RUN: turn one finished run's verdicts into bug events, and notice cases that moved (T-199b).

Its one job is the bridge from a run directory to the bug store (TB3, TB4, TB6). It reads
`Verdict` files and never a `RawResult`: `bug_loop.kind_of_verdict` is the only door from a grade to
an event kind, and this module only decides which bugs the kind is about. A FAIL verdict opens or
repeats one bug per failing criterion; every other verdict is an event of the kind the door gave,
for each bug of that case (the store keeps only the ones that can move a bug).

A bug whose case was deleted, or whose criterion was edited or removed, gets a `case_changed` event
and becomes `stale`, never `fixed` (TB4). A rubric that cannot be loaded is reported, not guessed.

Idempotent per run (TB6): every event's time is the run's own (`finished_at`, else when `run.json`
was saved), and its ref is `<run>/<case>` or `case/<case>/...`, so the same run produces the same
event ids and the store counts each once. A run exists once `run.json` does; the executor writes it
after the last case. The bug store is read once per call (P3).
"""

from __future__ import annotations

from datetime import datetime

from autotester.schema.bug_run import RunOutcome, RunReport
from autotester.schema.case import Case
from autotester.schema.tracked_bug import (
    LIVE_STATUSES,
    SYSTEM_ACTOR,
    BugEvent,
    BugSeed,
    EventKind,
    TrackedBug,
    case_bug_key,
)
from autotester.schema.verdict import Rubric, Verdict
from autotester.stages.bug_loop import Effect, kind_of_verdict
from autotester.store.bug_store import BugStore
from autotester.store.project_store import ProjectStore

K = EventKind


class _Rubrics:
    """Rubrics by id, loaded once per run; `None` is a rubric that could not be loaded."""

    def __init__(self, store: ProjectStore) -> None:
        self._store = store
        self._seen: dict[str, Rubric | None] = {}

    def of(self, case: Case | None) -> Rubric | None:
        if case is None or not case.rubric_ref:
            return None
        if case.rubric_ref not in self._seen:
            try:
                self._seen[case.rubric_ref] = self._store.load_rubric(case.rubric_ref)
            except ValueError:  # a corrupt rubric file is "cannot compare", never a crash
                self._seen[case.rubric_ref] = None
        return self._seen[case.rubric_ref]


def _seed(project: str, case: Case, criterion_id: str, rubric: Rubric | None) -> BugSeed | None:
    """The bug a failing criterion opens, or None when the case or the criterion cannot be
    resolved (a bug that would be stale on the next look is never opened: TB6)."""
    crit = next((c for c in rubric.criteria if c.id == criterion_id), None) if rubric else None
    if rubric is not None and crit is None:
        return None
    title = f"{case.title}: {crit.text}" if crit else f"{case.title}: criterion {criterion_id}"
    screen = next((s.screen_id for s in case.steps if s.screen_id), None)
    return BugSeed(bug_key=case_bug_key(project, case.id, criterion_id), project=project,
                   case_id=case.id, criterion_id=criterion_id,
                   criterion_fp=crit.fingerprint if crit else "", title=title[:200],
                   screen=screen, severity=case.severity)


def _event(bug_key: str, kind: EventKind, ref: str, at: datetime, run_id: str,
           seed: BugSeed | None = None) -> BugEvent:
    return BugEvent(bug_key=bug_key, kind=kind, ref=ref, at=at, actor=SYSTEM_ACTOR, run_id=run_id,
                    seed=seed)


def verdict_events(verdict: Verdict, run_id: str, at: datetime, project: str, case: Case | None,
                   rubric: Rubric | None, bugs: dict[str, TrackedBug],
                   ) -> tuple[list[BugEvent], list[str]]:
    """The events one verdict makes, and the failures it named that cannot be filed under a bug
    (case gone, or criterion not in its rubric). The kind is the door's; this only picks bugs."""
    kind, ref = kind_of_verdict(verdict), f"{run_id}/{verdict.case_id}"
    if kind is not K.FAIL:
        return [_event(b.bug_key, kind, ref, at, run_id)
                for b in bugs.values() if b.case_id == verdict.case_id], []
    events: list[BugEvent] = []
    unresolved: list[str] = []
    for crit in dict.fromkeys(f.criterion_id for f in verdict.failures):
        seed = _seed(project, case, crit, rubric) if case else None
        if seed is None:
            unresolved.append(f"{verdict.case_id}/{crit}")
        else:
            events.append(_event(seed.bug_key, kind, ref, at, run_id, seed))
    return events, unresolved


def changed_case_events(store: ProjectStore, rubrics: _Rubrics, bugs: dict[str, TrackedBug],
                        run_id: str, at: datetime) -> tuple[list[BugEvent], list[str]]:
    """A `case_changed` event for each live bug whose case is gone or whose criterion moved, and
    the keys of live bugs whose rubric could not be loaded to compare (never guessed)."""
    cases = {c.id: c for c in store.list_cases()}
    events: list[BugEvent] = []
    unverifiable: list[str] = []
    for bug in bugs.values():
        if bug.status not in LIVE_STATUSES or bug.case_id is None:
            continue
        if not cases:  # no case list at all (wrong root, missing file) is not "every case deleted"
            unverifiable.append(bug.bug_key)
            continue
        case = cases.get(bug.case_id)
        why = "deleted" if case is None else None
        if case is not None:
            rubric = rubrics.of(case)
            if rubric is None:
                unverifiable.append(bug.bug_key)
                continue
            crit = next((c for c in rubric.criteria if c.id == bug.criterion_id), None)
            if crit is None:
                why = f"{bug.criterion_id}/removed"
            elif bug.criterion_fp and crit.fingerprint != bug.criterion_fp:
                why = f"{bug.criterion_id}/{crit.fingerprint}"
        if why is not None:
            events.append(_event(bug.bug_key, K.CASE_CHANGED, f"case/{bug.case_id}/{why}", at,
                                 run_id))
    return events, unverifiable


def process_run(store: ProjectStore, bugs: BugStore, run_id: str) -> RunReport:
    """Apply one finished run to the bug store. Safe to call again for the same run (TB6)."""
    run = store.load_run(run_id)
    if run is None:
        return RunReport(run_id=run_id, outcome=RunOutcome.NOT_FINISHED)
    if run.project != store.paths.slug:
        return RunReport(run_id=run_id, outcome=RunOutcome.WRONG_PROJECT)
    at, snap = run.finished_at or run.created_at, bugs.snapshot()
    verdicts, rubrics = store.load_verdicts(run_id), _Rubrics(store)
    cases = {c.id: c for c in store.list_cases()}
    events: list[BugEvent] = []
    unresolved: list[str] = []
    for v in verdicts:
        case = cases.get(v.case_id)
        made, lost = verdict_events(v, run_id, at, run.project, case, rubrics.of(case), snap.bugs)
        events += made
        unresolved += lost
    changed, unverifiable = changed_case_events(store, rubrics, snap.bugs, run_id, at)
    results = bugs.apply_all([*events, *changed], snapshot=snap)
    judged = {v.case_id for v in verdicts}
    return RunReport(
        run_id=run_id, outcome=RunOutcome.PROCESSED, verdicts=len(verdicts),
        events_built=len(events) + len(changed),
        applied=sum(r.effect is Effect.APPLIED for r in results),
        duplicate=sum(r.effect is Effect.DUPLICATE for r in results),
        refused=[f"{e.bug_key}: {r.reason}" for e, r in zip([*events, *changed], results,
                                                             strict=True)
                 if r.effect is Effect.REFUSED],
        unjudged_cases=[v.case_id for v in verdicts if kind_of_verdict(v) not in (K.FAIL, K.PASS)],
        no_verdict_cases=[c for c in run.case_ids if c not in judged],
        case_changed=[e.bug_key for e in changed], unverifiable=unverifiable,
        unresolved_failures=unresolved,
        bad_files=snap.bad)

