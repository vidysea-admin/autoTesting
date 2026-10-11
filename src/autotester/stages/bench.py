"""BENCH: the north star made measurable. Contract: qa/contracts/bench.md K1-K5.

Turns a real run's `Verdict`s into `Finding`s against a `BenchCorpus`'s known
seeded bugs, and always scores through `BenchTrial.score` — never a
hand-computed detection-rate number anywhere in this module or its callers.
"""

from __future__ import annotations

from typing import Literal

from autotester.schema.bench import BenchCorpus, BenchTrial, Finding, SeededBug
from autotester.schema.enums import Participant, Result
from autotester.schema.verdict import Verdict


def findings_from_verdicts(
    verdicts: list[Verdict], case_bug_map: dict[str, str]
) -> list[Finding]:
    """One Finding per FAIL verdict. `case_bug_map` names which seeded bug a
    case's failure would mean (its known regression location); a FAIL on a
    case not in the map is a false positive (`matched_bug_id=None`) — the
    same treatment a real off-target report would get."""
    findings = []
    for verdict in verdicts:
        if verdict.result is not Result.FAIL:
            continue
        text = "; ".join(f"{f.criterion_id}: {f.reason}" for f in verdict.failures)
        findings.append(
            Finding(
                text=text or verdict.scoreboard,
                matched_bug_id=case_bug_map.get(verdict.case_id),
                evidence_refs=[ref for f in verdict.failures for ref in f.evidence_refs],
            )
        )
    return findings


def run_autotester_trial(
    trial_id: str, corpus: BenchCorpus, verdicts: list[Verdict], case_bug_map: dict[str, str],
    duration_s: float | None = None, *,
    ordering: Literal[
        "independent_parallel", "human_read_ai_first", "ai_read_human_first", "unknown"
    ] = "unknown",
) -> BenchTrial:
    """The real participant: findings derived mechanically from a real
    execute+grade run, never hand-adjusted afterward."""
    return BenchTrial(
        id=trial_id, corpus_id=corpus.id, participant=Participant.AUTOTESTER,
        participant_label="autotester-real-run",
        kind="autotester", ordering=ordering,
        findings=findings_from_verdicts(verdicts, case_bug_map),
        duration_s=duration_s,
    )


def oracle_human_trial(
    trial_id: str, corpus: BenchCorpus, duration_s: float | None = None
) -> BenchTrial:
    """Synthetic fixture oracle, typed separately from a live human.

    Missing duration stays unavailable; supplying timing never changes its kind.
    """
    if corpus.mode != "fixture" or any(
        bug.provenance != "fixture_seeded" for bug in corpus.seeded_bugs
    ):
        raise ValueError("oracle requires explicit fixture ground truth")
    findings = [
        Finding(text=f"{bug.location}: {bug.detect_hint}", matched_bug_id=bug.id,
                provenance="independent")
        for bug in corpus.seeded_bugs
    ]
    return BenchTrial(
        id=trial_id, corpus_id=corpus.id, participant=Participant.HUMAN,
        participant_label="human-oracle-baseline", findings=findings,
        kind="human_oracle", ordering="independent_parallel", duration_s=duration_s,
    )


def scorecard(
    corpus: BenchCorpus, trials: list[BenchTrial]
) -> dict[str, dict[str, float | int | str | None]]:
    """Every entry is `trial.score(corpus)` verbatim — the only place a
    detection-rate/false-positive-rate number is computed in this system."""
    return {
        trial.participant_label or trial.participant.value: trial.score(corpus)
        for trial in trials
    }


def seeded_bug(
    bug_id: str, description: str, location: str, detect_hint: str, severity
) -> SeededBug:
    return SeededBug(
        id=bug_id, description=description, location=location, detect_hint=detect_hint,
        severity=severity, provenance="fixture_seeded",
    )
