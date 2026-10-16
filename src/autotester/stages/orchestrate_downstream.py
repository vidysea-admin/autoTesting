"""Adapt generation, observation, independent grading and exports into durable pipeline stages."""

from __future__ import annotations

from pathlib import Path

from autotester.providers import for_role
from autotester.providers.base import Provider
from autotester.schema.enums import CaseStatus, Result, ReviewStatus, Trigger
from autotester.schema.flowspec import FlowSpec
from autotester.schema.project import Project
from autotester.schema.run_state import ExpansionAttempt, PipelineBatch, StageName
from autotester.schema.verdict import Verdict
from autotester.stages.expand import expand
from autotester.stages.flow_plan import plans_from_batch
from autotester.stages.grade import grade
from autotester.stages.orchestrate import StageContext
from autotester.stages.orchestrate_execute import (
    INTERRUPTION,
    PipelineStore,
    execute_pipeline_batch,
    guard_pipeline_artifacts,
    load_pipeline_batch,
    require_pipeline_eligibility,
    save_pipeline_batch,
)
from autotester.stages.report_export import export_excel, export_html
from autotester.stages.run_case_pipeline import finalize_case_video, rubric_for_case
from autotester.stages.run_launcher import (
    RunSeams,
    ask_for_what_it_did_not_recognise,
    judge_or_refuse,
    save_tracked_run,
)
from autotester.stages.video_retention import prune_old_videos_safely
from autotester.store.filestore import read_json, write_json
from autotester.store.project_store import ProjectStore


def _role_model(ctx, project, role, supplied):
    model = supplied if supplied is not None else for_role(project, role)
    model.trace = ctx.trace
    return model


def _generation_reentry(ctx, spec):
    complete = ctx.store.paths.pipeline_artifact(ctx.run_id, "expand")
    fingerprint = PipelineBatch.fingerprint(spec, [])
    if complete.exists():
        prior = load_pipeline_batch(ctx, str(complete))
        if PipelineBatch.fingerprint(prior.flowspec, []) != fingerprint:
            raise ValueError("completed generation has a different MODEL")
        return str(complete)
    marker = ctx.store.paths.pipeline_artifact(ctx.run_id, "expansion-attempt")
    attempt = read_json(marker, ExpansionAttempt)
    if attempt is not None:
        if (attempt.run_id != ctx.run_id or attempt.project != ctx.store.paths.slug
                or attempt.model_fingerprint != fingerprint):
            raise ValueError("generation attempt mixes MODEL or run lineage")
        raise ValueError("EXPAND interrupted or failed after call admission; start a new run. "
                         + (attempt.error or "Physical usage is unavailable."))
    return None


def _mark_generation(ctx, spec, *, error=None):
    attempt = ExpansionAttempt(run_id=ctx.run_id, project=spec.project,
                               model_fingerprint=PipelineBatch.fingerprint(spec, []), error=error)
    if ctx.secrets is not None:
        ctx.secrets.guard_prompt(attempt.model_dump_json())
    write_json(ctx.store.paths.pipeline_artifact(ctx.run_id, "expansion-attempt"), attempt)


def make_expand_stage(project: Project, *, generator: Provider | None = None,
                      initial_blocked: bool = False):
    def run(ctx: StageContext, prev_ref: str | None) -> str:
        if not prev_ref:
            raise ValueError("EXPAND has no MODEL artifact")
        spec = read_json(Path(prev_ref), FlowSpec)
        if spec is None or spec.project != project.slug:
            raise ValueError("MODEL artifact is missing or belongs to another project")
        if initial_blocked:
            raise ValueError("existing NEEDS_EDIT review blocks generation")
        require_pipeline_eligibility(ctx, spec)
        if prior := _generation_reentry(ctx, spec):
            return prior
        model = _role_model(ctx, project, "agent", generator)
        try:
            generated = expand(spec, model, store=ctx.store, secrets=ctx.secrets,
                               before_call=lambda: _mark_generation(ctx, spec))
            guard_pipeline_artifacts(ctx, *generated)
        except Exception as exc:
            if ctx.store.paths.pipeline_artifact(ctx.run_id, "expansion-attempt").exists():
                _mark_generation(ctx, spec, error=ctx.secrets.scrub_optional(
                    f"{type(exc).__name__}: {exc}"))
            raise
        for case in generated:
            ctx.store.add_case(case)
        cases = [c.model_copy(deep=True) for c in ctx.store.list_cases()
                 if c.status is not CaseStatus.RETIRED]
        if not cases:
            raise ValueError("FlowSpec produced no runnable cases")
        batch = PipelineBatch(run_id=ctx.run_id, project=project.slug, flowspec=spec,
                              cases=cases, input_fingerprint=PipelineBatch.fingerprint(spec, cases))
        return save_pipeline_batch(ctx, batch, "expand")
    return run


def make_execute_stage(project: Project, *, judge: Provider | None = None, session_cls=None):
    def run(ctx: StageContext, prev_ref: str | None) -> str:
        batch = load_pipeline_batch(ctx, prev_ref)
        model = _role_model(ctx, project, "judge", judge)
        judge_or_refuse(project, RunSeams(judge_factory=lambda _: model))
        return execute_pipeline_batch(ctx, batch, project, session_cls=session_cls)
    return run


def _require_complete_observations(batch: PipelineBatch) -> None:
    ids = [case.id for case in batch.cases]
    seen = [result.case_id for result in batch.results]
    if not batch.execution_started or batch.bounds is None or sorted(ids) != sorted(seen):
        raise ValueError("GRADE needs one persisted execution observation for every frozen case")


def _recover_grading(ctx, batch):
    saved = {v.case_id: v for v in ctx.store.load_verdicts(ctx.run_id)}
    if any(v.run_id != ctx.run_id or key not in {c.id for c in batch.cases}
           for key, v in saved.items()):
        raise ValueError("interrupted grading mixes verdict lineage")
    batch.verdicts = []
    for case in batch.cases:
        verdict = saved.get(case.id) or Verdict(
            run_id=ctx.run_id, case_id=case.id, result=Result.INCONCLUSIVE,
            grader_provider="unavailable", note="Grading interrupted or failed; uncertain "
            "judgments "
            "were not repeated. Start a new run to retry; physical usage is unavailable."
            + (f" Original failure: {batch.grading_error}" if batch.grading_error else ""))
        guard_pipeline_artifacts(ctx, verdict)
        ctx.store.save_verdict(ctx.run_id, verdict)
        batch.verdicts.append(verdict)
    return save_pipeline_batch(ctx, batch, "grade")


def make_grade_stage(project: Project, *, judge: Provider | None = None):
    def run(ctx: StageContext, prev_ref: str | None) -> str:
        batch = load_pipeline_batch(ctx, prev_ref)
        _require_complete_observations(batch)
        progress = ctx.store.paths.pipeline_artifact(ctx.run_id, "grading-progress")
        if progress.exists():
            prior = load_pipeline_batch(ctx, str(progress))
            if prior.input_fingerprint != batch.input_fingerprint:
                raise ValueError("interrupted grading has different frozen inputs")
            return _recover_grading(ctx, prior)
        model = _role_model(ctx, project, "judge", judge)
        view = PipelineStore(ctx.store, batch)
        cases = {case.id: case for case in batch.cases}
        batch.verdicts = []
        save_pipeline_batch(ctx, batch, "grading-progress")
        for result in batch.results:
            try:
                verdict = grade(rubric_for_case(cases[result.case_id], view), result,
                                ctx.run_id, model, run_dir=ctx.store.paths.run_dir(ctx.run_id),
                                secrets=ctx.secrets)
            except Exception as exc:
                batch.grading_error = ctx.secrets.scrub_optional(f"{type(exc).__name__}: {exc}")
                save_pipeline_batch(ctx, batch, "grading-progress")
                raise
            guard_pipeline_artifacts(ctx, result, verdict)
            finalize_case_video(result, verdict, batch.video_refs.get(result.case_id),
                                ctx.store.paths.run_dir(ctx.run_id))
            ctx.store.save_result(ctx.run_id, result)
            ctx.store.save_verdict(ctx.run_id, verdict)
            batch.verdicts.append(verdict)
            save_pipeline_batch(ctx, batch, "grading-progress")
        return save_pipeline_batch(ctx, batch, "grade")
    return run


def make_report_stage():
    def run(ctx: StageContext, prev_ref: str | None) -> str:
        batch = load_pipeline_batch(ctx, prev_ref)
        _require_complete_observations(batch)
        ids = [case.id for case in batch.cases]
        if sorted(ids) != sorted(v.case_id for v in batch.verdicts):
            raise ValueError("REPORT needs one verdict per frozen case")
        view = PipelineStore(ctx.store, batch, frozen_cases=True)
        prior = ctx.store.load_run(ctx.run_id)
        fields = {"created_at": prior.created_at} if prior is not None else {}
        save_tracked_run(view, id=ctx.run_id, project=batch.project, case_ids=ids,
                         trigger=Trigger.MANUAL, bounds=batch.bounds, parallel_n=1,
                         parallel_bound_by="config",
                         preflight_warnings=[INTERRUPTION] if batch.interrupted else [], **fields)
        cases = {case.id: case for case in batch.cases}
        output = ctx.store.paths.run_dir(ctx.run_id)
        html = export_html(batch.project, ctx.run_id, output / "report.html",
                           ctx.store.paths.root, case_overrides=cases)
        export_excel(batch.project, ctx.run_id, output / "report.xlsx",
                     ctx.store.paths.root, case_overrides=cases)
        for plan in plans_from_batch(batch):  # RR6: a completed flow leaves its plan
            ctx.store.save_flow_plan(plan)
        ask_for_what_it_did_not_recognise(view, ctx.run_id)
        prune_old_videos_safely(view)  # AT-735: after the O5 ask, error-safe
        return str(html)
    return run


def downstream_runners(project: Project, store: ProjectStore, *,
                       generator: Provider | None = None, judge: Provider | None = None,
                       session_cls=None):
    """Caller seam; entry/MODEL ownership remains with their shared CLI/UI adapters."""
    canonical = store.load_flowspec()
    blocked = canonical is not None and canonical.review.status is ReviewStatus.NEEDS_EDIT
    return {
        StageName.EXPAND: make_expand_stage(project, generator=generator, initial_blocked=blocked),
        StageName.EXECUTE: make_execute_stage(project, judge=judge, session_cls=session_cls),
        StageName.GRADE: make_grade_stage(project, judge=judge),
        StageName.REPORT: make_report_stage(),
    }
