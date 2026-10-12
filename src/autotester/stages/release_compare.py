"""Release record assembly, the trusted-baseline rule and the regression diff (T-167, RR3/RR6).

One job — turn the verdicts the grader already wrote for a release run into ONE `ReleaseRecord`
with ONE issues log, and diff it against its last trusted baseline (`schema.release.BASELINE_RULE`).
It reads `Verdict`s from the store and copies their `result`; it never grades, never builds a
verdict and never decides a pass (C7, RR4) — `is_pass` / `issue_kind` in `schema/release.py`
are the only readers of a `Result`. COMPARE and REPORT are `StageRunner`s over these functions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from autotester.schema.release import (
    BASELINE_RULE,
    FlowOutcome,
    RegressionDiff,
    ReleaseIssue,
    ReleaseRecord,
    ReleaseScope,
    is_pass,
    issue_kind,
)
from autotester.store.project_store import ProjectStore

if TYPE_CHECKING:
    from autotester.stages.orchestrate import StageContext

NO_BASELINE = ("no trusted baseline: no earlier release was finished, unflagged and all-PASS "
               "(a release is never compared with itself or with an untrusted run)")


def trusted_baseline(store: ProjectStore, scope: ReleaseScope) -> ReleaseRecord | None:
    """RR3: the most recent release created strictly before `scope` that `is_trusted`."""
    boundary = (scope.created_at, scope.run_id)
    eligible = [r for r in store.list_release_records()
                if r.run_id != scope.run_id and r.is_trusted
                and (r.scope.created_at, r.run_id) < boundary]
    return eligible[-1] if eligible else None


def _diff(scope: ReleaseScope, results: dict, baseline: ReleaseRecord | None) -> RegressionDiff:
    if baseline is None:
        return RegressionDiff(note=NO_BASELINE)
    before, cases = baseline.results, scope.case_ids
    now_pass = {c for c in cases if c in results and is_pass(results[c])}
    return RegressionDiff(
        baseline_run_id=baseline.run_id,
        regressed=[c for c in cases if c in before and is_pass(before[c]) and c not in now_pass],
        fixed=[c for c in cases if c in before and not is_pass(before[c]) and c in now_pass],
        new_cases=[c for c in cases if c not in before],
        note=f"compared with {baseline.run_id} under {BASELINE_RULE}")


def _flow_lines(scope: ReleaseScope, verdicts: dict, regressed: set[str]):  # type: ignore[no-untyped-def]
    """Per expected flow, in scope order: its outcome and its entries of the single log."""
    plans = {p.flow_id: p for p in scope.plans}
    flows, issues = [], []
    for flow_id in scope.expected_flow_ids:
        plan = plans.get(flow_id)
        if plan is None:  # RR6: a flow with no plan is `not run`, never omitted
            flows.append(FlowOutcome(flow_id=flow_id, status="not_run"))
            issues.append(ReleaseIssue(flow_id=flow_id, kind="not_run",
                                       detail="no persisted validation plan"))
            continue
        found = [(c, verdicts.get(c)) for c in plan.case_ids]
        for case_id, verdict in found:
            if verdict is None:
                issues.append(ReleaseIssue(flow_id=flow_id, case_id=case_id, kind="not_run",
                                           detail="no grader verdict"))
            elif not is_pass(verdict.result):
                issues.append(ReleaseIssue(
                    flow_id=flow_id, case_id=case_id, kind=issue_kind(verdict.result),
                    detail=verdict.note or verdict.scoreboard or str(verdict.result.value)))
            if case_id in regressed:
                issues.append(ReleaseIssue(flow_id=flow_id, case_id=case_id, kind="regressed",
                                           detail="passed in the trusted baseline"))
        status = ("failed" if any(v is not None and not is_pass(v.result) for _, v in found)
                  else "not_run" if any(v is None for _, v in found) else "passed")
        flows.append(FlowOutcome(flow_id=flow_id, status=status, case_ids=list(plan.case_ids)))
    return flows, issues


def build_record(store: ProjectStore, scope: ReleaseScope, *, finished: bool = False
                 ) -> ReleaseRecord:
    """The release's record from the grader's verdicts on disk; reads, never grades."""
    wanted = set(scope.case_ids)
    verdicts = {v.case_id: v for v in store.load_verdicts(scope.run_id) if v.case_id in wanted}
    results = {case_id: v.result for case_id, v in verdicts.items()}
    diff = _diff(scope, results, trusted_baseline(store, scope))
    flows, issues = _flow_lines(scope, verdicts, set(diff.regressed))
    return ReleaseRecord(
        run_id=scope.run_id, project=scope.project, approval_id=scope.approval_id,
        git_sha=scope.git_sha, scope=scope, finished=finished, results=results,
        flows=flows, issues=issues, diff=diff, created_at=scope.created_at)


def _scope_of(ctx: StageContext) -> ReleaseScope:
    scope = ctx.release_scope or ctx.store.load_release_scope(ctx.run_id)
    if scope is None:
        raise RuntimeError(f"run {ctx.run_id} has no frozen release scope")
    return scope


def make_compare_runner():  # type: ignore[no-untyped-def]
    """COMPARE: assemble and persist the record + diff (not yet `finished`)."""

    def _run(ctx: StageContext, prev_ref: str | None) -> str:
        ctx.store.save_release_record(build_record(ctx.store, _scope_of(ctx)))
        return str(ctx.store.paths.run_release_record(ctx.run_id))

    return _run


def make_report_runner():  # type: ignore[no-untyped-def]
    """REPORT: mark the one record `finished` — the release's single issues log."""

    def _run(ctx: StageContext, prev_ref: str | None) -> str:
        record = ctx.store.load_release_record(ctx.run_id)
        if record is None:
            raise RuntimeError(f"run {ctx.run_id} has no compared release record to report")
        ctx.store.save_release_record(record.model_copy(update={"finished": True}))
        return str(ctx.store.paths.run_release_record(ctx.run_id))

    return _run


def flag_bad(store: ProjectStore, run_id: str, reason: str) -> ReleaseRecord:
    """A human marks a finished release untrusted; it can then never be a baseline (RR3)."""
    record = store.load_release_record(run_id)
    if record is None:
        raise ValueError(f"no release record for run {run_id}")
    record = record.model_copy(update={"flagged_bad": True, "flagged_reason": reason})
    store.save_release_record(record)
    return record
