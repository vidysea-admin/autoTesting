"""The one run launcher: gates, execution and the saved `Run` (T-205, team-foundation TF1/TF2).

One job: given a project, a trigger, an optional requester and an optional slot key, load the
project and its cases, apply the pre-run gates, execute every case through the resilient
pipeline and save the `Run`. The UI Run button, the queue worker, the Test button and the
scheduler's tick all reach a run through `launch_run`, and nothing else in `src/` builds a
`Run` for them or calls `run_cases_traced`.

The gates are part of the launcher, not of any caller (so none can skip them, and there is no
parameter that does): 400 for no cases / no provider / a credential with no value, then the
D-018 live-case approval (403, AT-570; D-068 derives it from the project's own credentials)
before a run id, a directory or a browser exists.

It does not queue (`ui/run_queue.py`), schedule (`stages/scheduler.py`) or authenticate, and it
imports no web framework: a queue worker or the CLI tick can call it. Refusals are
`LaunchRefused` carrying the HTTP status the route shows. `RunSeams` lets a caller supply the
judge factory, the width planner and the shared-RAM ledger (the queue); defaults are the real ones.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from contextlib import AbstractContextManager
from pathlib import Path
from typing import NamedTuple, Protocol

from autotester.browser.secrets import SecretStore
from autotester.browser.video import VIDEO_OVERHEAD_MB
from autotester.core.consent import ApprovalRequired
from autotester.core.ids import ulid
from autotester.core.paths import ProjectPaths
from autotester.core.redact import placeholder_keys
from autotester.core.safe_names import SLUG_PATTERN
from autotester.providers import for_role, why_unavailable
from autotester.providers.base import Provider, ProviderError
from autotester.schema.approval import RunApproval
from autotester.schema.case import Case, CasePriority
from autotester.schema.catalog import TIER_BY_CLASS, Catalog
from autotester.schema.crawl import CrawlBounds
from autotester.schema.enums import Action, ApprovalKind, CaseStatus, Trigger
from autotester.schema.project import Project
from autotester.schema.run import Run, RunBounds
from autotester.schema.run_state import StageCheckpoint, StageName
from autotester.schema.team_enums import RunVia
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
from autotester.ui.run_execution import _run_cases_in_parallel, _run_cases_serially

__all__ = ["DEFAULT_SEAMS", "LaunchRefused", "Prepared", "RunSeams", "launch_run",
           "prepare_run"]


class LaunchRefused(Exception):
    """A gate said no. `status` is the HTTP code a route shows (400, 403, 404); `reason` is
    the human sentence."""

    def __init__(self, status: int, reason: str) -> None:
        super().__init__(reason)
        self.status, self.reason = status, reason


class PlanningLedger(Protocol):
    """What the run queue offers so concurrent runs plan against one RAM budget (HO20)."""

    def planning(self, run_id: str) -> AbstractContextManager[float]: ...

    def grant(self, run_id: str, megabytes: float) -> None: ...


def default_judge(project: Project) -> Provider:
    """The project's judge via the one provider factory (LL2/LL11)."""
    return for_role(project, "judge")


class RunSeams(NamedTuple):
    """The collaborators a caller may substitute; the defaults are the production ones."""

    judge_factory: Callable[[Project], Provider] = default_judge
    planner: Callable[..., ParallelPlan] = plan_parallel_run
    free_ram_mb: Callable[[], float] = _free_ram_mb
    ledger: PlanningLedger | None = None


DEFAULT_SEAMS = RunSeams()


class Prepared(NamedTuple):
    store: ProjectStore
    project: Project
    cases: list[Case]
    judge: Provider
    paths: ProjectPaths
    secrets: SecretStore
    approval: RunApproval
    entry_flags: list[bool]
    cat: Catalog


def is_entry_case(case: Case, project: Project) -> bool:
    """True when this case's first step navigates to the project's own declared entry screen
    (`base_url`) -- e.g. a sign-in page. Such a case tests the entry screen itself, which only
    means something from a genuinely logged-out state; the shared, persistently-authenticated
    profile every other case reuses would make it never appear (AT-044)."""
    return bool(case.steps) and case.steps[0].action is Action.NAVIGATE \
        and case.steps[0].target == project.base_url


def require_declared_values(
    project: Project, secrets: SecretStore, slug: str, cases: list[Case] | None = None,
) -> set[str]:
    """Check referenced credentials before launch; unused roles never gate a run."""
    keys = ({ref.key for ref in project.secrets} if cases is None else {
        key for case in cases for step in case.steps
        for text in (step.target, step.value or "") for key in placeholder_keys(text)
    })
    missing = sorted(key for key in keys if not secrets.has_value(key))
    if missing:
        raise LaunchRefused(400, (
            f"{', '.join(missing)} has no value yet. Enter it on the project's "
            f"Credentials page (/projects/{slug}/env) before running."
            if len(missing) == 1 else
            f"these credentials have no value yet: {', '.join(missing)}. Enter them on the "
            f"project's Credentials page (/projects/{slug}/env) before running."
        ))
    return keys


def require_live_case_approval(
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
        raise LaunchRefused(403, str(exc)) from exc


def judge_or_refuse(project: Project, seams: RunSeams) -> Provider:
    """The project's judge, or a 400 saying why none can serve (LL11): the model and the one
    variable to set, never a key, a prompt or an endpoint value. A queued run's 400 becomes
    `refused` (HO16/HO19), so a run launches no browser without a judge."""
    try:
        judge = seams.judge_factory(project)
    except ProviderError as exc:
        raise LaunchRefused(400, str(exc)) from None
    if why := why_unavailable(judge):
        raise LaunchRefused(400, f"no AI provider is configured ({why}) -- cannot grade a run")
    return judge


def prepare_run(slug: str, seams: RunSeams = DEFAULT_SEAMS,
                priorities: list[CasePriority] | None = None) -> Prepared:
    """Everything a run needs, with every gate evaluated (`LaunchRefused` otherwise).

    Called when a request arrives (so a refusal is immediate) and again when the run starts
    (hosting.md HO19: a queued run is not a way around the credential, provider or consent
    gates). Every launch goes through here: there is no way to start a run without it."""
    if not re.fullmatch(SLUG_PATTERN, slug):
        raise LaunchRefused(400, "invalid project slug")
    store = ProjectStore(slug)
    project = store.load_project()
    if project is None:
        raise LaunchRefused(404, f"no project '{slug}'")
    cases = [c for c in store.list_cases(priorities=priorities)  # FB4: priorities + pinned p0
             if c.status is not CaseStatus.RETIRED]  # AT-774: retired beats a pin
    if not cases:
        raise LaunchRefused(400, f"project '{slug}' has no cases to run")
    judge = judge_or_refuse(project, seams)
    paths = ProjectPaths(slug)
    secrets = SecretStore.load(project, paths.env_file, strict=False)
    account_keys = require_declared_values(project, secrets, slug, cases)
    approval = require_live_case_approval(project, store, cases, secrets, account_keys)
    cat = catalog(project, store.load_flowspec(), store)   # snapshot taken when the run starts
    entry_flags = [is_entry_case(c, project) for c in cases]
    return Prepared(store, project, cases, judge, paths, secrets, approval, entry_flags, cat)


def plan_under_shared_budget(
    project: Project, run_id: str, seams: RunSeams = DEFAULT_SEAMS,
) -> ParallelPlan:
    """PR1 for one run, planned net of what the other running runs were already granted
    (hosting.md HO20): two runs starting together share one RAM budget instead of each assuming
    the whole host is free. With no ledger, or nothing else running, this is exactly the plain
    `planner(project, video_enabled=True)` call."""
    if seams.ledger is None:
        return seams.planner(project, video_enabled=True)
    with seams.ledger.planning(run_id) as reserved_mb:
        extra = {"free_ram_mb": max(0.0, seams.free_ram_mb() - reserved_mb)} if reserved_mb else {}
        plan = seams.planner(project, video_enabled=True, **extra)
        seams.ledger.grant(run_id, plan.n * (DEFAULT_PER_CONTEXT_MB + VIDEO_OVERHEAD_MB))
    return plan


def run_cases_traced(
    store: ProjectStore, run_id: str, secrets: SecretStore, project: Project,
    cases: list[Case], entry_flags: list[bool], run_dir: Path, paths: ProjectPaths,
    slug: str, judge: Provider, approval: RunApproval,
    catalog_snapshot: Catalog | None = None, seams: RunSeams = DEFAULT_SEAMS,
) -> ParallelPlan:
    """AT-562/AT-564: build this run's `StageContext` with the project's real `SecretStore`
    (RT6 -- a real, redacted `trace.jsonl`), attach it to the judge so its LLM calls join that
    trace (RT4/RT5), decide this run's width (PR1), execute the cases at that width tier by
    tier, and record one EXECUTE stage span covering the whole batch."""
    ctx = StageContext(store=store, run_id=run_id, secrets=secrets)
    judge.trace = ctx.trace
    plan = plan_under_shared_budget(project, run_id, seams)
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


def launch_run(
    slug: str, *, run_id: str | None = None, trigger: Trigger = Trigger.MANUAL,
    requested_by: str | None = None, slot_key: str | None = None, via: RunVia | None = None,
    seams: RunSeams = DEFAULT_SEAMS, priorities: list[CasePriority] | None = None,
) -> Run:
    """Run the project (every case, or `priorities` plus pinned p0) as `run_id` and save it. The one
    place a `Run` is built.

    The gates run here, so every caller is gated and none can pass a flag to skip them. Raises
    `LaunchRefused` before any run directory or browser exists."""
    store, project, cases, judge, paths, secrets, approval, entry_flags, cat = prepare_run(
        slug, seams, priorities)
    run_id = run_id or f"run-{ulid()}"
    plan = run_cases_traced(
        store, run_id, secrets, project, cases, entry_flags, paths.run_dir(run_id), paths, slug,
        judge, approval, cat, seams,
    )
    run = Run(
        id=run_id, project=slug, case_ids=[c.id for c in cases], trigger=trigger,
        requested_by=requested_by, slot_key=slot_key, via=via,
        parallel_n=plan.n, parallel_bound_by=plan.bound_by,
        catalog_runnable_counts={tier.value: len(cat.runnable_in_tier(tier))
                                 for tier in tiers_to_run(cat)},
        # CN10: what it ran under, reported not capped -- a 19-year wall clock is
        # visible to whoever reads run.json instead of silently honoured.
        bounds=RunBounds(approval_id=approval.id, max_actions=approval.max_actions,
                         max_probes=approval.max_probes, wall_clock_s=approval.wall_clock_s),
    )
    store.save_run(run)
    prune_old_videos(store)  # T-191/AT-587 V5: most recent 20 kept videos, project-wide
    ask_for_what_it_did_not_recognise(store, run_id)
    return run


def ask_for_what_it_did_not_recognise(store: ProjectStore, run_id: str) -> None:
    """Turn this run's coverage gaps into video requests (AT-240: the north star's "ask the
    human for a video when it meets an unknown screen" had never happened). Deliberately after
    `save_run`: a request is about a run that HAPPENED, and failing to ask must never lose it."""
    spec = store.load_flowspec()
    if spec is None:
        return                      # nothing learned yet -> nothing is "unknown" (V2)
    queue_requests(store, diff_coverage(spec, store.load_results(run_id)))
