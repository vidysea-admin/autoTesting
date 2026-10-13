"""Contract: qa/contracts/bench.md K6-K9 + D-089 item 3 (no-human-list mode).

Fixtures only: no browser, no network."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from autotester.schema.acceptance import Measure
from autotester.schema.bench import BenchCorpus, BenchTrial, Finding, SeededBug
from autotester.schema.enums import Participant, Severity
from autotester.stages.acceptance_comparison import (
    MissingInput,
    build_comparison,
    completeness_problems,
)
from autotester.store.project_store import ProjectStore

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_acceptance_comparison.py"
CORPUS_ID = "demo-acceptance"


def _cli():
    spec = importlib.util.spec_from_file_location("check_acceptance_comparison", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _ai(duration: float | None = 12.0, ordering: str = "independent_parallel") -> BenchTrial:
    return BenchTrial(
        id="t_ai", corpus_id=CORPUS_ID, participant=Participant.AUTOTESTER,
        participant_label="autotester-real-run", kind="autotester", ordering=ordering,
        duration_s=duration,
        findings=[Finding(text="a"), Finding(text="b", matched_bug_id="b1")],
    )


def _seed(root: Path, *, corpus: BenchCorpus | None, trials: list[BenchTrial]) -> ProjectStore:
    store = ProjectStore("demo", root)
    if corpus:
        store.save_bench_corpus(corpus)
    for trial in trials:
        store.save_bench_trial(trial)
    return store


def _no_list_corpus() -> BenchCorpus:
    return BenchCorpus(id=CORPUS_ID, app="demo", build_ref="b")


def _human_corpus() -> BenchCorpus:
    bug = SeededBug(id="b1", description="d", location="/x", detect_hint="h",
                    severity=Severity.S1, provenance="human_independent")
    return BenchCorpus(id=CORPUS_ID, app="demo", build_ref="b", mode="human_confirmed",
                       seeded_bugs=[bug])


def _human(kind: str = "human_live", ordering: str = "independent_parallel",
           provenance: str = "independent") -> BenchTrial:
    return BenchTrial(
        id="t_hu", corpus_id=CORPUS_ID, participant=Participant.HUMAN, kind=kind,
        ordering=ordering, participant_label="umesh", duration_s=600.0,
        findings=[Finding(text="x", matched_bug_id="b1", provenance=provenance)],
    )


def test_no_human_list_is_a_supported_mode_with_recall_unavailable(tmp_path: Path) -> None:
    store = _seed(tmp_path, corpus=_no_list_corpus(), trials=[_ai()])
    cmp = build_comparison(store, "demo")
    assert cmp.human_list == "absent"
    assert cmp.human.absent_reason == "no human list"
    assert cmp.autotester.severity_weighted_recall.value is None
    assert cmp.autotester.severity_weighted_recall.unavailable_reason == "no human list"
    # BenchTrial.score counts a finding matching no corpus bug as a false positive; with an
    # empty corpus bug list that is every finding, so the number is scorer-verbatim.
    assert cmp.autotester.false_positive_rate.value == pytest.approx(1.0)
    assert cmp.autotester.duration_s.value == 12.0
    assert cmp.bugs_unavailable_reason == "no ground-truth bug list"
    assert completeness_problems(cmp) == []


def test_untimed_autotester_is_incomplete_never_zero(tmp_path: Path) -> None:
    store = _seed(tmp_path, corpus=_no_list_corpus(), trials=[_ai(duration=None)])
    cmp = build_comparison(store, "demo")
    assert cmp.autotester.duration_s.value is None
    assert any("duration_s" in p for p in completeness_problems(cmp))


def test_no_findings_means_fp_rate_unavailable_and_incomplete(tmp_path: Path) -> None:
    trial = _ai().model_copy(update={"findings": []})
    cmp = build_comparison(_seed(tmp_path, corpus=_no_list_corpus(), trials=[trial]), "demo")
    assert cmp.autotester.false_positive_rate.value is None
    assert any("false_positive_rate" in p for p in completeness_problems(cmp))


def test_unrecorded_ordering_is_flagged(tmp_path: Path) -> None:
    store = _seed(tmp_path, corpus=_no_list_corpus(), trials=[_ai(ordering="unknown")])
    assert any("ordering" in p for p in completeness_problems(build_comparison(store, "demo")))


def test_human_list_plugs_in_as_files_with_no_code_change(tmp_path: Path) -> None:
    store = _seed(tmp_path, corpus=_human_corpus(), trials=[_ai(), _human()])
    cmp = build_comparison(store, "demo")
    assert cmp.human_list == "present"
    assert cmp.human.kind == "human_live" and cmp.human.independent_findings == 1
    assert cmp.human.severity_weighted_recall.value == 1.0
    assert cmp.autotester.severity_weighted_recall.value == 1.0
    assert [r.found_by for r in cmp.bugs] == [["autotester", "human"]]
    assert completeness_problems(cmp) == []
    assert store.paths.bench_human_trial(CORPUS_ID).name.endswith(".trial.json")


def test_prompted_human_recall_is_unavailable_not_credited(tmp_path: Path) -> None:
    human = _human(ordering="human_read_ai_first", provenance="prompted")
    cmp = build_comparison(_seed(tmp_path, corpus=_human_corpus(), trials=[_ai(), human]), "demo")
    assert cmp.human.prompted_findings == 1
    assert cmp.human.independent_findings == 0
    assert cmp.human.detected == 0  # a prompted finding never counts toward recall (K7)
    assert cmp.bugs[0].found_by == ["autotester"] or "human" in cmp.bugs[0].found_by


def test_human_with_unknown_kind_fails_k6(tmp_path: Path) -> None:
    human = _human(kind="unknown", ordering="unknown")
    cmp = build_comparison(_seed(tmp_path, corpus=_human_corpus(), trials=[_ai(), human]), "demo")
    problems = completeness_problems(cmp)
    assert any("K6" in p for p in problems) and any("K7" in p for p in problems)


def test_missing_corpus_and_missing_trial_name_what_is_absent(tmp_path: Path) -> None:
    with pytest.raises(MissingInput, match="bench corpus"):
        build_comparison(_seed(tmp_path, corpus=None, trials=[]), "demo")
    with pytest.raises(MissingInput, match="AutoTester bench trial"):
        build_comparison(_seed(tmp_path, corpus=_no_list_corpus(), trials=[]), "demo")


def test_measure_is_a_value_or_a_reason_never_both_or_neither() -> None:
    with pytest.raises(ValueError):
        Measure()
    with pytest.raises(ValueError):
        Measure(value=0.0, unavailable_reason="x")


def test_cli_exit_codes_and_artifact(tmp_path: Path, capsys) -> None:
    cli = _cli()
    assert cli.main(["demo", "--root", str(tmp_path)]) == 2
    assert "missing bench corpus" in capsys.readouterr().err
    store = _seed(tmp_path, corpus=_no_list_corpus(), trials=[_ai()])
    assert cli.main(["demo", "--root", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "unavailable (no human list)" in out
    saved = json.loads(store.paths.bench_comparison(CORPUS_ID).read_text(encoding="utf-8"))
    assert saved["human_list"] == "absent" and "Umesh" in saved["verdict"]
    store.save_bench_trial(_ai(duration=None))
    assert cli.main(["demo", "--root", str(tmp_path)]) == 1
