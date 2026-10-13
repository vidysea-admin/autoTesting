"""Build and check the T-136 acceptance comparison from stored bench artifacts.

Reuses `stages.bench.scorecard` (so every number is `BenchTrial.score` verbatim,
bench.md K3) and the `ProjectStore` bench files (K5). A human list is an input
file, not a code path: with no human `BenchTrial` the human column reads
`unavailable (no human list)` -- a supported mode (D-089 item 3), not an error.
"""

from __future__ import annotations

from autotester.schema.acceptance import (
    AcceptanceComparison,
    BugRow,
    Measure,
    ParticipantColumn,
)
from autotester.schema.bench import BenchCorpus, BenchTrial
from autotester.stages import bench
from autotester.store.project_store import ProjectStore

NO_HUMAN = "no human list"
AI_ASSISTED = "known_bugs_ai_assisted"
RECALL_BASIS = {
    "fixture": "seeded fixture bugs",
    "human_confirmed": "independent human list",
    AI_ASSISTED: "AI-assisted video review, not independent",
}


class MissingInput(Exception):
    """A stored artifact the comparison needs does not exist."""


def corpus_id_for(slug: str) -> str:
    """Convention: one acceptance corpus per project."""
    return f"{slug}-acceptance"


def _measure(score: dict, key: str, override: str | None = None) -> Measure:
    value = score.get(key)
    if value is None:
        reason = override or score.get(f"{key}_unavailable_reason") or "not reported"
        return Measure(unavailable_reason=str(reason))
    return Measure(value=float(value))


def _absent(participant: str, reason: str) -> ParticipantColumn:
    gone = Measure(unavailable_reason=reason)
    return ParticipantColumn(
        participant=participant, present=False, absent_reason=reason,
        detection_rate=gone, false_positive_rate=gone,
        severity_weighted_recall=gone, duration_s=gone,
    )


def _column(corpus: BenchCorpus, trial: BenchTrial, human_missing: bool) -> ParticipantColumn:
    score = bench.scorecard(corpus, [trial])[trial.participant_label or trial.participant.value]
    # With no human list the AutoTester recall has no independent denominator.
    override = NO_HUMAN if human_missing and corpus.mode not in ("fixture", AI_ASSISTED) else None
    independent = sum(1 for f in trial.findings if f.provenance == "independent")
    prompted = sum(1 for f in trial.findings if f.provenance == "prompted")
    return ParticipantColumn(
        participant=trial.participant.value, present=True, label=trial.participant_label,
        kind=trial.kind, ordering=trial.ordering, findings_reported=len(trial.findings),
        independent_findings=independent, prompted_findings=prompted,
        detected=int(score["detected"]), seeded=int(score["seeded"]),
        detection_rate=_measure(score, "detection_rate", override),
        false_positive_rate=_measure(score, "false_positive_rate"),
        severity_weighted_recall=_measure(score, "severity_weighted_recall", override),
        duration_s=_measure(score, "duration_s"),
        false_positive_population=str(score["false_positive_population"]),
        denominator_population=str(score["denominator_population"]),
    )


def _bug_rows(corpus: BenchCorpus, trials: list[BenchTrial]) -> list[BugRow]:
    return [
        BugRow(
            bug_id=bug.id, description=bug.description, severity=bug.severity.value,
            provenance=bug.provenance,
            found_by=[t.participant.value for t in trials
                      if any(f.matched_bug_id == bug.id for f in t.findings)],
        )
        for bug in corpus.seeded_bugs
    ]


def build_comparison(
    store: ProjectStore, slug: str, corpus: BenchCorpus | None = None
) -> AcceptanceComparison:
    """Assemble the comparison; raise `MissingInput` naming what is absent.

    `corpus` overrides the stored one (the gitignored known-bugs corpus, K12)."""
    corpus_id = corpus.id if corpus else corpus_id_for(slug)
    corpus = corpus or store.load_bench_corpus(corpus_id)
    if corpus is None:
        raise MissingInput(f"bench corpus {store.paths.bench_corpus(corpus_id)}")
    trials = store.list_bench_trials(corpus_id)
    ai = next((t for t in trials if t.kind == "autotester"), None)
    if ai is None:
        raise MissingInput(
            f"AutoTester bench trial (kind=autotester, corpus_id={corpus_id}) under "
            f"{store.paths.bench_dir}"
        )
    human = next((t for t in trials if t.participant.value == "human"), None)
    return AcceptanceComparison(
        id=f"cmp_{corpus_id}", project=slug, corpus_id=corpus_id, corpus_mode=corpus.mode,
        recall_basis=RECALL_BASIS.get(corpus.mode, "unknown"),
        human_list="present" if human else "absent",
        fp_rate_unadjudicated=human is None,
        autotester=_column(corpus, ai, human is None),
        human=_column(corpus, human, False) if human else _absent("human", NO_HUMAN),
        bugs=_bug_rows(corpus, [t for t in (ai, human) if t]),
        bugs_unavailable_reason=None if corpus.seeded_bugs else "no ground-truth bug list",
    )


def completeness_problems(cmp: AcceptanceComparison) -> list[str]:
    """Why this comparison is not judgeable (bench.md K9). Empty means complete.

    Asserts completeness only -- never that AutoTester won. In no-list mode the
    AutoTester false-positive rate and wall-clock must be real numbers (D-089)."""
    problems: list[str] = []
    ai = cmp.autotester
    if ai.kind != "autotester":
        problems.append(f"AutoTester column kind is {ai.kind!r}")
    if ai.ordering == "unknown":
        problems.append("AutoTester ordering not recorded (K7)")
    for name, measure in (("false_positive_rate", ai.false_positive_rate),
                          ("duration_s", ai.duration_s)):
        if measure.value is None:
            problems.append(f"autotester {name} {measure.text()} (must be measured)")
    if cmp.human_list == "present":
        hu = cmp.human
        if hu.kind in ("unknown", "autotester"):
            problems.append(f"human trial kind {hu.kind!r} (K6)")
        if hu.ordering == "unknown":
            problems.append("human ordering not recorded (K7)")
        if hu.findings_reported != hu.independent_findings + hu.prompted_findings:
            problems.append("human findings lack an independent/prompted mark (K7)")
    return problems
