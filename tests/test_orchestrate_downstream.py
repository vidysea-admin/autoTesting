"""Frozen downstream inputs, distinct real checkpoints, consent and report lineage."""

from pathlib import Path

import pytest
from downstream_fixture import DownstreamSession, downstream_fixture

from autotester.core.paths import ProjectPaths
from autotester.schema.enums import Outcome, ReviewStatus
from autotester.schema.flowspec import Review
from autotester.schema.run_state import PipelineBatch, StageName
from autotester.stages import expand as expansion
from autotester.stages import orchestrate_downstream as stages
from autotester.stages import orchestrate_execute as execution
from autotester.stages.orchestrate import run_or_resume
from autotester.stages.review import FlowSpecNotReviewed
from autotester.stages.run_launcher import LaunchRefused
from autotester.store.filestore import read_json, write_json


def _expand(fixture):
    *_, ref, _generator, _judge, ctx = fixture
    return ctx.runners[StageName.EXPAND](ctx, ref)


def _additional_case(ref, store, case_id, *, target=None):
    batch = read_json(Path(ref), PipelineBatch)
    case = batch.cases[0].model_copy(deep=True)
    case.id = case_id
    if target is not None:
        case.steps[0].target = target
    batch.cases.append(case)
    store.add_case(case)
    batch.input_fingerprint = PipelineBatch.fingerprint(batch.flowspec, batch.cases)
    write_json(Path(ref), batch)
    return case


def test_downstream_generation_reads_exact_model_and_preserves_approved_truth(tmp_path):
    f = downstream_fixture(tmp_path)
    store, _, spec, _, _, _, _ctx = f
    approved = spec.model_copy(update={"flows": [], "review": Review(status=ReviewStatus.APPROVED)})
    store.save_flowspec(approved)
    before = store.paths.flowspec.read_bytes()
    ref = _expand(f)
    batch = read_json(Path(ref), PipelineBatch)
    assert batch.flowspec == spec and len(batch.cases) == 1
    assert "from unreviewed DRAFT flow" in batch.cases[0].provenance
    assert store.paths.flowspec.read_bytes() == before
    calls = len(f[-3].prompts)
    assert _expand(f) == ref and len(f[-3].prompts) == calls


def test_downstream_needs_edit_and_unreconciled_model_stop_before_spend(tmp_path):
    f = downstream_fixture(tmp_path)
    store, _, spec, ref, generator, _, _ctx = f
    store.save_flowspec(spec.model_copy(update={"review": Review(status=ReviewStatus.NEEDS_EDIT)}))
    with pytest.raises(FlowSpecNotReviewed):
        _expand(f)
    assert generator.prompts == []
    store.save_flowspec(spec)
    spec.flows[0].kind = None
    write_json(Path(ref), spec)
    with pytest.raises(FlowSpecNotReviewed):
        _expand(f)
    assert generator.prompts == []


def test_downstream_execution_persists_raw_results_before_any_grade(tmp_path):
    f = downstream_fixture(tmp_path)
    store, _, _, _, _, judge, ctx = f
    expanded = _expand(f)
    observed = ctx.runners[StageName.EXECUTE](ctx, expanded)
    assert len(store.load_results(ctx.run_id)) == 1
    assert store.load_verdicts(ctx.run_id) == [] and judge.prompts == []
    assert read_json(Path(observed), PipelineBatch).results[0].outcome is Outcome.COMPLETED
    graded = ctx.runners[StageName.GRADE](ctx, observed)
    assert len(store.load_verdicts(ctx.run_id)) == 1 and judge.prompts
    assert read_json(Path(graded), PipelineBatch).verdicts


def test_downstream_approval_refusal_opens_no_sessions(tmp_path, monkeypatch):
    f = downstream_fixture(tmp_path, grant=False)
    ctx = f[-1]
    expanded = _expand(f)
    root = ctx.store.paths.run_dir(ctx.run_id)
    before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    constructors = []
    original = DownstreamSession.__init__

    def construct(self, *args, **kwargs):
        constructors.append(True)
        original(self, *args, **kwargs)

    monkeypatch.setattr(DownstreamSession, "__init__", construct)
    with pytest.raises(LaunchRefused):
        ctx.runners[StageName.EXECUTE](ctx, expanded)
    assert DownstreamSession.instances == []
    assert constructors == [] and ctx.store.load_run(ctx.run_id) is None
    assert ctx.store.load_results(ctx.run_id) == ctx.store.load_verdicts(ctx.run_id) == []
    assert {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()} == before
    assert not ctx.store.paths.pipeline_artifact(ctx.run_id, "execution-progress").exists()


def test_downstream_snapshot_controls_execution_and_report_after_case_edits(tmp_path):
    f = downstream_fixture(tmp_path)
    store, _, _, _, _, _, ctx = f
    expanded = _expand(f)
    batch = read_json(Path(expanded), PipelineBatch)
    original = batch.cases[0]
    altered = original.model_copy(deep=True)
    altered.title = "CHANGED CANONICAL TITLE"
    altered.steps[0].target = "https://demo.test/changed"
    store.update_case(altered)
    observed = ctx.runners[StageName.EXECUTE](ctx, expanded)
    assert DownstreamSession.instances[0].calls == [original.steps[0].target]
    graded = ctx.runners[StageName.GRADE](ctx, observed)
    report = ctx.runners[StageName.REPORT](ctx, graded)
    assert original.title in Path(report).read_text(encoding="utf-8")
    assert "CHANGED CANONICAL TITLE" not in Path(report).read_text(encoding="utf-8")
    assert store.load_run(ctx.run_id).id == ctx.run_id
    assert (Path(report).parent / "report.xlsx").is_file()


def test_downstream_failed_grade_resumes_without_repeating_browser(tmp_path, monkeypatch):
    f = downstream_fixture(tmp_path)
    store, project, _, model, _, judge, ctx = f
    expanded = _expand(f)
    second = _additional_case(expanded, store, "case-ungraded")
    ctx.runners[StageName.INGEST] = lambda *_: model
    ctx.runners[StageName.MODEL] = lambda *_: model
    ctx.runners[StageName.EXPAND] = lambda *_: expanded
    original_grade = stages.grade

    def fail_second(rubric, result, *args, **kwargs):
        if result.case_id == second.id:
            raise RuntimeError("judge failed")
        return original_grade(rubric, result, *args, **kwargs)

    monkeypatch.setattr(stages, "grade", fail_second)
    state = run_or_resume(project, ctx)
    assert state.checkpoint(StageName.EXECUTE).status == "done"
    assert state.checkpoint(StageName.GRADE).status == "failed"
    saved = store.load_verdicts(ctx.run_id)[0]
    spent = len(judge.prompts)
    before = store.paths.pipeline_artifact(ctx.run_id, "execute").read_bytes()
    calls = sum(len(s.calls) for s in DownstreamSession.instances)
    monkeypatch.setattr(stages, "grade", original_grade)
    state = run_or_resume(project, ctx)
    assert state.checkpoint(StageName.REPORT).status == "done"
    verdicts = {v.case_id: v for v in store.load_verdicts(ctx.run_id)}
    assert len(judge.prompts) == spent and verdicts[saved.case_id] == saved
    assert "judge failed" in verdicts[second.id].note
    assert "not repeated" in verdicts[second.id].note
    assert sum(len(s.calls) for s in DownstreamSession.instances) == calls
    assert store.paths.pipeline_artifact(ctx.run_id, "execute").read_bytes() == before


def test_downstream_interrupted_execution_reports_unfinished_without_repeat(tmp_path, monkeypatch):
    f = downstream_fixture(tmp_path)
    store, _, _, _, _, _, ctx = f
    expanded = _expand(f)
    second = _additional_case(expanded, store, "case-interrupted")
    original_save = execution._persist_observation

    def fail_second(ctx, batch, result, video):
        if result.case_id == second.id:
            raise OSError("disk")
        original_save(ctx, batch, result, video)

    monkeypatch.setattr(execution, "_persist_observation", fail_second)
    with pytest.raises(OSError):
        ctx.runners[StageName.EXECUTE](ctx, expanded)
    count = len(DownstreamSession.instances)
    monkeypatch.setattr(execution, "_persist_observation", original_save)
    observed = ctx.runners[StageName.EXECUTE](ctx, expanded)
    batch = read_json(Path(observed), PipelineBatch)
    assert batch.interrupted and batch.results[0].outcome is Outcome.COMPLETED
    assert batch.results[1].outcome is Outcome.NOT_RUN
    assert "interrupted" in batch.results[1].not_run_reason
    assert len(DownstreamSession.instances) == count


def test_downstream_rejects_changed_frozen_input_or_foreign_lineage(tmp_path):
    f = downstream_fixture(tmp_path)
    ctx = f[-1]
    ref = _expand(f)
    batch = read_json(Path(ref), PipelineBatch)
    batch.cases[0].title = "changed snapshot"
    write_json(Path(ref), batch)
    with pytest.raises(ValueError, match="content changed"):
        ctx.runners[StageName.EXECUTE](ctx, ref)
    batch.input_fingerprint = PipelineBatch.fingerprint(batch.flowspec, batch.cases)
    batch.run_id = "foreign-run"
    write_json(Path(ref), batch)
    with pytest.raises(ValueError, match="another run"):
        ctx.runners[StageName.EXECUTE](ctx, ref)
    batch.run_id = ctx.run_id
    batch.video_refs[batch.cases[0].id] = "../outside.webm"
    write_json(Path(ref), batch)
    with pytest.raises(ValueError, match="video evidence"):
        ctx.runners[StageName.EXECUTE](ctx, ref)


def test_downstream_entry_case_uses_wiped_isolated_profile(tmp_path):
    f = downstream_fixture(tmp_path)
    store, project, _, _, _, _, ctx = f
    ref = _expand(f)
    _additional_case(ref, store, "case-entry", target=project.base_url)
    normal = store.paths.profile_dir / "prior-login"
    isolated = ProjectPaths("demo-entry-test", tmp_path).profile_dir / "prior-login"
    for path in (normal, isolated):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("old login", encoding="utf-8")
    ctx.runners[StageName.EXECUTE](ctx, ref)
    sessions = DownstreamSession.instances
    assert len(sessions) == 2 and all(s.closed for s in sessions)
    assert sessions[0].paths.slug == "demo-entry-test" and sessions[0].entry_profile_clean
    assert sessions[0].calls == [project.base_url]
    assert sessions[1].paths.slug == "demo" and normal.exists()


def test_downstream_captured_human_block_survives_model_status_laundering(tmp_path):
    f = downstream_fixture(tmp_path)
    store, project, spec, model, generator, judge, ctx = f
    store.save_flowspec(spec.model_copy(update={"review": Review(status=ReviewStatus.NEEDS_EDIT)}))
    ctx.runners = stages.downstream_runners(project, store, generator=generator, judge=judge)
    store.save_flowspec(spec)
    with pytest.raises(ValueError, match="NEEDS_EDIT"):
        ctx.runners[StageName.EXPAND](ctx, model)
    assert generator.prompts == [] and DownstreamSession.instances == []


def test_downstream_uncertain_generation_never_spends_again(tmp_path, monkeypatch):
    f = downstream_fixture(tmp_path)
    generator, ctx = f[-3], f[-1]
    original = generator.act

    def lose_response(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError("generation response lost")

    monkeypatch.setattr(generator, "act", lose_response)
    with pytest.raises(RuntimeError, match="response lost"):
        _expand(f)
    assert len(generator.prompts) == 1
    monkeypatch.setattr(generator, "act", original)
    with pytest.raises(ValueError, match="new run"):
        _expand(f)
    assert len(generator.prompts) == 1
    assert not ctx.store.paths.pipeline_artifact(ctx.run_id, "expand").exists()


def test_downstream_pre_call_prompt_refusal_remains_retryable(tmp_path, monkeypatch):
    f = downstream_fixture(tmp_path)
    generator, ctx = f[-3], f[-1]
    original = expansion.guard_expand_prompt
    monkeypatch.setattr(expansion, "guard_expand_prompt",
                        lambda *_: (_ for _ in ()).throw(ValueError("prompt refused")))
    with pytest.raises(ValueError, match="prompt refused"):
        _expand(f)
    assert generator.prompts == []
    assert not ctx.store.paths.pipeline_artifact(ctx.run_id, "expansion-attempt").exists()
    monkeypatch.setattr(expansion, "guard_expand_prompt", original)
    assert Path(_expand(f)).is_file() and generator.prompts
