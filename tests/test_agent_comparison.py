"""T-179d: the agent-vs-pipeline comparison (AL12 report, AL13 verdict line), offline.
Both paths are scored by the one bench scorer; the verdict is stated whichever way it went."""

from __future__ import annotations

from pathlib import Path

from autotester.agents import comparison
from autotester.schema.agent_comparison import Comparison
from autotester.schema.bench import BenchCorpus, SeededBug
from autotester.schema.enums import Result, Severity
from autotester.schema.lead_loop import AgentRun
from autotester.schema.verdict import Verdict


def _corpus() -> BenchCorpus:
    bugs = [SeededBug(id=b, description=b, location=f"/{b}", detect_hint=b,
                      severity=Severity.S2, provenance="fixture_seeded") for b in ("b1", "b2")]
    return BenchCorpus(id="fx", app="demo", build_ref="seeded", mode="fixture", seeded_bugs=bugs)


def _fail(case: str) -> Verdict:
    return Verdict(run_id="r", case_id=case, result=Result.FAIL, rubric_hash="h",
                   grader_provider="mock", scoreboard="1/2")


MAP = {"c1": "b1", "c2": "b2"}


def _cmp(pipeline: list[str], agent: list[str], stopped: str = "finished") -> Comparison:
    run_ = AgentRun(run_id="r", stopped=stopped, tokens_used=900)  # type: ignore[arg-type]
    return comparison.compare(_corpus(), MAP, [_fail(c) for c in pipeline],
                              [_fail(c) for c in agent], run_, pipeline_tokens=0,
                              pipeline_wall_s=4.0, agent_wall_s=9.5)


def test_al12_the_report_has_all_four_numbers_for_both_paths(tmp_path: Path) -> None:
    cmp = _cmp(["c1", "cX"], ["c1", "c2"])
    assert (cmp.pipeline.bugs_found, cmp.pipeline.false_positives) == (1, 1)
    assert (cmp.agent.bugs_found, cmp.agent.false_positives) == (2, 0)
    assert (cmp.pipeline.tokens, cmp.agent.tokens, cmp.agent.wall_s) == (0, 900, 9.5)
    out = comparison.write_report(cmp, tmp_path / "cmp.json")
    assert Comparison.model_validate_json(out.read_text(encoding="utf-8")) == cmp


def test_al13_a_gain_is_stated_with_the_numbers() -> None:
    cmp = _cmp(["c1"], ["c1", "c2"])
    assert cmp.verdict == "gain" and cmp.verdict_line.startswith("GAIN")
    assert "2 bugs" in cmp.verdict_line and "1 bugs" in cmp.verdict_line


def test_al13_no_gain_is_recorded_not_hidden() -> None:
    cmp = _cmp(["c1", "c2"], ["c1"])
    assert cmp.verdict == "no_gain" and cmp.verdict_line.startswith("NO GAIN")
    assert "did worse" in cmp.verdict_line and "tokens" in cmp.verdict_line
    assert _cmp(["c1"], ["c1"]).verdict == "no_gain"  # a tie is not a gain


def test_al13_a_gain_that_breached_the_budget_is_not_a_gain() -> None:
    cmp = _cmp(["c1"], ["c1", "c2"], stopped="budget_exceeded")
    assert cmp.verdict == "no_gain" and "breached its budget" in cmp.verdict_line
