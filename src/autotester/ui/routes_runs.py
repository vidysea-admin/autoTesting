"""Trigger a real run. Contract: qa/contracts/ui-run.md RU1-RU4. Run-history
and report views live in `ui/routes_report.py`. Serial-vs-parallel case
execution lives in `ui/run_execution.py` (AT-567 -- split out to keep this
file under the C2 line cap).
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, NamedTuple

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse

from autotester.browser.secrets import SecretStore
from autotester.browser.video import VIDEO_OVERHEAD_MB
from autotester.core.consent import ApprovalRequired
from autotester.core.ids import ulid
from autotester.core.paths import ProjectPaths
from autotester.core.redact import placeholder_keys
from autotester.providers import for_role, why_unavailable
from autotester.providers.base import Provider, ProviderError
from autotester.schema.approval import RunApproval
from autotester.schema.case import Case, CasePriority
from autotester.schema.catalog import TIER_BY_CLASS, Catalog
from autotester.schema.crawl import CrawlBounds
from autotester.schema.enums import Action, ApprovalKind
from autotester.schema.project import Project
from autotester.schema.run import Run, RunBounds
from autotester.schema.run_queue import QueueEntry
from autotester.schema.run_state import StageCheckpoint, StageName
from autotester.stages.catalog import catalog, tiers_to_run
from autotester.stages.coverage import diff_coverage, queue_requests
from autotester.stages.explore_consent import covering_approval
from autotester.stages.orchestrate import StageContext
from autotester.stages.parallel_run import (
    DEFAULT_PER_CONTEXT_MB,
    ParallelPlan,
    _free_ram_mb,
    plan_parallel_run,
)
from autotester.stages.run_budget import RunBudget, action_cost, wall_clock_request_s
from autotester.stages.video_retention import prune_old_videos
from autotester.store.project_store import ProjectStore
from autotester.ui.helpers import _load_project_or_404
from autotester.ui.run_execution import _run_cases_in_parallel, _run_cases_serially
from autotester.ui.run_queue import QueueFull, RunRefused, get_queue, set_runner

router = APIRouter()


def _is_entry_case(case: Case, project: Project) -> bool:
    """True when this case's first step navigates to the project's own
    declared entry screen (`base_url`) -- e.g. a sign-in page. Such a case is
    testing the entry screen itself, which only means something from a
    genuinely logged-out state; the shared, persistently-authenticated
    profile every other case reuses would make the entry screen never
    appear (AT-044 -- exactly the staleness bug already fixed once for
    `scripts/run_pathlynks_first_cases.py`, but never generalized into this
    pipeline)."""
    return bool(case.steps) and case.steps[0].action is Action.NAVIGATE \
        and case.steps[0].target == project.base_url


def _require_declared_values(
    project: Project, secrets: SecretStore, slug: str, cases: list[Case] | None = None,
) -> set[str]:
    """Check referenced credentials before launch; unused roles never gate a run."""
    keys = ({ref.key for ref in project.secrets} if cases is None else {
        key for case in cases for step in case.steps
        for text in (step.target, step.value or "") for key in placeholder_keys(text)
    })
    missing = sorted(key for key in keys if not secrets.has_value(key))
    if missing:
        raise HTTPException(400, (
            f"{', '.join(missing)} has no value yet. Enter it on the project's "
            f"Credentials page (/projects/{slug}/env) before running."
            if len(missing) == 1 else
            f"these credentials have no value yet: {', '.join(missing)}. Enter them on the "
            f"project's Credentials page (/projects/{slug}/env) before running."
        ))
    return keys


def _require_live_case_approval(
    project: Project, store: ProjectStore, cases: list[Case],
    secrets: SecretStore | None = None, account_keys: set[str] | None = None,
) -> RunApproval:
    """Pre-run D-018/CN11 gate (D-068): a covering human grant, else one derived from the
    project's provisioned credentials -- reused if an earlier row covers the run, else minted.

    Refuse before run-id/directory/browser creation, naming human-grant shortfalls.
    System-derived action/probe/time brakes bound, never expand, account consent.
    """
    bounds = CrawlBounds(
        max_actions=sum(action_cost(c) for c in cases),
        wall_clock_s=wall_clock_request_s(cases),
    )
    try:
        if any(case.project != project.slug for case in cases):
            raise ApprovalRequired("case project differs from the requested project")
        return covering_approval(project, store, bounds, kind=ApprovalKind.LIVE_CASE,
                                 secrets=secrets, account_keys=account_keys or None)
    except ApprovalRequired as exc:
        raise HTTPException(403, str(exc)) from exc


def _plan_under_shared_budget(project: Project, run_id: str) -> ParallelPlan:
    """PR1 for one run, planned one run at a time and net of what the other running runs were
    already granted (hosting.md HO20): two runs starting together share one RAM budget instead of
    each assuming the whole host is free. With nothing else running this is exactly the plain
    `plan_parallel_run(project, video_enabled=True)` call."""
    queue = get_queue()
    with queue.planning(run_id) as reserved_mb:
        extra = {"free_ram_mb": max(0.0, _free_ram_mb() - reserved_mb)} if reserved_mb else {}
        plan = plan_parallel_run(project, video_enabled=True, **extra)
        queue.grant(run_id, plan.n * (DEFAULT_PER_CONTEXT_MB + VIDEO_OVERHEAD_MB))
    return plan


def _execute_with_trace(
    store: ProjectStore, run_id: str, secrets: SecretStore, project: Project,
    cases: list[Case], entry_flags: list[bool], run_dir: Path, paths: ProjectPaths,
    slug: str, judge: Provider, approval: RunApproval,
    catalog_snapshot: Catalog | None = None,
) -> ParallelPlan:
    """AT-562/AT-564: build this run's `StageContext` with the project's real
    `SecretStore` (RT6 — a real, redacted `trace.jsonl`), attach it to the
    judge so its LLM calls join that trace (RT4/RT5), decide this run's width
    (PR1), execute the cases at that width, and record one EXECUTE stage span
    covering the whole batch."""
    ctx = StageContext(store=store, run_id=run_id, secrets=secrets)
    judge.trace = ctx.trace
    plan = _plan_under_shared_budget(project, run_id)
    budget = RunBudget(approval)
    cat = catalog_snapshot if catalog_snapshot is not None else catalog(
        project, store.load_flowspec(), store)
    started = ctx.clock()
    snapshot = list(zip(cases, entry_flags, strict=True))
    for tier in tiers_to_run(cat):
        tier_cases = [case for case, _ in snapshot if TIER_BY_CLASS[case.case_class] == tier]
        tier_flags = [flag for case, flag in snapshot if TIER_BY_CLASS[case.case_class] == tier]
        if plan.n > 1:
            _run_cases_in_parallel(
                tier_cases, tier_flags, plan, project, secrets, run_dir, slug, judge, run_id,
                store, approval, budget=budget,
            )
        else:
            _run_cases_serially(
                tier_cases, tier_flags, project, secrets, run_dir, paths, slug, judge, run_id,
                store, budget=budget,
            )
    assert ctx.trace is not None
    ctx.trace.record_stage(StageCheckpoint(
        stage=StageName.EXECUTE, status="failed" if budget.stop_reason else "done",
        error=f"run budget exhausted: {budget.stop_reason}" if budget.stop_reason else None,
        started=started, finished=ctx.clock(),
    ))
    return plan


def _judge_or_400(project: Project) -> Provider:
    """The project's judge, or a 400 saying why none can serve (LL11): the model and the one
    variable to set, never a key, a prompt or an endpoint value. The queue turns the 400 of a
    queued run into `refused` (HO16/HO19), so a run launches no browser without a judge."""
    try:
        judge = for_role(project, "judge")
    except ProviderError as exc:
        raise HTTPException(400, str(exc)) from None
    if why := why_unavailable(judge):
        raise HTTPException(400, f"no AI provider is configured ({why}) -- cannot grade a run")
    return judge


class _Prepared(NamedTuple):
    store: ProjectStore
    project: Project
    cases: list[Case]
    judge: Provider
    paths: ProjectPaths
    secrets: SecretStore
    approval: RunApproval
    entry_flags: list[bool]
    cat: Catalog


def _prepare_run(slug: str, priorities: list[CasePriority] | None = None) -> _Prepared:
    """Everything a run needs, with every gate evaluated (400/403 as `HTTPException`).

    Called when the press arrives (so a refusal is immediate) and again when the queue starts the
    run (hosting.md HO19: a queued run is not a way around the credential, provider or consent
    gates). Runs every case through the same resilient pipeline
    (stages/run_case_pipeline.py) whether serial or parallel (AT-574).

    AT-562/AT-564: this is the live entry point wired to the T-172/T-173
    machinery those goal-coverage gaps named -- see `_execute_with_trace`."""
    store, project = _load_project_or_404(slug)
    cases = store.list_cases(priorities=priorities)  # FB4: selected priorities + pinned p0
    if not cases:
        raise HTTPException(400, f"project '{slug}' has no cases to run")
    judge = _judge_or_400(project)
    paths = ProjectPaths(slug)
    secrets = SecretStore.load(project, paths.env_file, strict=False)
    account_keys = _require_declared_values(project, secrets, slug, cases)
    approval = _require_live_case_approval(project, store, cases, secrets, account_keys)
    cat = catalog(project, store.load_flowspec(), store)   # snapshot taken when the run starts
    entry_flags = [_is_entry_case(c, project) for c in cases]
    return _Prepared(store, project, cases, judge, paths, secrets, approval, entry_flags, cat)


@router.post("/projects/{slug}/run")
def trigger_run(slug: str, priority: Annotated[list[CasePriority] | None, Query()] = None
                ) -> RedirectResponse:
    """Queue a real run and return at once (RU1-RU4; T-203/D-072 G6 replaced v1's synchronous
    wait). Validation and consent are checked now, so 400/403 come back immediately; the run
    itself starts when the server-wide limit and the project's single-flight slot allow
    (`ui/run_queue.py`), and the report page shows it as queued, then running."""
    _prepare_run(slug, priority)
    try:
        get_queue().submit(slug, run_id=f"run-{ulid()}", priorities=priority)  # id: after the gates
    except QueueFull as exc:
        raise HTTPException(429, str(exc)) from exc
    return RedirectResponse(f"/projects/{slug}/report", status_code=303)


def _run_queued(entry: QueueEntry) -> None:
    """The queue's executor: re-check every gate, then run the whole project as run `entry.id`."""
    try:
        prepared = _prepare_run(entry.project, entry.priorities)
    except HTTPException as exc:
        raise RunRefused(str(exc.detail)) from exc
    _execute_and_record(prepared, entry.id)


set_runner(_run_queued)


def _execute_and_record(prepared: _Prepared, run_id: str) -> None:
    """The body of a run, executed by the queue's worker: every case, then `run.json`."""
    store, project, cases, judge, paths, secrets, approval, entry_flags, cat = prepared
    slug = project.slug
    plan = _execute_with_trace(
        store, run_id, secrets, project, cases, entry_flags, paths.run_dir(run_id), paths, slug,
        judge, approval, cat,
    )
    store.save_run(Run(
        id=run_id, project=slug, case_ids=[c.id for c in cases],
        parallel_n=plan.n, parallel_bound_by=plan.bound_by,
        catalog_runnable_counts={tier.value: len(cat.runnable_in_tier(tier))
                                 for tier in tiers_to_run(cat)},
        # CN10: what it ran under, reported not capped -- a 19-year wall clock is
        # visible to whoever reads run.json instead of silently honoured.
        bounds=RunBounds(approval_id=approval.id, max_actions=approval.max_actions,
                          max_probes=approval.max_probes, wall_clock_s=approval.wall_clock_s),
    ))
    prune_old_videos(store)  # T-191/AT-587 V5: most recent 20 kept videos, project-wide
    _ask_for_what_it_did_not_recognise(store, run_id)


def _ask_for_what_it_did_not_recognise(store: ProjectStore, run_id: str) -> None:
    """Turn this run's coverage gaps into video requests.

    AT-240: `diff_coverage`, `request_for` and `add_request` were each written,
    each tested, and each called from nothing -- so across four real projects
    not one `VideoRequest` had ever been created and the north star's "when it
    meets a screen it does not know, it asks the human for a video instead of
    guessing" had never once happened. A loop whose last link is missing is not
    a slow loop, it is an open one.

    Deliberately after `save_run`: a request is about a run that HAPPENED, and
    failing to ask must never lose the run itself."""
    spec = store.load_flowspec()
    if spec is None:
        return                      # nothing learned yet -> nothing is "unknown" (V2)
    results = store.load_results(run_id)
    queue_requests(store, diff_coverage(spec, results))
