"""Contract: qa/contracts/bench.md K10 (+K8). Fixture runs only; no browser, no judge."""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from autotester.schema.bench import BenchCorpus, SeededBug
from autotester.schema.enums import Result, Severity
from autotester.schema.run import Run
from autotester.schema.verdict import Failure, Verdict
from autotester.stages.acceptance_comparison import build_comparison, completeness_problems
from autotester.stages.bench_from_run import RunNotUsable, bench_from_run
from autotester.store.project_store import ProjectStore

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import bench_from_run as script
import check_acceptance_comparison as check


def _verdict(case_id: str, result: Result) -> Verdict:
    fails = [Failure(criterion_id="c1", reason="broke")] if result is Result.FAIL else []
    return Verdict(run_id="run_1", case_id=case_id, result=result, failures=fails)


def _seed(tmp_path: Path, *, timed: bool = True, graded: bool = True) -> ProjectStore:
    store = ProjectStore("demo", tmp_path)
    t0 = datetime(2026, 10, 13, tzinfo=UTC)
    store.save_run(Run(
        id="run_1", project="demo", case_ids=["a", "b"],
        started_at=t0 if timed else None,
        finished_at=t0 + timedelta(seconds=42) if timed else None,
    ))
    store.save_verdict("run_1", _verdict("a", Result.FAIL))
    if graded:
        store.save_verdict("run_1", _verdict("b", Result.PASS))
    return store


def test_no_list_mode_builds_corpus_and_trial_and_check_exits_zero(tmp_path: Path) -> None:
    store = _seed(tmp_path)
    trial = bench_from_run(store, "demo", "run_1")
    assert trial.kind == "autotester" and trial.duration_s == 42.0
    assert [f.matched_bug_id for f in trial.findings] == [None]  # unadjudicated
    corpus = store.load_bench_corpus("demo-acceptance")
    assert corpus is not None and corpus.mode == "unknown" and corpus.seeded_bugs == []
    cmp = build_comparison(store, "demo")
    assert completeness_problems(cmp) == []
    assert cmp.human_list == "absent" and cmp.fp_rate_unadjudicated
    assert cmp.autotester.severity_weighted_recall.value is None  # unavailable, never 0.0
    assert cmp.autotester.false_positive_rate.value == 1.0
    assert check.main(["demo", "--root", str(tmp_path)]) == 0


def test_script_main_writes_trial_file_where_comparison_expects(tmp_path: Path) -> None:
    _seed(tmp_path)
    assert script.main(["demo", "--run", "run_1", "--root", str(tmp_path)]) == 0
    store = ProjectStore("demo", tmp_path)
    assert store.paths.bench_trial("demo-acceptance-autotester").exists()
    assert script.main(["demo", "--run", "nope", "--root", str(tmp_path)]) == 2


def test_rerun_replaces_trial_not_duplicates(tmp_path: Path) -> None:
    store = _seed(tmp_path)
    bench_from_run(store, "demo", "run_1")
    bench_from_run(store, "demo", "run_1")
    assert len(store.list_bench_trials("demo-acceptance")) == 1


def test_human_corpus_present_is_used_and_not_overwritten(tmp_path: Path) -> None:
    store = _seed(tmp_path)
    human = BenchCorpus(
        id="demo-acceptance", app="demo", build_ref="b", mode="human_confirmed",
        seeded_bugs=[SeededBug(id="bug1", description="d", location="/x", detect_hint="h",
                               severity=Severity.S1, provenance="human_independent")],
    )
    store.save_bench_corpus(human)
    trial = bench_from_run(store, "demo", "run_1", {"a": "bug1"})
    assert store.load_bench_corpus("demo-acceptance") == human
    assert trial.findings[0].matched_bug_id == "bug1"
    assert trial.score(human)["detected"] == 1


def test_untimed_run_without_results_has_unavailable_duration(tmp_path: Path) -> None:
    store = _seed(tmp_path, timed=False)
    trial = bench_from_run(store, "demo", "run_1")
    assert trial.duration_s is None
    assert any("duration_s" in p for p in completeness_problems(build_comparison(store, "demo")))


def test_ungraded_or_missing_run_refused(tmp_path: Path) -> None:
    store = _seed(tmp_path, graded=False)
    with pytest.raises(RunNotUsable, match="not fully graded"):
        bench_from_run(store, "demo", "run_1")
    with pytest.raises(RunNotUsable, match="not found"):
        bench_from_run(store, "demo", "missing")
    assert store.load_bench_corpus("demo-acceptance") is None  # nothing written on refusal
