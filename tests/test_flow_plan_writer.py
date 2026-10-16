"""AT-898 / RR6: a completed flow's plan is produced, saved, loaded and consumed by a release."""

from pathlib import Path

from downstream_fixture import downstream_fixture
from run_approval_fixture import grant_live_case_approval
from test_regression_trigger import PASS, PROJECT, YES, _runners

from autotester.schema.run_state import PipelineBatch, StageName
from autotester.stages.flow_plan import plans_from_batch
from autotester.stages.release import start_release
from autotester.store.filestore import read_json


def _report(tmp_path):
    f = downstream_fixture(tmp_path)
    store, *_, ctx = f
    expanded = ctx.runners[StageName.EXPAND](ctx, f[3])
    graded = ctx.runners[StageName.GRADE](ctx, ctx.runners[StageName.EXECUTE](ctx, expanded))
    ctx.runners[StageName.REPORT](ctx, graded)
    return store, graded


def test_report_stage_persists_a_plan_per_completed_flow_and_release_runs_it(tmp_path):
    store, graded = _report(tmp_path)
    batch = read_json(Path(graded), PipelineBatch)
    plans = store.list_flow_plans()
    assert [p.flow_id for p in plans] == ["flow-home"]
    assert plans[0].case_ids == [c.id for c in batch.cases]

    store.save_flowspec(read_json(Path(graded), PipelineBatch).flowspec)  # the reviewed MODEL
    grant_live_case_approval(store)
    runners = _runners(store, {cid: PASS for cid in plans[0].case_ids})
    paused = start_release(PROJECT, store, run_id="rel", runners=runners)
    scope = store.load_release_scope("rel")
    assert scope.unplanned_flow_ids == [] and scope.case_ids == plans[0].case_ids
    assert paused.checkpoint(StageName.CONFIRM).status == "awaiting_human"
    done = start_release(PROJECT, store, run_id="rel", runners=runners, decision=YES)
    assert done.next_pending() is None


def test_incomplete_flow_gets_no_plan(tmp_path):
    _store, graded = _report(tmp_path)
    batch = read_json(Path(graded), PipelineBatch)
    batch.verdicts = []
    assert plans_from_batch(batch) == []
