"""Trigger a real run. Contract: qa/contracts/ui-run.md RU1-RU4. Run-history
and report views live in `ui/routes_report.py`. Serial-vs-parallel case
execution lives in `ui/run_execution.py` (AT-567 -- split out to keep this
file under the C2 line cap).
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from autotester.browser.secrets import SecretStore
from autotester.core.ids import ulid
from autotester.core.paths import ProjectPaths
from autotester.providers.langchain_fallback import LangChainFallbackProvider
from autotester.schema.case import Case
from autotester.schema.enums import Action
from autotester.schema.project import Project
from autotester.schema.run import Run
from autotester.schema.run_state import StageCheckpoint, StageName
from autotester.stages.coverage import diff_coverage, queue_requests
from autotester.stages.orchestrate import StageContext
from autotester.stages.parallel_run import ParallelPlan, plan_parallel_run
from autotester.store.project_store import ProjectStore
from autotester.ui.helpers import _load_project_or_404
from autotester.ui.run_execution import _run_cases_in_parallel, _run_cases_serially

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


def _require_declared_values(project: Project, secrets: SecretStore, slug: str) -> None:
    """Refuse the run up front when a declared credential has no value yet.

    The UI path loads secrets with `strict=False`, so a missing value used to
    surface only when a step tried to type it — as `BLOCKED_HITL`, mid-run,
    after a browser had already been launched. Name the key instead, and say
    where to fix it."""
    missing = [ref.key for ref in project.secrets if not secrets.has_value(ref.key)]
    if missing:
        raise HTTPException(400, (
            f"{', '.join(missing)} has no value yet. Enter it on the project's "
            f"Credentials page (/projects/{slug}/env) before running."
            if len(missing) == 1 else
            f"these credentials have no value yet: {', '.join(missing)}. Enter them on the "
            f"project's Credentials page (/projects/{slug}/env) before running."
        ))


def _execute_with_trace(
    store: ProjectStore, run_id: str, secrets: SecretStore, project: Project,
    cases: list[Case], entry_flags: list[bool], run_dir: Path, paths: ProjectPaths,
    slug: str, judge: LangChainFallbackProvider,
) -> ParallelPlan:
    """AT-562/AT-564: build this run's `StageContext` with the project's real
    `SecretStore` (RT6 — a real, redacted `trace.jsonl`), attach it to the
    judge so its LLM calls join that trace (RT4/RT5), decide this run's width
    (PR1), execute the cases at that width, and record one EXECUTE stage span
    covering the whole batch."""
    ctx = StageContext(store=store, run_id=run_id, secrets=secrets)
    judge.trace = ctx.trace
    plan = plan_parallel_run(project)

    started = ctx.clock()
    if plan.n > 1:
        _run_cases_in_parallel(
            cases, entry_flags, plan, project, secrets, run_dir, slug, judge, run_id, store
        )
    else:
        _run_cases_serially(
            cases, entry_flags, project, secrets, run_dir, paths, slug, judge, run_id, store
        )
    assert ctx.trace is not None
    ctx.trace.record_stage(StageCheckpoint(
        stage=StageName.EXECUTE, status="done", started=started, finished=ctx.clock(),
    ))
    return plan


@router.post("/projects/{slug}/run")
def trigger_run(slug: str) -> RedirectResponse:
    """A real, synchronous run: the request waits for the browser to finish
    every case before redirecting to the report (RU1-RU4 — v1's honest
    boundary, no background job queue). Runs every case through the same
    resilient pipeline (stages/run_case_pipeline.py) whether serial or
    parallel (AT-574) -- a CLI script that wants the un-guarded, self-grading
    path still calls `run_and_grade_case` directly.

    AT-562/AT-564: this is the live entry point wired to the T-172/T-173
    machinery those goal-coverage gaps named -- see `_execute_with_trace`."""
    store, project = _load_project_or_404(slug)
    cases = store.list_cases()
    if not cases:
        raise HTTPException(400, f"project '{slug}' has no cases to run")
    judge = LangChainFallbackProvider()
    if not judge.available():
        raise HTTPException(
            400, "no AI provider is configured (set an API key in .env) -- cannot grade a run"
        )
    paths = ProjectPaths(slug)
    secrets = SecretStore.load(project, paths.env_file, strict=False)
    _require_declared_values(project, secrets, slug)
    run_id = f"run-{ulid()}"
    run_dir = paths.run_dir(run_id)
    entry_flags = [_is_entry_case(c, project) for c in cases]

    plan = _execute_with_trace(
        store, run_id, secrets, project, cases, entry_flags, run_dir, paths, slug, judge
    )

    store.save_run(Run(
        id=run_id, project=slug, case_ids=[c.id for c in cases],
        parallel_n=plan.n, parallel_bound_by=plan.bound_by,
    ))
    _ask_for_what_it_did_not_recognise(store, run_id)
    return RedirectResponse(f"/projects/{slug}/report", status_code=303)


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
