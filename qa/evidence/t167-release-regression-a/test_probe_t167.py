"""Checker A throwaway probes (scratch copy only)."""
import json
from datetime import UTC, datetime
from pathlib import Path
import pytest
from langgraph.graph.state import CompiledStateGraph
from test_regression_trigger import (PROJECT, YES, ALL, PASS, _store, _runners, _outcome, _Rec, _learn)
from run_approval_fixture import grant_live_case_approval
from autotester.core.consent import ApprovalRequired
from autotester.schema.run_state import RunState, StageName, StageCheckpoint
from autotester.schema.enums import SourceKind
from autotester.schema.project import Source
from autotester.stages import release
from autotester.stages.orchestrate import StageContext, run_or_resume
from autotester.stages.release import start_release


def test_p1_forged_scope_graph_never_invoked(tmp_path, monkeypatch):
    store = _store(tmp_path, flows=ALL)
    invoked = []
    real = CompiledStateGraph.invoke
    monkeypatch.setattr(CompiledStateGraph, "invoke", lambda self, *a, **k: invoked.append(1) or real(self, *a, **k))
    calls = []
    scope = release.build_scope(PROJECT, store, run_id="rel", approval_id="appr_nope", max_actions=3)
    ctx = StageContext(store=store, run_id="rel", release_scope=scope, runners=_runners(store, {}, calls))
    with pytest.raises(ApprovalRequired):
        run_or_resume(PROJECT, ctx)
    assert invoked == [] and calls == [] and not store.paths.run_dir("rel").exists()


def test_p2_revoked_approval_blocks_the_resume_after_pause(tmp_path):
    store = _store(tmp_path, flows=ALL)
    calls = []
    runners = _runners(store, _outcome(f1=PASS, f2=PASS, f3=PASS), calls)
    paused = start_release(PROJECT, store, run_id="rel", runners=runners)
    assert paused.checkpoint(StageName.CONFIRM).status == "awaiting_human"
    appr = store.paths.dir / "approvals.jsonl"
    appr.write_text("", encoding="utf-8")  # approval withdrawn between pause and answer
    with pytest.raises(ApprovalRequired):
        start_release(PROJECT, store, run_id="rel", runners=runners, decision=YES)
    assert calls == []


def test_p3_old_format_state_json_resumes_without_redo(tmp_path):
    rec_ing, rec_model = _Rec(tmp_path / "i.txt"), _Rec(tmp_path / "m.txt")
    store = _store(tmp_path, approve=False)
    store.add_source(Source(project="demo", kind=SourceKind.VIDEO, path="/t/a.mp4", sha256="s"))
    now = datetime(2026, 9, 1, tzinfo=UTC)
    old = RunState(run_id="old", project_slug="demo", mode="learn", mode_reason="r", created=now, updated=now,
        stages=[StageCheckpoint(stage=s) for s in (StageName.INGEST, StageName.MODEL, StageName.EXPAND, StageName.EXECUTE, StageName.GRADE, StageName.REPORT)])
    old.stages[0] = old.stages[0].model_copy(update={"status": "done", "artifact_ref": "ing-ref", "finished": now})
    d = json.loads(old.model_dump_json(exclude={"scope_fingerprint", "release_decision"}))
    assert "scope_fingerprint" not in d
    sp = store.paths.run_dir("old") / "state.json"
    sp.parent.mkdir(parents=True); sp.write_text(json.dumps(d), encoding="utf-8")
    ctx = StageContext(store=store, run_id="old", runners={StageName.INGEST: rec_ing, StageName.MODEL: rec_model})
    out = run_or_resume(PROJECT, ctx)
    assert rec_ing.calls == 0 and rec_model.calls == 1
    assert out.checkpoint(StageName.INGEST).artifact_ref == "ing-ref" and out.checkpoint(StageName.MODEL).status == "done"


def test_p4_corrupt_or_foreign_checkpoint_is_refused_loudly(tmp_path):
    rec = _Rec(tmp_path / "i.txt")
    ctx, store = _learn(tmp_path, rec)
    run_or_resume(PROJECT, ctx)
    cp = store.paths.run_dir("r1") / "checkpoint.json"
    good = cp.read_text("utf-8")
    cp.write_text(good[:-20], encoding="utf-8")
    with pytest.raises(Exception):
        run_or_resume(PROJECT, ctx)
    env = json.loads(good); env["thread_id"] = "other:r9"
    cp.write_text(json.dumps(env), encoding="utf-8")
    with pytest.raises(ValueError):
        run_or_resume(PROJECT, ctx)
    cp.write_text(good, encoding="utf-8")
    run_or_resume(PROJECT, ctx)
    assert rec.calls == 1


def test_p5_release_ledger_without_scope_is_refused(tmp_path):
    store = _store(tmp_path, flows=ALL)
    calls = []
    runners = _runners(store, _outcome(f1=PASS, f2=PASS, f3=PASS), calls)
    start_release(PROJECT, store, run_id="rel", runners=runners)
    ctx = StageContext(store=store, run_id="rel", runners=runners)  # no release_scope
    with pytest.raises(ApprovalRequired):
        run_or_resume(PROJECT, ctx)
    assert calls == []


def test_p6_scope_that_understates_its_plan_cost_passes_the_gate(tmp_path):
    store = _store(tmp_path, approve=False, flows=ALL)
    grant_live_case_approval(store, max_actions=1)  # covers 1 action only
    calls = []
    scope = release.build_scope(PROJECT, store, run_id="rel", approval_id=store.list_approvals()[0].id, max_actions=1)
    assert len(scope.case_ids) == 3
    runners = _runners(store, _outcome(f1=PASS, f2=PASS, f3=PASS), calls)
    from autotester.stages.release_compare import make_compare_runner, make_report_runner
    wired = {**runners, StageName.COMPARE: make_compare_runner(), StageName.REPORT: make_report_runner()}
    ctx = StageContext(store=store, run_id="rel", runners=wired, release_scope=scope)
    run_or_resume(PROJECT, ctx)
    ctx2 = StageContext(store=store, run_id="rel", runners=wired, release_scope=scope, decision=YES)
    run_or_resume(PROJECT, ctx2)
    assert len(calls) == 3  # 3 cases executed under an approval for 1 action
