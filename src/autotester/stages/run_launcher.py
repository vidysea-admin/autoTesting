"""Prepare and execute a regression run once, enforcing credentials and covering consent."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

from autotester.browser.secrets import SecretStore
from autotester.core.consent import ApprovalRequired
from autotester.core.ids import ulid
from autotester.core.paths import ProjectPaths
from autotester.core.redact import placeholder_keys
from autotester.providers import Provider, ProviderError, for_role, why_unavailable
from autotester.schema.approval import RunApproval
from autotester.schema.case import Case
from autotester.schema.catalog import TIER_BY_CLASS, Catalog
from autotester.schema.crawl import CrawlBounds
from autotester.schema.enums import Action, ApprovalKind, Trigger
from autotester.schema.project import Project
from autotester.schema.run import Run, RunBounds
from autotester.schema.run_state import StageCheckpoint, StageName
from autotester.schema.team_enums import RunVia
from autotester.stages.catalog import catalog, tiers_to_run
from autotester.stages.coverage import diff_coverage, queue_requests
from autotester.stages.explore_consent import covering_approval
from autotester.stages.orchestrate import StageContext
from autotester.stages.parallel_run import ParallelPlan, plan_parallel_run
from autotester.stages.run_budget import RunBudget, action_cost, wall_clock_request_s
from autotester.stages.video_retention import prune_old_videos
from autotester.store.project_store import ProjectStore
from autotester.ui.run_execution import _run_cases_in_parallel, _run_cases_serially


class RunLaunchRefused(Exception):
    """A domain preflight refusal, translated by the UI and worker adapters."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code, self.detail = status_code, detail


class _Prepared(NamedTuple):
    store: ProjectStore
    project: Project
    cases: list[Case]
    judge: Provider
    paths: ProjectPaths
    secrets: SecretStore
    approval: RunApproval
    catalog_snapshot: Catalog


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
        raise RunLaunchRefused(400, (
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
        raise RunLaunchRefused(403, str(exc)) from exc


def _execute_with_trace(
    store: ProjectStore, run_id: str, secrets: SecretStore, project: Project,
    cases: list[Case], entry_flags: list[bool], run_dir: Path, paths: ProjectPaths,
    slug: str, judge: Provider, approval: RunApproval,
    catalog_snapshot: Catalog | None = None,
    capacity: Callable[[Project], ParallelPlan] | None = None,
) -> ParallelPlan:
    """AT-562/AT-564: build this run's `StageContext` with the project's real
    `SecretStore` (RT6 — a real, redacted `trace.jsonl`), attach it to the
    judge so its LLM calls join that trace (RT4/RT5), decide this run's width
    (PR1), execute the cases at that width, and record one EXECUTE stage span
    covering the whole batch."""
    ctx = StageContext(store=store, run_id=run_id, secrets=secrets)
    judge.trace = ctx.trace
    plan = capacity(project) if capacity else plan_parallel_run(project, video_enabled=True)
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


def prepare_run(slug: str) -> _Prepared:
    """Re-read cases, provider, credentials and covering approval before any execution."""
    store = ProjectStore(slug)
    project = store.load_project()
    if project is None:
        raise RunLaunchRefused(404, f"no project '{slug}'")
    cases = store.list_cases()
    if not cases:
        raise RunLaunchRefused(400, f"project '{slug}' has no cases to run")
    try:
        judge = for_role(project, "judge")
        if not judge.available():
            raise ProviderError(why_unavailable(judge) or
                                "no AI provider is configured (set an API key in .env) -- "
                                "cannot grade a run")
    except ProviderError as exc:
        raise RunLaunchRefused(400, str(exc)) from None
    paths = ProjectPaths(slug)
    secrets = SecretStore.load(project, paths.env_file, strict=False)
    account_keys = _require_declared_values(project, secrets, slug, cases)
    approval = _require_live_case_approval(project, store, cases, secrets, account_keys)
    return _Prepared(store, project, cases, judge, paths, secrets, approval,
                     catalog(project, store.load_flowspec(), store))


def launch_run(
    slug: str, *, trigger: Trigger = Trigger.MANUAL, requested_by: str | None = None,
    slot_key: str | None = None, via: RunVia | None = None, run_id: str | None = None,
    capacity: Callable[[Project], ParallelPlan] | None = None,
) -> Run:
    """The single execution-and-save path; every caller inherits current preflight."""
    store, project, cases, judge, paths, secrets, approval, cat = prepare_run(slug)
    run_id = run_id or f"run-{ulid()}"
    plan = _execute_with_trace(
        store, run_id, secrets, project, cases, [_is_entry_case(c, project) for c in cases],
        paths.run_dir(run_id), paths, slug, judge, approval, cat, capacity,
    )
    run = Run(
        id=run_id, project=slug, trigger=trigger, requested_by=requested_by,
        slot_key=slot_key, via=via, case_ids=[c.id for c in cases],
        parallel_n=plan.n, parallel_bound_by=plan.bound_by,
        catalog_runnable_counts={tier.value: len(cat.runnable_in_tier(tier))
                                 for tier in tiers_to_run(cat)},
        bounds=RunBounds(approval_id=approval.id, max_actions=approval.max_actions,
                         max_probes=approval.max_probes, wall_clock_s=approval.wall_clock_s),
    )
    store.save_run(run)
    prune_old_videos(store)
    _ask_for_what_it_did_not_recognise(store, run_id)
    return run


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
