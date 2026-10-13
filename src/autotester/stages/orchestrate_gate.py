"""The checks and ledger views around the orchestration graph (RR2, T-167).

One job — refuse a release that lacks a covering signed `RunApproval` before any run
directory, checkpoint or browser exists (CN1 shape), refuse state that belongs to another run
or scope, and translate between the graph's snapshot and the `RunState` ledger. Split out of
`orchestrate.py`, which sits at the file cap. It reads approvals; it never mints or repairs
one, and it adds no approval mechanism of its own.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from autotester.core.consent import ApprovalRequired, require_project_approval
from autotester.schema.enums import ApprovalKind
from autotester.schema.project import Project
from autotester.schema.release import FlowPlan
from autotester.schema.run_state import RunState
from autotester.stages.run_budget import WALL_CLOCK_PER_ACTION_S, action_cost
from autotester.store.project_store import ProjectStore

if TYPE_CHECKING:
    from autotester.stages.orchestrate import StageContext


def plans_cost(store: ProjectStore, plans: list[FlowPlan]) -> int:
    """Actions the release will spend: each planned case's declared steps (min 1)."""
    cases = {c for p in plans for c in p.case_ids}
    return sum(action_cost(case) if (case := store.get_case(c)) else 1 for c in sorted(cases))


def release_preflight(project: Project, ctx: StageContext) -> None:
    """RR2/CN1: a release needs a valid signed `RunApproval` covering its bounds.

    The bounds checked are the LARGER of what the scope declares and what its plans cost when
    recomputed from the store, so a hand-written `scope.json` cannot under-declare its way
    past a small approval. Max (not refuse-on-mismatch) keeps an honestly frozen scope
    resumable: its declared bounds equal its cost, and a human 'yes' can never widen them."""
    scope = ctx.release_scope
    if scope is None:
        return
    if scope.project != project.slug or scope.run_id != ctx.run_id:
        raise ApprovalRequired("release scope belongs to another project or run")
    rows = [a for a in ctx.store.list_approvals() if a.id == scope.approval_id]
    actions = max(scope.max_actions, plans_cost(ctx.store, scope.plans))
    require_project_approval(  # D-088: a production project accepts a human production row only
        rows, project=project, kind=ApprovalKind.LIVE_CASE, target=project.base_url,
        actions=actions,
        wall_clock_s=max(scope.wall_clock_s, actions * WALL_CLOCK_PER_ACTION_S))


def check_lineage(project: Project, ctx: StageContext, state: RunState) -> None:
    """A ledger for another run/project, or a release whose scope changed, is refused."""
    if state.run_id != ctx.run_id or state.project_slug != project.slug:
        raise ValueError("foreign orchestration state")
    scope = ctx.release_scope
    if state.mode == "release" and (scope is None or state.scope_fingerprint != scope.fingerprint):
        raise ApprovalRequired("release scope changed or is missing")
    if state.mode != "release" and scope is not None:
        raise ApprovalRequired("cannot replace a teaching run with a release")


def reenter(state: RunState) -> dict[str, Any]:
    """Graph input that re-enters a `failed`/`running` checkpoint: reset it to `pending`."""
    stages = [c.model_copy(update={"status": "pending", "error": None})
              if c.status in ("failed", "running") else c for c in state.stages]
    return {"state": state.model_copy(update={"stages": stages}).model_dump(mode="json")}


def paused_view(snapshot: Any) -> RunState:
    """The snapshot's ledger, with a stage paused on `interrupt()` shown as `awaiting_human`
    (the pause itself is not part of the committed graph state)."""
    state = RunState.model_validate(snapshot.values["state"])
    waiting = {task.name for task in snapshot.tasks if task.interrupts}
    stages = [c.model_copy(update={"status": "awaiting_human"}) if c.stage.value in waiting else c
              for c in state.stages]
    return state.model_copy(update={"stages": stages})
