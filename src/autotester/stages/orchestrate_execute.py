"""Persist frozen pipeline observations under canonical approval and browser-budget boundaries."""

from __future__ import annotations

import contextlib
from pathlib import Path

from autotester.browser.profiles import wipe_entry_profile
from autotester.browser.session import BrowserSession
from autotester.core.paths import ProjectPaths
from autotester.schema.enums import Outcome, ReviewStatus
from autotester.schema.flowspec import FlowSpec
from autotester.schema.project import Project
from autotester.schema.run import RawResult, RunBounds
from autotester.schema.run_state import PipelineBatch
from autotester.stages.browser_recovery import BrowserRecovery, is_browser_closed
from autotester.stages.orchestrate import StageContext
from autotester.stages.review import require_generatable
from autotester.stages.run_budget import RunBudget
from autotester.stages.run_case_pipeline import observe_case
from autotester.stages.run_launcher import (
    is_entry_case,
    require_declared_values,
    require_live_case_approval,
)
from autotester.store.filestore import read_json, write_json
from autotester.store.project_store import ProjectStore

INTERRUPTION = "execution interrupted; unfinished cases were not repeated; start a new run to retry"


class PipelineStore(ProjectStore):
    """A view of frozen inputs over the same filestore, not another persistence implementation."""

    def __init__(self, store: ProjectStore, batch: PipelineBatch, *, frozen_cases: bool = False):
        super().__init__(store.paths.slug, store.paths.root)
        self._batch, self._frozen_cases = batch, frozen_cases

    def load_flowspec(self) -> FlowSpec:
        return self._batch.flowspec

    def list_cases(self, priorities=None):
        if not self._frozen_cases:
            return super().list_cases(priorities)
        if priorities is not None:
            raise ValueError("a frozen pipeline cannot change case selection")
        return list(self._batch.cases)


def load_pipeline_batch(ctx: StageContext, ref: str | None) -> PipelineBatch:
    if not ref:
        raise ValueError("downstream stage has no preceding artifact")
    batch = read_json(Path(ref), PipelineBatch)
    if batch is None:
        raise ValueError("downstream stage artifact is missing")
    validate_pipeline_batch(ctx, batch)
    return batch


def validate_pipeline_batch(ctx: StageContext, batch: PipelineBatch) -> None:
    ids = [case.id for case in batch.cases]
    if (batch.run_id != ctx.run_id or batch.project != ctx.store.paths.slug
            or batch.flowspec.project != batch.project
            or any(case.project != batch.project for case in batch.cases)):
        raise ValueError("pipeline artifact belongs to another run or project")
    if (len(ids) != len(set(ids))
            or any(result.case_id not in ids for result in batch.results)
            or any(v.case_id not in ids or v.run_id != ctx.run_id for v in batch.verdicts)):
        raise ValueError("pipeline artifact mixes case or verdict lineage")
    if batch.input_fingerprint != PipelineBatch.fingerprint(batch.flowspec, batch.cases):
        raise ValueError("frozen pipeline input content changed")
    root = ctx.store.paths.run_dir(ctx.run_id).resolve()
    if any(key not in ids or Path(ref).is_absolute()
           or not (root / ref).resolve().is_relative_to(root)
           for key, ref in batch.video_refs.items()):
        raise ValueError("pipeline video evidence escapes its run")


def save_pipeline_batch(ctx: StageContext, batch: PipelineBatch, name: str) -> str:
    validate_pipeline_batch(ctx, batch)
    if ctx.secrets is not None:
        ctx.secrets.guard_prompt(batch.model_dump_json())
    path = ctx.store.paths.pipeline_artifact(ctx.run_id, name)
    write_json(path, batch)
    return str(path)


def require_pipeline_eligibility(ctx: StageContext, spec: FlowSpec) -> None:
    require_generatable(spec)
    canonical = ctx.store.load_flowspec()
    if canonical is not None and canonical.review.status is ReviewStatus.NEEDS_EDIT:
        require_generatable(canonical)


def _case_observation(case, session, store):
    try:
        session.budget.check_start()
        scripted, video = observe_case(case, session, store)
        return scripted.result, video
    except Exception as exc:
        return RawResult(case_id=case.id, outcome=Outcome.ERRORED,
                         error=session.secrets.scrub_optional(f"{type(exc).__name__}: {exc}")), None


def _start_session(ctx, project, budget, case, session_cls, *, entry=False):
    paths = (ProjectPaths(f"{project.slug}-entry-test", ctx.store.paths.root)
             if entry else ctx.store.paths)
    if entry:
        wipe_entry_profile(paths.profile_dir)
    session = session_cls(project, ctx.secrets, ctx.store.paths.run_dir(ctx.run_id),
                          paths, record_video=True)
    session.budget = budget
    session.state.evidence_prefix = case.id
    try:
        budget.check_start()
        session.start()
    except BaseException:
        with contextlib.suppress(Exception):
            session.close()
        raise
    return session


def _persist_observation(ctx, batch, result, video):
    ctx.store.save_result(ctx.run_id, result)
    batch.results.append(result)
    if video is not None:
        batch.video_refs[result.case_id] = video
    save_pipeline_batch(ctx, batch, "execution-progress")


def _recover_interrupted(ctx: StageContext, batch: PipelineBatch) -> str:
    observed = {r.case_id: r for r in batch.results}
    observed.update({r.case_id: r for r in ctx.store.load_results(ctx.run_id)})
    if set(observed) - {case.id for case in batch.cases}:
        raise ValueError("interrupted execution mixes case lineage")
    batch.results = []
    batch.interrupted = True
    for case in batch.cases:
        result = observed.get(case.id) or RawResult(
            case_id=case.id, outcome=Outcome.NOT_RUN, not_run_reason=INTERRUPTION)
        ctx.store.save_result(ctx.run_id, result)
        batch.results.append(result)
    return save_pipeline_batch(ctx, batch, "execute")


def _run_observations(ctx, project, batch, budget, session_cls):
    store = PipelineStore(ctx.store, batch)
    normal = None
    startup_error = None
    recovery = None
    ordered = sorted(batch.cases, key=lambda case: not is_entry_case(case, project))
    try:
        for case in ordered:
            entry = is_entry_case(case, project)
            session = None
            try:
                if entry:
                    session = _start_session(ctx, project, budget, case,
                                             session_cls, entry=True)
                else:
                    if normal is None and startup_error is None:
                        normal = _start_session(ctx, project, budget, case, session_cls)
                        recovery = BrowserRecovery(normal)
                    if startup_error is not None:
                        raise RuntimeError(startup_error)
                    session = normal
                    session.state.evidence_prefix = case.id
                result, video = _case_observation(case, session, store)
                if not entry and is_browser_closed(result):
                    recovery.recover()
                    startup_error = recovery.stop_reason
            except Exception as exc:
                reason = ctx.secrets.scrub_optional(f"{type(exc).__name__}: {exc}")
                result = RawResult(case_id=case.id, outcome=Outcome.ERRORED, error=reason)
                video = None
                if not entry:
                    startup_error = reason
            finally:
                if entry and session is not None:
                    with contextlib.suppress(Exception):
                        session.close()
            _persist_observation(ctx, batch, result, video)
    finally:
        if normal is not None:
            with contextlib.suppress(Exception):
                normal.close()


def execute_pipeline_batch(ctx: StageContext, batch: PipelineBatch, project: Project,
                           *, session_cls=None) -> str:
    """Observe once; an interrupted in-flight run never resets its budget or repeats writes."""
    require_pipeline_eligibility(ctx, batch.flowspec)
    complete = ctx.store.paths.pipeline_artifact(ctx.run_id, "execute")
    if complete.exists():
        prior = load_pipeline_batch(ctx, str(complete))
        if prior.input_fingerprint != batch.input_fingerprint:
            raise ValueError("completed execution has different frozen inputs")
        return str(complete)
    progress = ctx.store.paths.pipeline_artifact(ctx.run_id, "execution-progress")
    if progress.exists():
        prior = load_pipeline_batch(ctx, str(progress))
        if prior.input_fingerprint != batch.input_fingerprint:
            raise ValueError("interrupted execution has different frozen inputs")
        return _recover_interrupted(ctx, prior)
    keys = require_declared_values(project, ctx.secrets, project.slug, batch.cases)
    approval = require_live_case_approval(project, ctx.store, batch.cases, ctx.secrets, keys)
    budget = RunBudget.for_cases(approval, batch.cases)
    batch.bounds = RunBounds(approval_id=approval.id, max_actions=approval.max_actions,
                             max_probes=approval.max_probes, wall_clock_s=approval.wall_clock_s)
    batch.execution_started = True
    save_pipeline_batch(ctx, batch, "execution-progress")
    _run_observations(ctx, project, batch, budget, session_cls or BrowserSession)
    return save_pipeline_batch(ctx, batch, "execute")
