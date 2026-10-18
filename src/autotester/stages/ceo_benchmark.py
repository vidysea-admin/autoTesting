"""Score the CEO benchmark through the existing bench scorer, and print it (MP29, MP30, MPI6).

One job: turn a `CeoRunInput` (the private atomic list's ids and categories, the run's matched
findings) into a `CeoScorecard`, and render it with the per-oracle ran / not built / not run table
from `oracle_registry`. There is NO second scorer here: every rate is read out of
`BenchTrial.score` via `stages.bench.scorecard` (the same call `acceptance_comparison` makes), by
building a `BenchCorpus` / `BenchTrial` per population (all, per priority, per technique, without
seeded-data findings). This module contains no division; a test pins that.

Rules it applies on top of the scorer:
  * Unadjudicated findings are dropped from the FP trial: they are neither TP nor FP, so the FP rate
    is over adjudicated findings (matched ones and ruled-on false positives) only.
  * Ordering (T-136 gate): if the list's sha256 and commit time do not precede the run start, the
    trial's ordering is `unknown`, and bench itself answers `ordering not recorded` -- recall reads
    `unavailable (ordering not recorded)`, never a number.
  * Contamination: a finding from a scenario labelled derived-from-finding is not credited; the
    atomic finding it matched leaves the recall population (numerator and denominator).
  * A technique whose owner did not run reads `not run`, never 0.
"""

from __future__ import annotations

from typing import TextIO

from autotester.schema.acceptance import Measure
from autotester.schema.bench import BenchCorpus, BenchTrial, Finding, SeededBug
from autotester.schema.ceo_inputs import AtomicFinding, CeoRunInput, Technique
from autotester.schema.ceo_scorecard import CeoScorecard, RecallLine, TechniqueLine
from autotester.schema.enums import Participant, Severity
from autotester.schema.multi_role_enums import OracleName, Priority
from autotester.schema.oracle_context import OracleRunSummary, OracleState
from autotester.stages import bench

CORPUS_ID = "ceo-benchmark"
LABEL = "autotester-ceo-benchmark"
SEVERITY_FOR = {Priority.P0: Severity.S1, Priority.P1: Severity.S2, Priority.P2: Severity.S3}
# (unit, oracle): oracle None is the cross-role framework (T-210 session, T-211 runner).
Owner = tuple[str, OracleName | None]
TECHNIQUE_OWNERS: dict[Technique, tuple[Owner, ...]] = {
    Technique.MULTI_ROLE_COMPARISON: (("T-211", None), ("T-215", OracleName.CONSISTENCY)),
    Technique.COPY_BRANDING: (("T-216", OracleName.COPY_LINT),),
    Technique.INBOX: (("T-212", OracleName.MAILBOX),),
    Technique.STATE_AFTER: (("T-220", OracleName.STATE_AFTER),),
    Technique.CROSS_ROLE_CONSISTENCY: (("T-215", OracleName.CONSISTENCY),),
    Technique.NEGATIVE_INPUT: (("T-219", OracleName.NEGATIVE_INPUT),),
    Technique.HANDOFF_CHAIN: (("T-210", None), ("T-211", None)),
    Technique.NOTIFICATION_ABSENCE: (("T-211", None), ("T-212", OracleName.MAILBOX)),
    Technique.CROSS_TENANT: (("T-213", OracleName.TENANT),),
    Technique.API_ERROR: (("T-214", OracleName.API_ERROR),),
    Technique.ANSWER_KEY: (("T-215", OracleName.ANSWER_KEY),),
    Technique.RESPONSIVE: (("T-216", OracleName.RESPONSIVE),),
    Technique.PAYMENT: (("T-217", OracleName.PAYMENT),),
    Technique.REQUEST_COUNT: (("T-214", OracleName.REQUEST_BUDGET),),
}


def _corpus(items: list[AtomicFinding]) -> BenchCorpus:
    bugs = [SeededBug(id=i.id, description=i.id, severity=SEVERITY_FOR[i.priority],
                      location=i.technique.value, detect_hint=i.id, provenance="human_independent")
            for i in items]
    return BenchCorpus(id=CORPUS_ID, app=CORPUS_ID, build_ref=CORPUS_ID, seeded_bugs=bugs,
                       mode="human_confirmed")


def _trial(findings: list[Finding], ordering_ok: bool, duration_s: float | None) -> BenchTrial:
    return BenchTrial(
        id="ceo-trial", corpus_id=CORPUS_ID, participant=Participant.AUTOTESTER,
        participant_label=LABEL, kind="autotester", findings=findings, duration_s=duration_s,
        ordering="independent_parallel" if ordering_ok else "unknown")


def _measure(score: dict, key: str) -> Measure:
    """The scorer's number, or its own reason when there is none (never a zero)."""
    if score[key] is None:
        return Measure(unavailable_reason=str(score[f"{key}_unavailable_reason"]))
    return Measure(value=float(score[key]))


def ordering_detail(run: CeoRunInput) -> str:
    """Why the T-136 ordering gate passes or fails, in a fixed, finding-free vocabulary."""
    record = run.ordering
    if record is None:
        return "not recorded"
    if record.list_sha256 != run.atomic_sha256:
        return "list hash differs from the recorded one"
    if record.committed_at >= record.run_started_at:
        return "list committed after run start"
    return "recorded"


def _recall(items: list[AtomicFinding], credited: set[str], run: CeoRunInput) -> RecallLine:
    """Recall of one population, read from `BenchTrial.score`."""
    ids = {item.id for item in items}
    findings = [Finding(text=i, matched_bug_id=i) for i in sorted(credited & ids)]
    trial = _trial(findings, ordering_detail(run) == "recorded", run.duration_s)
    score = bench.scorecard(_corpus(items), [trial])[LABEL]
    return RecallLine(measure=_measure(score, "detection_rate"),
                      detected=int(score["detected"]), total=int(score["seeded"]))


def _derived_ids(run: CeoRunInput) -> set[str]:
    derived = {x.scenario_id for x in run.labels if x.derived_from_finding}
    return {f.matched_atomic_id for f in run.findings
            if f.matched_atomic_id and f.scenario_id in derived}


def _false_positive_rate(run: CeoRunInput) -> Measure:
    """FP rate over adjudicated findings only: unadjudicated ones are left out of the trial."""
    findings = [Finding(text=f.id, matched_bug_id=f.matched_atomic_id) for f in run.findings
                if f.matched_atomic_id or f.adjudication == "false_positive"]
    score = bench.scorecard(_corpus(run.atomic.items), [_trial(findings, True, None)])[LABEL]
    if score["false_positive_rate"] is None:
        return Measure(unavailable_reason="no adjudicated findings")
    return Measure(value=float(score["false_positive_rate"]))


def technique_ran(technique: Technique, summary: OracleRunSummary, runner_ran: bool) -> bool:
    """True only if every owner of the technique ran; a missing owner is `not run`, not zero."""
    state = {s.oracle: s.state for s in summary.statuses}
    return all(runner_ran if oracle is None else state[oracle] is OracleState.RAN
               for _, oracle in TECHNIQUE_OWNERS[technique])


def _technique_line(technique: Technique, items: list[AtomicFinding], credited: set[str],
                    run: CeoRunInput, summary: OracleRunSummary) -> TechniqueLine:
    owners = list(dict.fromkeys(unit for unit, _ in TECHNIQUE_OWNERS[technique]))
    if not technique_ran(technique, summary, run.runner_ran):
        return TechniqueLine(technique=technique, owner_units=owners, state="not run")
    mine = [i for i in items if i.technique is technique]
    return TechniqueLine(technique=technique, owner_units=owners, state="ran",
                         recall=_recall(mine, credited, run))


def build_scorecard(run: CeoRunInput, summary: OracleRunSummary) -> CeoScorecard:
    """The scorecard for one run; `summary` is the oracle registry's per-oracle status."""
    derived = _derived_ids(run)
    items = [i for i in run.atomic.items if i.id not in derived]
    credited = {f.matched_atomic_id for f in run.findings
                if f.matched_atomic_id and f.matched_atomic_id not in derived}
    by_priority = {p.value: _recall([i for i in items if i.priority is p], credited, run)
                   for p in Priority}
    matched = sum(1 for f in run.findings if f.matched_atomic_id)
    return CeoScorecard(
        atomic_count=len(run.atomic.items), atomic_sha256=run.atomic_sha256,
        ordering=ordering_detail(run), findings_total=len(run.findings), matched=matched,
        adjudicated_false_positives=sum(f.adjudication == "false_positive" for f in run.findings),
        unadjudicated=sum(f.adjudication == "unadjudicated" for f in run.findings),
        derived_excluded=len(derived),
        recall_overall=_recall(items, credited, run), recall_by_priority=by_priority,
        recall_excluding_seeded_data=_recall(
            [i for i in items if not i.needs_seeded_data], credited, run),
        false_positive_rate=_false_positive_rate(run),
        wall_time_s=(Measure(unavailable_reason="unknown") if run.duration_s is None
                     else Measure(value=run.duration_s)),
        techniques=[_technique_line(t, items, credited, run, summary) for t in Technique],
    )


def render_oracle_table(summary: OracleRunSummary) -> list[str]:
    """One line per registry oracle: module and `ran` / `not built` / `not run` / `errored`."""
    return [f"  {s.oracle.value:<18} {s.module}  {s.state.value}"
            + (f" [{s.reason}]" if s.reason else "") for s in summary.statuses]


def render_scorecard(card: CeoScorecard, summary: OracleRunSummary) -> str:
    """The printed scorecard: counts, hash, recall lines, technique lines and the oracle table."""
    lines = [
        "CEO benchmark scorecard (counts and the list hash only)",
        f"atomic list: {card.atomic_count} findings, sha256 {card.atomic_sha256}",
        f"ordering: {card.ordering}",
        f"run findings: {card.findings_total} (matched {card.matched}, adjudicated false "
        f"positives {card.adjudicated_false_positives}, unadjudicated {card.unadjudicated}); "
        f"excluded as derived: {card.derived_excluded}",
        f"recall overall: {card.recall_overall.text()}",
        *[f"recall {name}: {line.text()}" for name, line in card.recall_by_priority.items()],
        f"recall excluding seeded-data findings: {card.recall_excluding_seeded_data.text()}",
        f"false positive rate (adjudicated findings only): {card.false_positive_rate.text()}",
        f"wall time: {card.wall_time_s.unavailable_reason or card.wall_time_s.text()}",
        "recall per technique (owner units):",
        *[f"  {t.text()}" for t in card.techniques],
        "oracles (ran / not built / not run):",
        *render_oracle_table(summary),
    ]
    return "\n".join(lines)


def print_scorecard(card: CeoScorecard, summary: OracleRunSummary,
                    file: TextIO | None = None) -> None:
    """Print the scorecard to `file` (stdout by default)."""
    print(render_scorecard(card, summary), file=file)
