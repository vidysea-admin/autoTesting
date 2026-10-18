"""Contract: qa/contracts/multi-role-platform.md MP29, MP30 and MPI6 (T-218, build leg).

Fixtures are synthetic and blind (MPI2): six ids over three priorities, no real finding."""

from __future__ import annotations

import ast
import io
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from autotester.schema.bench import BenchCorpus, BenchTrial, Finding, SeededBug
from autotester.schema.ceo_inputs import (
    AtomicFinding,
    AtomicList,
    CeoRunInput,
    OrderingRecord,
    RunFinding,
    ScenarioLabel,
    Technique,
)
from autotester.schema.enums import Participant, Severity
from autotester.schema.multi_role_enums import OracleName, Priority
from autotester.schema.oracle_context import OracleRunSummary, OracleState, OracleStatus
from autotester.stages import bench, ceo_benchmark, oracle_registry
from autotester.stages.ceo_benchmark import (
    TECHNIQUE_OWNERS,
    build_scorecard,
    print_scorecard,
    render_scorecard,
)

SHA = "ab" * 32
T0 = datetime(2026, 10, 18, 9, 0, tzinfo=UTC)
ITEMS = [
    ("CEO-ATOM-001", Priority.P0, Technique.CROSS_TENANT, False),
    ("CEO-ATOM-002", Priority.P1, Technique.API_ERROR, False),
    ("CEO-ATOM-003", Priority.P1, Technique.INBOX, False),
    ("CEO-ATOM-004", Priority.P1, Technique.PAYMENT, True),
    ("CEO-ATOM-005", Priority.P2, Technique.COPY_BRANDING, False),
    ("CEO-ATOM-006", Priority.P2, Technique.RESPONSIVE, False),
]


def atomic() -> AtomicList:
    return AtomicList(items=[AtomicFinding(id=i, priority=p, technique=t, needs_seeded_data=s)
                             for i, p, t, s in ITEMS])


def good_ordering(**over) -> OrderingRecord:
    fields = {"list_sha256": SHA, "committed_at": T0, "run_started_at": T0 + timedelta(hours=2)}
    return OrderingRecord(**{**fields, **over})


def run_input(**over) -> CeoRunInput:
    """3 matches (001, 002, 005), 1 adjudicated FP, 1 unadjudicated -- the MP29 Verify set."""
    fields = {
        "atomic": atomic(), "atomic_sha256": SHA, "ordering": good_ordering(),
        "findings": [
            RunFinding(id="run-f1", matched_atomic_id="CEO-ATOM-001"),
            RunFinding(id="run-f2", matched_atomic_id="CEO-ATOM-002"),
            RunFinding(id="run-f3", matched_atomic_id="CEO-ATOM-005"),
            RunFinding(id="run-f4", adjudication="false_positive"),
            RunFinding(id="run-f5"),
        ],
        "runner_ran": True,
    }
    return CeoRunInput(**{**fields, **over})


def summary(**states: OracleState) -> OracleRunSummary:
    return OracleRunSummary(statuses=[
        OracleStatus(oracle=o, module=oracle_registry.module_name(o),
                     state=states.get(o.value, OracleState.RAN)) for o in OracleName])


def value(line) -> float | None:
    return line.measure.value


# ---- MP29 -----------------------------------------------------------------------------------

def test_mp29_recall_overall_and_per_priority_and_fp_over_adjudicated_only() -> None:
    card = build_scorecard(run_input(), summary())
    assert value(card.recall_overall) == 3 / 6
    assert (card.recall_overall.detected, card.recall_overall.total) == (3, 6)
    assert [(k, v.detected, v.total) for k, v in card.recall_by_priority.items()] == [
        ("P0", 1, 1), ("P1", 1, 3), ("P2", 1, 2)]
    assert value(card.recall_by_priority["P1"]) == 1 / 3
    # 3 matched + 1 ruled-on false positive are adjudicated; the unadjudicated one is neither
    assert card.false_positive_rate.value == 1 / 4
    assert (card.matched, card.adjudicated_false_positives, card.unadjudicated) == (3, 1, 1)
    assert list(card.recall_by_priority) == ["P0", "P1", "P2"]


def test_mp29_numbers_equal_bench_output_on_the_same_input() -> None:
    corpus = BenchCorpus(
        id="c", app="a", build_ref="b", mode="human_confirmed",
        seeded_bugs=[SeededBug(id=i, description=i, severity=sev, location="x", detect_hint="y",
                               provenance="human_independent")
                     for (i, *_), sev in zip(ITEMS, [Severity.S1] + [Severity.S2] * 3
                                             + [Severity.S3] * 2, strict=True)])
    trial = BenchTrial(
        id="t", corpus_id="c", participant=Participant.AUTOTESTER, kind="autotester",
        ordering="independent_parallel", participant_label="p",
        findings=[Finding(text="1", matched_bug_id="CEO-ATOM-001"),
                  Finding(text="2", matched_bug_id="CEO-ATOM-002"),
                  Finding(text="3", matched_bug_id="CEO-ATOM-005"), Finding(text="4")])
    expected = bench.scorecard(corpus, [trial])["p"]
    card = build_scorecard(run_input(), summary())
    assert value(card.recall_overall) == expected["detection_rate"]
    assert card.false_positive_rate.value == expected["false_positive_rate"]


def test_mp29_every_number_is_read_from_the_bench_scorer(monkeypatch) -> None:
    calls = []

    def fake(corpus, trials):
        calls.append(len(corpus.seeded_bugs))
        return {trials[0].participant_label: {
            "detection_rate": 0.123, "detected": 1, "seeded": 8, "false_positive_rate": 0.456}}

    monkeypatch.setattr(ceo_benchmark.bench, "scorecard", fake)
    card = build_scorecard(run_input(), summary())
    assert value(card.recall_overall) == 0.123 and card.false_positive_rate.value == 0.456
    assert calls, "the scorer was never called"


def test_mp29_no_second_scorer_in_the_stage() -> None:
    tree = ast.parse(Path(ceo_benchmark.__file__).read_text(encoding="utf-8"))
    divisions = [n for n in ast.walk(tree) if isinstance(n, ast.BinOp)
                 and isinstance(n.op, (ast.Div, ast.FloorDiv))]
    assert divisions == []
    stages = Path(ceo_benchmark.__file__).parent
    assert sorted(p.name for p in stages.glob("ceo_*.py")) == [
        "ceo_benchmark.py", "ceo_run_evidence.py"]      # no ceo_*scor* module beside the stage
    assert "bench.scorecard" in Path(ceo_benchmark.__file__).read_text(encoding="utf-8")


def test_mp29_unadjudicated_is_neither_tp_nor_fp() -> None:
    only_unadjudicated = [RunFinding(id="u1"), RunFinding(id="u2")]
    card = build_scorecard(run_input(findings=only_unadjudicated), summary())
    assert card.false_positive_rate.value is None
    assert card.false_positive_rate.text() == "unavailable (no adjudicated findings)"
    assert value(card.recall_overall) == 0 and card.unadjudicated == 2
    ruled = [RunFinding(id="u1", adjudication="false_positive"), RunFinding(id="u2")]
    assert build_scorecard(run_input(findings=ruled), summary()).false_positive_rate.value == 1.0


def test_mp29_recall_excluding_findings_that_need_seeded_data() -> None:
    card = build_scorecard(run_input(), summary())
    assert (card.recall_excluding_seeded_data.detected,
            card.recall_excluding_seeded_data.total) == (3, 5)
    assert value(card.recall_excluding_seeded_data) == 3 / 5


def test_mp29_one_recall_line_per_technique_naming_its_owner_unit() -> None:
    card = build_scorecard(run_input(), summary())
    assert [t.technique for t in card.techniques] == list(Technique)
    by = {t.technique: t for t in card.techniques}
    assert by[Technique.CROSS_TENANT].owner_units == ["T-213"]
    assert by[Technique.MULTI_ROLE_COMPARISON].owner_units == ["T-211", "T-215"]
    assert by[Technique.CROSS_TENANT].recall.detected == 1
    assert by[Technique.PAYMENT].recall.detected == 0   # ran, found nothing: a real 0
    assert by[Technique.PAYMENT].recall.measure.value == 0.0
    assert set(TECHNIQUE_OWNERS) == set(Technique)


def test_mp29_a_technique_whose_owner_did_not_run_reads_not_run_never_zero() -> None:
    states = {"tenant": OracleState.NOT_BUILT, "payment": OracleState.NOT_RUN,
              "mailbox": OracleState.ERRORED}
    card = build_scorecard(run_input(), summary(**states))
    by = {t.technique: t for t in card.techniques}
    for tech in (Technique.CROSS_TENANT, Technique.PAYMENT, Technique.INBOX):
        assert by[tech].state == "not run" and by[tech].recall is None
        assert by[tech].text().endswith(": not run")
    assert by[Technique.NOTIFICATION_ABSENCE].state == "not run"   # T-212 owner is among its two
    assert by[Technique.API_ERROR].state == "ran"
    no_runner = build_scorecard(run_input(runner_ran=False), summary())
    states = {t.technique: t.state for t in no_runner.techniques}
    assert states[Technique.HANDOFF_CHAIN] == "not run"


def test_wall_time_is_unknown_until_given() -> None:
    assert build_scorecard(run_input(), summary()).wall_time_s.text() == "unavailable (unknown)"
    assert build_scorecard(run_input(duration_s=90.0), summary()).wall_time_s.value == 90.0


def test_input_models_refuse_a_double_or_unknown_match_and_default_to_unadjudicated() -> None:
    twice = [RunFinding(id="a", matched_atomic_id="CEO-ATOM-001"),
             RunFinding(id="b", matched_atomic_id="CEO-ATOM-001")]
    with pytest.raises(ValidationError, match="one-to-one"):
        run_input(findings=twice)
    with pytest.raises(ValidationError, match="not in the list"):
        run_input(findings=[RunFinding(id="a", matched_atomic_id="NOPE")])
    with pytest.raises(ValidationError, match="no adjudication"):
        RunFinding(id="a", matched_atomic_id="CEO-ATOM-001", adjudication="false_positive")
    assert RunFinding(id="a").adjudication == "unadjudicated"
    with pytest.raises(ValidationError, match="duplicate"):
        one = AtomicFinding(id="x", priority=Priority.P0, technique=Technique.INBOX)
        AtomicList(items=[one, one])


# ---- MP30 -----------------------------------------------------------------------------------

def test_mp30_hash_and_commit_time_precede_the_run_so_recall_is_a_number() -> None:
    card = build_scorecard(run_input(), summary())
    assert card.ordering == "recorded" and value(card.recall_overall) == 0.5


@pytest.mark.parametrize("ordering,detail", [
    (good_ordering(committed_at=T0 + timedelta(hours=3)), "list committed after run start"),
    (good_ordering(committed_at=T0 + timedelta(hours=2)), "list committed after run start"),
    (good_ordering(list_sha256="cd" * 32), "list hash differs from the recorded one"),
    (None, "not recorded"),
])
def test_mp30_without_the_recorded_ordering_recall_is_unavailable(ordering, detail) -> None:
    card = build_scorecard(run_input(ordering=ordering), summary())
    assert card.ordering == detail
    assert card.recall_overall.text() == "unavailable (ordering not recorded)"
    assert all(v.text() == "unavailable (ordering not recorded)"
               for v in card.recall_by_priority.values())
    assert card.recall_excluding_seeded_data.measure.value is None
    ran = [t for t in card.techniques if t.state == "ran"]
    assert ran and all(t.recall.measure.value is None for t in ran)


def test_mp30_a_derived_from_finding_scenario_is_excluded_from_recall() -> None:
    findings = [RunFinding(id="run-f1", matched_atomic_id="CEO-ATOM-001", scenario_id="s-derived"),
                RunFinding(id="run-f2", matched_atomic_id="CEO-ATOM-002", scenario_id="s-blind"),
                RunFinding(id="run-f3", matched_atomic_id="CEO-ATOM-005")]
    labels = [ScenarioLabel(scenario_id="s-derived", derived_from_finding=True),
              ScenarioLabel(scenario_id="s-blind", derived_from_finding=False)]
    card = build_scorecard(run_input(findings=findings, labels=labels), summary())
    assert (card.recall_overall.detected, card.recall_overall.total) == (2, 5)
    assert value(card.recall_overall) == 2 / 5
    assert card.derived_excluded == 1
    assert "P0" in card.recall_by_priority and card.recall_by_priority["P0"].total == 0
    assert card.recall_by_priority["P0"].text() == "unavailable (no eligible ground truth)"
    unlabelled = build_scorecard(run_input(findings=findings), summary())
    assert value(unlabelled.recall_overall) == 3 / 6      # the label is what excludes it


def test_mp30_the_committed_scorecard_holds_only_counts_and_the_list_hash() -> None:
    run = run_input()
    card = build_scorecard(run, summary())
    committed = card.model_dump_json() + render_scorecard(card, summary())
    assert SHA in committed
    secrets = [i.id for i in run.atomic.items] + [f.id for f in run.findings]
    assert not [s for s in secrets if s in committed]
    strings = set(_strings(json.loads(card.model_dump_json())))
    vocabulary = ({t.value for t in Technique} | {"ran", "not run", "recorded", SHA, "unknown",
                  "ordering not recorded", "no eligible ground truth", "no adjudicated findings"}
                  | {u for owners in TECHNIQUE_OWNERS.values() for u, _ in owners})
    assert strings <= vocabulary, strings - vocabulary


def _strings(node) -> list[str]:
    if isinstance(node, str):
        return [node]
    if isinstance(node, dict):
        return [s for v in node.values() for s in _strings(v)]
    if isinstance(node, list):
        return [s for v in node for s in _strings(v)]
    return []


# ---- printed scorecard ----------------------------------------------------------------------

def test_the_printed_scorecard_has_the_per_oracle_table_from_the_registry() -> None:
    def never_there(name: str):
        raise ModuleNotFoundError(name=name)

    real = oracle_registry.oracle_statuses(importer=never_there)
    text = render_scorecard(build_scorecard(run_input(runner_ran=False), real), real)
    assert text.count("not built") >= len(OracleName)
    assert all(o.value in text for o in OracleName)
    mixed = summary(tenant=OracleState.NOT_BUILT, payment=OracleState.NOT_RUN)
    table = ceo_benchmark.render_oracle_table(mixed)
    assert len(table) == len(OracleName)
    assert any("tenant" in r and r.endswith("not built") for r in table)
    assert any("payment" in r and r.endswith("not run") for r in table)
    assert any("mailbox" in r and r.endswith("ran") for r in table)


def test_print_scorecard_writes_the_rendered_text() -> None:
    out = io.StringIO()
    card = build_scorecard(run_input(), summary())
    print_scorecard(card, summary(), file=out)
    text = out.getvalue()
    assert text.startswith("CEO benchmark scorecard") and "recall overall: 0.5 (3/6)" in text
    assert "recall P0: 1 (1/1)" in text and "wall time: unknown" in text
    assert "false positive rate (adjudicated findings only): 0.25" in text
    assert text.index("recall P0") < text.index("recall P1") < text.index("recall P2")
