"""The release trigger: stitch every flow's persisted plan into ONE gated release run (T-167).

One job — start (or resume) a release. It reads the project's FlowSpec and persisted
`FlowPlan`s, freezes them into a `ReleaseScope`, asks the existing consent gate for a covering
signed `RunApproval` BEFORE anything is written (RR2, CN1 shape: no run directory, no
checkpoint, no navigation without one), then hands the run to `stages/orchestrate.py`, whose
graph pauses on `interrupt()` for a human decision. It starts runs; it never judges them (C7,
RR4): execution and grading are injected stage runners, the record is built by
`stages/release_compare.py` from the grader's own verdicts, and nothing here constructs one.
"""

from __future__ import annotations

from datetime import datetime

from autotester.browser.secrets import SecretStore
from autotester.schema.crawl import CrawlBounds
from autotester.schema.enums import ApprovalKind
from autotester.schema.project import Project
from autotester.schema.release import FlowPlan, ReleaseDecision, ReleaseScope
from autotester.schema.run_state import RunState, StageName
from autotester.stages.explore_consent import covering_approval
from autotester.stages.orchestrate import StageContext, StageRunner, run_or_resume
from autotester.stages.release_compare import make_compare_runner, make_report_runner
from autotester.stages.run_budget import WALL_CLOCK_PER_ACTION_S, action_cost
from autotester.store.project_store import ProjectStore


class ReleaseError(RuntimeError):
    """A release cannot be scoped (no FlowSpec flows) — named, never a silent empty run."""


def _plan_cost(store: ProjectStore, plans: list[FlowPlan]) -> int:
    """Actions the release will spend: each planned case's declared steps (min 1)."""
    cases = {c for p in plans for c in p.case_ids}
    return sum(action_cost(case) if (case := store.get_case(c)) else 1 for c in sorted(cases))


def build_scope(project: Project, store: ProjectStore, *, run_id: str, approval_id: str,
                max_actions: int, git_sha: str | None = None,
                created_at: datetime | None = None) -> ReleaseScope:
    """Every FlowSpec flow, exactly once: planned flows carry their plan, the rest are named
    `unplanned` so the log reports them `not run` (RR6). Reads only."""
    spec = store.load_flowspec()
    if spec is None or not spec.flows:
        raise ReleaseError(f"{project.slug}: no FlowSpec flows to build a release from")
    by_flow = {p.flow_id: p for p in store.list_flow_plans()}
    expected = [f.id for f in spec.flows]
    extra = {"created_at": created_at} if created_at else {}
    return ReleaseScope(
        run_id=run_id, project=project.slug, approval_id=approval_id, git_sha=git_sha,
        max_actions=max_actions, wall_clock_s=max_actions * WALL_CLOCK_PER_ACTION_S,
        expected_flow_ids=expected, plans=[by_flow[f] for f in expected if f in by_flow],
        unplanned_flow_ids=[f for f in expected if f not in by_flow], **extra)


def _frozen_or_new(project: Project, store: ProjectStore, run_id: str,
                   secrets: SecretStore | None, git_sha: str | None,
                   created_at: datetime | None) -> ReleaseScope:
    """A resume uses the scope frozen at the first call; a first call gates, then scopes."""
    frozen = store.load_release_scope(run_id)
    if frozen is not None:
        return frozen
    plans = store.list_flow_plans()
    spec = store.load_flowspec()
    in_scope = [p for p in plans if spec and p.flow_id in {f.id for f in spec.flows}]
    actions = max(1, _plan_cost(store, in_scope))
    bounds = CrawlBounds(max_actions=actions, wall_clock_s=actions * WALL_CLOCK_PER_ACTION_S)
    approval = covering_approval(project, store, bounds, kind=ApprovalKind.LIVE_CASE,
                                 secrets=secrets)  # RR2: ApprovalRequired, nothing written
    return build_scope(project, store, run_id=run_id, approval_id=approval.id,
                       max_actions=actions, git_sha=git_sha, created_at=created_at)


def start_release(
    project: Project, store: ProjectStore, *, run_id: str,
    runners: dict[StageName, StageRunner], secrets: SecretStore | None = None,
    git_sha: str | None = None, decision: ReleaseDecision | None = None,
    created_at: datetime | None = None,
) -> RunState:
    """Start a release, or resume it with `run_id` (and `decision` to answer a pause).

    `runners` supplies EXECUTE and GRADE (the existing stages, injected); COMPARE and REPORT
    are wired here. Without a covering approval this raises `ApprovalRequired` before the
    graph exists. With one, the run stops at CONFIRM until a `decision` answers it (RR2)."""
    scope = _frozen_or_new(project, store, run_id, secrets, git_sha, created_at)
    wired = {**runners, StageName.COMPARE: make_compare_runner(),
             StageName.REPORT: make_report_runner()}
    ctx = StageContext(store=store, run_id=run_id, runners=wired, secrets=secrets,
                       release_scope=scope, decision=decision)
    return run_or_resume(project, ctx)
