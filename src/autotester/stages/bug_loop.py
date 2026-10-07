"""BUG LOOP: move tracked bugs by graded verdicts, and nothing else (T-199a, TB2-TB4, TB6).

Contract: qa/contracts/team-bug-loop.md. Pure over artifacts on disk -- no provider, no network.

It reads `Verdict` files and never a `RawResult` (TB3, R46): a run the judge did not finish
changes nothing, and a replayed run (D-072) counts like any other because it carries a judge
verdict. Statuses are machine-owned: only `process_run` moves one (R44).

Assumption flagged for the checker: a `Verdict` has no evidence field on a PASS, so "a PASS
cites evidence" is read as every rubric criterion met and no screenshot the judge was owed
missing (`Verdict.graded_on_partial_evidence`). D-074 (a failed assertion never PASSes) is the
judge's rule; the loop trusts the verdict and does not re-open the raw result to second-guess it.

Idempotent per run (TB6): every verdict ref a bug has counted is kept on the bug, so a
re-processed run, or one that crashed between two bugs, changes nothing it already counted. The
processed-run marker is only the fast path and is written last.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from enum import StrEnum

from autotester.core.ids import content_hash
from autotester.schema.enums import Result, Severity
from autotester.schema.issue import Issue
from autotester.schema.tracked_bug import (
    DEFAULT_CLOSE_PASSES,
    BugStatus,
    ProcessedRun,
    TrackedBug,
    case_bug_key,
    verdict_ref,
)
from autotester.schema.verdict import Verdict
from autotester.stages.issues import bug_from_issue
from autotester.store.filestore import read_jsonl, upsert_jsonl, write_json
from autotester.store.project_store import ProjectStore

CLOSE_PASSES_DEFAULT = DEFAULT_CLOSE_PASSES
Resolver = Callable[[str, str], str | None]
"""`(case_id, criterion_id) -> fingerprint`, or None when the case or criterion is gone."""


class BugSignal(StrEnum):
    """What one verdict says about one bug. Everything that is not a judged FAIL or an
    evidenced PASS (INCONCLUSIVE, BLOCKED, no verdict, an unevidenced PASS) is NONE."""

    FAIL = "fail"
    PASS = "pass"
    NONE = "none"


class Move(StrEnum):
    OPEN = "open"
    REFAIL = "refail"
    REOPEN = "reopen"
    RESTART = "restart"
    PASS_STEP = "pass_step"
    NOOP = "noop"


def _table() -> dict[tuple[BugStatus | None, BugSignal], Move]:
    table = {(s, g): Move.NOOP for s in (None, *BugStatus) for g in BugSignal}
    table[(None, BugSignal.FAIL)] = Move.OPEN
    table[(BugStatus.OPEN, BugSignal.FAIL)] = Move.REFAIL
    table[(BugStatus.REOPENED, BugSignal.FAIL)] = Move.REFAIL
    table[(BugStatus.FIXED, BugSignal.FAIL)] = Move.REOPEN
    table[(BugStatus.STALE, BugSignal.FAIL)] = Move.RESTART  # a new failure of a changed check
    table[(BugStatus.OPEN, BugSignal.PASS)] = Move.PASS_STEP
    table[(BugStatus.REOPENED, BugSignal.PASS)] = Move.PASS_STEP
    return table


TRANSITIONS = _table()
"""The TB2 lifecycle: every (state, signal) cell is present, so none is decided by accident."""


def signal_of(verdict: Verdict) -> BugSignal:
    if verdict.result is Result.FAIL and verdict.is_actionable_failure:
        return BugSignal.FAIL
    if (verdict.result is Result.PASS and verdict.criteria_total > 0
            and verdict.criteria_met == verdict.criteria_total
            and not verdict.graded_on_partial_evidence):
        return BugSignal.PASS
    return BugSignal.NONE


def step(
    bug: TrackedBug | None, signal: BugSignal, *, project: str, case_id: str, criterion_id: str,
    fp: str, title: str, at: datetime, run_id: str, ref: str, close_passes: int,
    severity: Severity = Severity.S2,
) -> TrackedBug | None:
    """One cell of the table. Returns the new bug (None if there is still none)."""
    move = TRANSITIONS[(bug.status if bug else None, signal)]
    if move is Move.NOOP:
        return bug
    if move is Move.OPEN:
        return TrackedBug(
            bug_key=case_bug_key(project, case_id, criterion_id), project=project,
            case_id=case_id, criterion_id=criterion_id, criterion_fp=fp, title=title,
            severity=severity, first_seen=at, last_seen=at, evidence_run_id=run_id,
            applied=[ref])
    assert bug is not None
    applied = [*bug.applied, ref]
    if move is Move.PASS_STEP:
        runs, refs = [*bug.streak_runs, run_id], [*bug.streak_verdicts, ref]
        if len(refs) < close_passes:
            return bug.model_copy(update={"pass_streak": len(refs), "streak_runs": runs,
                                          "streak_verdicts": refs, "applied": applied})
        return bug.model_copy(update={
            "status": BugStatus.FIXED, "pass_streak": 0, "streak_runs": [],
            "streak_verdicts": [], "closed_by_runs": runs, "closed_by_verdicts": refs,
            "applied": applied})
    seen = {"last_seen": at, "evidence_run_id": run_id, "applied": applied, "pass_streak": 0,
            "streak_runs": [], "streak_verdicts": []}
    if move is Move.RESTART:
        return bug.model_copy(update={**seen, "status": BugStatus.OPEN, "count": 1,
                                      "first_seen": at, "criterion_fp": fp, "title": title,
                                      "closed_by_runs": [], "closed_by_verdicts": []})
    status = BugStatus.REOPENED if move is Move.REOPEN else bug.status
    extra = {"criterion_fp": fp, "closed_by_runs": [], "closed_by_verdicts": []} \
        if move is Move.REOPEN else {}
    return bug.model_copy(update={**seen, **extra, "status": status, "count": bug.count + 1})


# -- persistence (module-level: ProjectStore is at the 300-line cap) ----------------------------

def load_bugs(store: ProjectStore) -> list[TrackedBug]:
    return read_jsonl(store.paths.bugs, TrackedBug)


def _save(store: ProjectStore, bug: TrackedBug) -> None:
    upsert_jsonl(store.paths.bugs, bug, TrackedBug, key="bug_key")


def store_resolver(store: ProjectStore) -> Resolver:
    """Fingerprint a criterion from the case's persisted rubric, as `run_case_pipeline`
    resolves it (`rubric_ref or rub_<case id>`). A snapshot per call: build one per run."""
    cases = {c.id: c for c in store.list_cases()}

    def resolve(case_id: str, criterion_id: str) -> str | None:
        case = cases.get(case_id)
        rubric = store.load_rubric(case.rubric_ref or f"rub_{case.id}") if case else None
        criterion = next((c for c in rubric.criteria if c.id == criterion_id), None) \
            if rubric else None
        return content_hash(criterion.model_dump(mode="json")) if criterion else None

    return resolve


def adopt_issue(store: ProjectStore, issue: Issue) -> TrackedBug:
    """Track a video-found issue as an open bug; adopting it again changes nothing."""
    existing = next((b for b in load_bugs(store) if b.bug_key == issue.id), None)
    if existing is not None:
        return existing
    bug = bug_from_issue(issue)
    _save(store, bug)
    return bug


def _close_passes(store: ProjectStore) -> int:
    project = store.load_project()
    return project.bug_close_passes if project else CLOSE_PASSES_DEFAULT


def _mark_stale(store: ProjectStore, bugs: dict[str, TrackedBug], resolve: Resolver) -> None:
    """TB4: an open bug whose case was deleted or whose criterion changed can no longer be
    honestly confirmed or closed. `fixed` bugs keep their honest record."""
    for bug in list(bugs.values()):
        live = bug.status in (BugStatus.OPEN, BugStatus.REOPENED) and bug.case_id
        if live and resolve(bug.case_id or "", bug.criterion_id or "") != bug.criterion_fp:
            bugs[bug.bug_key] = bug.model_copy(update={
                "status": BugStatus.STALE, "pass_streak": 0, "streak_runs": [],
                "streak_verdicts": []})
            _save(store, bugs[bug.bug_key])


def _apply(store: ProjectStore, bugs: dict[str, TrackedBug], v: Verdict, resolve: Resolver,
           close_passes: int, titles: dict[str, tuple[str, Severity]]) -> None:
    signal, ref = signal_of(v), verdict_ref(v.run_id, v.case_id)
    if signal is BugSignal.NONE:
        return
    name, severity = titles.get(v.case_id, (v.case_id, Severity.S2))
    if signal is BugSignal.FAIL:
        targets = {f.criterion_id: f.reason for f in v.failures}
    else:  # a PASS speaks for every criterion of the case
        targets = {b.criterion_id or "": "" for b in bugs.values() if b.case_id == v.case_id}
    for criterion_id in sorted(targets):
        old = bugs.get(case_bug_key(store.paths.slug, v.case_id, criterion_id))
        if old is not None and ref in old.applied:
            continue
        new = step(old, signal, project=store.paths.slug, case_id=v.case_id,
                   criterion_id=criterion_id, fp=resolve(v.case_id, criterion_id) or "",
                   title=f"{name} - {criterion_id}: {targets[criterion_id]}"[:200],
                   at=v.created_at, run_id=v.run_id, ref=ref, close_passes=close_passes,
                   severity=severity)
        if new is not None and new is not old:
            bugs[new.bug_key] = new
            _save(store, new)


def process_run(store: ProjectStore, run_id: str, *, resolve: Resolver | None = None,
                close_passes: int | None = None) -> list[TrackedBug]:
    """Apply one run's graded verdicts to the project's bugs. Safe to call twice (TB6)."""
    marker = store.paths.bug_run_marker(run_id)
    if marker.exists():
        return load_bugs(store)
    resolve = resolve or store_resolver(store)
    n = close_passes or _close_passes(store)
    bugs = {b.bug_key: b for b in load_bugs(store)}
    titles = {c.id: (c.title, c.severity) for c in store.list_cases()}
    _mark_stale(store, bugs, resolve)
    verdicts = sorted(store.load_verdicts(run_id), key=lambda v: v.case_id)
    for verdict in verdicts:
        _apply(store, bugs, verdict, resolve, n, titles)
    write_json(marker, ProcessedRun(
        run_id=run_id, verdicts=[verdict_ref(v.run_id, v.case_id) for v in verdicts]))
    return load_bugs(store)
