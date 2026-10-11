"""T-167 release regression (`qa/contracts/release-regression.md` RR1-RR6). Offline, fixture-only:
scripted execute/grade runners, the real `grade()` on a seeded `MockProvider`, a signed fixture
`RunApproval`. RR1 re-proves OR2/OR4 on the LangGraph checkpointer (not the `state.json` view).
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

import pytest
from run_approval_fixture import grant_live_case_approval

from autotester import doctor
from autotester.core.consent import ApprovalRequired
from autotester.providers.mock import MockProvider
from autotester.schema.enums import EvidenceKind, Outcome, Result, SourceKind
from autotester.schema.flowspec import Flow, FlowSpec
from autotester.schema.project import Project, Source
from autotester.schema.release import FlowPlan, ReleaseDecision
from autotester.schema.run import Evidence, RawResult
from autotester.schema.run_state import StageName
from autotester.schema.verdict import Criterion, Failure, Judgment, Rubric
from autotester.stages import orchestrate, release, release_compare
from autotester.stages.grade import grade
from autotester.stages.orchestrate import StageContext, run_or_resume
from autotester.stages.release import start_release
from autotester.stages.release_compare import flag_bad
from autotester.store.project_store import ProjectStore

PROJECT = Project(slug="demo", name="Demo", base_url="https://demo.test",
                  allowed_domains=["demo.test"])
RUBRIC = Rubric(id="rub", criteria=[Criterion(id="c1", text="the flow works")])
YES = ReleaseDecision(approved=True, by="release-manager")


def _store(tmp_path: Path, *, approve: bool = True, flows: tuple[str, ...] = ()) -> ProjectStore:
    store = ProjectStore("demo", tmp_path)
    store.save_project(PROJECT)
    if flows:
        store.save_flowspec(FlowSpec(project="demo", flows=[
            Flow(id=f, name=f, entry_screen="home") for f in flows]))
        for flow in flows:
            store.save_flow_plan(FlowPlan(project="demo", flow_id=flow, case_ids=[f"c-{flow}"]))
    if approve:
        grant_live_case_approval(store)
    return store


def _runners(store: ProjectStore, outcome: dict[str, Result], calls: list[str] | None = None):
    """EXECUTE saves a raw result per case; GRADE runs the real `grade()` on a seeded judge."""

    def execute(ctx: StageContext, prev: str | None) -> str:
        for case_id in ctx.release_scope.case_ids:
            if calls is not None:
                calls.append(case_id)
            store.save_result(ctx.run_id, RawResult(case_id=case_id, outcome=Outcome.COMPLETED,
                evidence=[Evidence(kind=EvidenceKind.URL, path="u", step_order=1)]))
        return "executed"

    def judged(case_id: str) -> Judgment:
        if outcome[case_id] is Result.PASS:
            return Judgment(result=Result.PASS, scoreboard="1/1", criteria_met=1, criteria_total=1)
        return Judgment(result=Result.FAIL, scoreboard="0/1", criteria_total=1, failures=[
            Failure(criterion_id="c1", reason="broken", evidence_refs=["u"])])

    def run_grade(ctx: StageContext, prev: str | None) -> str:
        judge = MockProvider(responses={"judge": [judged(r.case_id) for r in
                                                  store.load_results(ctx.run_id)]})
        for raw in store.load_results(ctx.run_id):
            store.save_verdict(ctx.run_id, grade(RUBRIC, raw, ctx.run_id, judge))
        return "graded"

    return {StageName.EXECUTE: execute, StageName.GRADE: run_grade}


def _release(store, run_id, outcome, day=1):
    when = datetime(2026, 10, day, tzinfo=UTC)
    runners = _runners(store, outcome)
    paused = start_release(PROJECT, store, run_id=run_id, runners=runners, created_at=when)
    assert paused.checkpoint(StageName.CONFIRM).status == "awaiting_human"
    return start_release(PROJECT, store, run_id=run_id, runners=runners, decision=YES)


PASS, FAIL = Result.PASS, Result.FAIL
ALL = ("f1", "f2", "f3")


def _outcome(**cases: Result) -> dict[str, Result]:
    return {f"c-{k}": v for k, v in cases.items()}


# -- RR1: LangGraph conversion in place; OR2 / OR4 hold on the checkpointer ------------------

class _Rec:
    def __init__(self, path: Path, fail_times: int = 0) -> None:
        self.calls, self.fail_times, self.path = 0, fail_times, path

    def __call__(self, ctx: StageContext, prev: str | None) -> str:
        self.calls += 1
        if self.calls <= self.fail_times:
            raise RuntimeError("boom")
        self.path.write_text(str(self.calls), encoding="utf-8")
        return str(self.path)


def _learn(tmp_path: Path, rec: _Rec) -> tuple[StageContext, ProjectStore]:
    store = _store(tmp_path, approve=False)
    store.add_source(Source(project="demo", kind=SourceKind.VIDEO, path="/t/a.mp4", sha256="s"))
    return StageContext(store=store, run_id="r1", runners={StageName.INGEST: rec}), store


def test_rr1_is_an_in_place_conversion_not_a_second_orchestrator() -> None:
    root = Path(orchestrate.__file__).parents[1]
    owners = [p.name for p in root.rglob("*.py") if "def run_or_resume" in p.read_text("utf-8")]
    assert owners == ["orchestrate.py"]
    assert "StateGraph(" in Path(orchestrate.__file__).read_text("utf-8")


def test_rr1_a_done_stage_is_not_redone_when_the_checkpointer_is_the_only_record(
        tmp_path: Path) -> None:
    rec = _Rec(tmp_path / "ingest.txt")
    ctx, store = _learn(tmp_path, rec)
    run_or_resume(PROJECT, ctx)
    run_dir = store.paths.run_dir("r1")
    assert (run_dir / "checkpoint.json").exists()
    (run_dir / "state.json").unlink()  # the projection is gone; only LangGraph remembers
    again = run_or_resume(PROJECT, ctx)
    assert rec.calls == 1 and rec.path.read_text("utf-8") == "1"
    assert again.checkpoint(StageName.INGEST).status == "done"


def test_rr1_a_raise_is_failed_and_resume_re_enters_that_stage(tmp_path: Path) -> None:
    rec = _Rec(tmp_path / "ingest.txt", fail_times=1)
    ctx, store = _learn(tmp_path, rec)
    first = run_or_resume(PROJECT, ctx)
    failed = first.checkpoint(StageName.INGEST)
    assert failed.status == "failed" and "boom" in failed.error and failed.artifact_ref is None
    assert first.next_pending().stage is StageName.INGEST
    (store.paths.run_dir("r1") / "state.json").unlink()
    second = run_or_resume(PROJECT, ctx)
    assert rec.calls == 2 and second.checkpoint(StageName.INGEST).status == "done"


# -- RR2: interrupt() layers on RunApproval -------------------------------------------------

def test_rr2_no_approval_is_refused_before_the_graph_or_any_directory(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = _store(tmp_path, approve=False, flows=ALL)
    calls: list[str] = []

    def never(*_a, **_k):
        raise AssertionError("the graph was built for an unapproved release")

    monkeypatch.setattr(orchestrate, "_compile", never)
    with pytest.raises(ApprovalRequired):
        start_release(PROJECT, store, run_id="rel", runners=_runners(store, {}, calls))
    assert not store.paths.run_dir("rel").exists() and calls == []


def test_rr2_a_forged_scope_cannot_skip_the_gate_through_run_or_resume(tmp_path: Path) -> None:
    store = _store(tmp_path, flows=ALL)
    scope = release.build_scope(PROJECT, store, run_id="rel", approval_id="appr_nope",
                                max_actions=3)
    ctx = StageContext(store=store, run_id="rel", release_scope=scope)
    with pytest.raises(ApprovalRequired):
        run_or_resume(PROJECT, ctx)
    assert not store.paths.run_dir("rel").exists()


def test_rr2_an_approval_narrower_than_the_release_is_refused(tmp_path: Path) -> None:
    store = _store(tmp_path, approve=False, flows=ALL)
    grant_live_case_approval(store, max_actions=1)
    with pytest.raises(ApprovalRequired, match="narrower"):
        start_release(PROJECT, store, run_id="rel", runners={})
    assert not store.paths.run_dir("rel").exists()


def test_rr2_an_approved_release_pauses_and_a_resume_without_a_human_never_proceeds(
        tmp_path: Path) -> None:
    store = _store(tmp_path, flows=ALL)
    calls: list[str] = []
    runners = _runners(store, _outcome(f1=PASS, f2=PASS, f3=PASS), calls)
    paused = start_release(PROJECT, store, run_id="rel", runners=runners)
    assert paused.checkpoint(StageName.CONFIRM).status == "awaiting_human"
    for _ in range(2):  # resuming without an answer is still paused
        again = start_release(PROJECT, store, run_id="rel", runners=runners)
        assert again.checkpoint(StageName.CONFIRM).status == "awaiting_human"
        assert again.checkpoint(StageName.EXECUTE).status == "pending" and calls == []
    done = start_release(PROJECT, store, run_id="rel", runners=runners, decision=YES)
    assert done.next_pending() is None and sorted(calls) == ["c-f1", "c-f2", "c-f3"]


def test_rr2_a_declined_release_runs_nothing(tmp_path: Path) -> None:
    store = _store(tmp_path, flows=ALL)
    calls: list[str] = []
    runners = _runners(store, {}, calls)
    start_release(PROJECT, store, run_id="rel", runners=runners)
    no = ReleaseDecision(approved=False, by="release-manager")
    state = start_release(PROJECT, store, run_id="rel", runners=runners, decision=no)
    assert calls == [] and state.checkpoint(StageName.EXECUTE).status == "skipped"
    assert store.load_release_record("rel") is None


# -- RR3: ONE named baseline rule ----------------------------------------------------------

def _good_bad_good(tmp_path: Path) -> ProjectStore:
    store = _store(tmp_path, flows=ALL)
    _release(store, "run1", _outcome(f1=PASS, f2=PASS, f3=PASS), day=1)
    _release(store, "run2", _outcome(f1=FAIL, f2=FAIL, f3=PASS), day=2)
    _release(store, "run3", _outcome(f1=PASS, f2=FAIL, f3=PASS), day=3)
    return store


def test_rr3_the_third_run_diffs_against_the_first_good_run_not_the_prior_one(
        tmp_path: Path) -> None:
    store = _good_bad_good(tmp_path)
    one, two, three = (store.load_release_record(r) for r in ("run1", "run2", "run3"))
    assert one.is_trusted and not two.is_trusted and not three.is_trusted
    assert three.diff.baseline_run_id == "run1"
    assert three.diff.baseline_rule == release_compare.BASELINE_RULE
    # "whatever ran last" (run2) would have hidden this: c-f2 failed in run2 too.
    assert three.diff.regressed == ["c-f2"] and three.diff.fixed == []
    assert two.diff.regressed == ["c-f1", "c-f2"]


def test_rr3_the_first_release_has_no_baseline_and_says_so(tmp_path: Path) -> None:
    store = _store(tmp_path, flows=ALL)
    _release(store, "run1", _outcome(f1=PASS, f2=PASS, f3=PASS))
    diff = store.load_release_record("run1").diff
    assert diff.baseline_run_id is None and "no trusted baseline" in diff.note
    assert diff.regressed == [] and diff.fixed == []


def test_rr3_a_human_flagged_release_is_never_a_baseline(tmp_path: Path) -> None:
    store = _store(tmp_path, flows=ALL)
    _release(store, "run1", _outcome(f1=PASS, f2=PASS, f3=PASS), day=1)
    flag_bad(store, "run1", "shipped a broken checkout")
    _release(store, "run2", _outcome(f1=PASS, f2=PASS, f3=PASS), day=2)
    assert store.load_release_record("run2").diff.baseline_run_id is None


def test_rr3_a_release_with_an_unrun_flow_is_never_a_baseline(tmp_path: Path) -> None:
    store = _store(tmp_path, flows=ALL)
    (store.paths.flow_plans).write_text("", encoding="utf-8")  # no plans: every flow `not run`
    _release(store, "run1", {}, day=1)
    assert not store.load_release_record("run1").is_trusted


@pytest.mark.parametrize("module", [release, release_compare])
def test_rr4_release_modules_construct_no_verdict_and_do_not_import_the_grader(module) -> None:
    text = Path(module.__file__).read_text("utf-8")
    assert not re.search(r"Result\.|Verdict\(", text)
    assert not re.search(r"stages\.grade|import grade|\bgrade\(", text)


def test_rr4_every_result_in_the_record_is_what_the_grader_returned(tmp_path: Path) -> None:
    store = _store(tmp_path, flows=ALL)
    _release(store, "rel", _outcome(f1=PASS, f2=FAIL, f3=PASS))
    verdicts = {v.case_id: v for v in store.load_verdicts("rel")}
    record = store.load_release_record("rel")
    assert record.results == {c: v.result for c, v in verdicts.items()} and len(verdicts) == 3
    assert {v.grader_provider for v in verdicts.values()} == {"mock"}  # from the judge call
    (issue,) = record.issues
    assert issue.detail == verdicts["c-f2"].scoreboard  # copied from the verdict, not decided


def test_rr5_langgraph_is_declared_and_doctor_finds_no_undeclared_import() -> None:
    root = doctor.repo_root()
    lines = [x for x in (root / "pyproject.toml").read_text("utf-8").splitlines()
             if "langgraph" in x]
    assert lines and lines[0].strip().startswith('"langgraph==')
    assert doctor.check_dependencies_declared(root) == []


# -- RR6: per-flow plans stitch into ONE release and ONE issues log --------------------------

def test_rr6_one_run_one_log_names_both_failures_and_passes_the_third(tmp_path: Path) -> None:
    store = _store(tmp_path, flows=ALL)
    _release(store, "rel", _outcome(f1=FAIL, f2=PASS, f3=FAIL))
    record = store.load_release_record("rel")
    assert record.finished and len(list(store.paths.run_dir("rel").glob("release*.json"))) == 1
    assert sorted((i.flow_id, i.case_id) for i in record.issues) == [
        ("f1", "c-f1"), ("f3", "c-f3")]
    assert {f.flow_id: f.status for f in record.flows} == {
        "f1": "failed", "f2": "passed", "f3": "failed"}


def test_rr6_a_flow_without_a_plan_is_reported_not_run_never_omitted(tmp_path: Path) -> None:
    store = _store(tmp_path, flows=ALL)
    keep = [p for p in store.list_flow_plans() if p.flow_id != "f3"]
    store.paths.flow_plans.write_text("".join(p.model_dump_json() + "\n" for p in keep), "utf-8")
    _release(store, "rel", _outcome(f1=PASS, f2=PASS))
    record = store.load_release_record("rel")
    assert {f.flow_id: f.status for f in record.flows}["f3"] == "not_run"
    assert [(i.flow_id, i.kind) for i in record.issues] == [("f3", "not_run")]
    assert not record.is_trusted
