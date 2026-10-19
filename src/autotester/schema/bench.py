"""The north star, made measurable: human expert tester vs AutoTester.

Both participants get the same material pack and the same seeded build. The
scorecard is computed from these records — never written by hand.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from autotester.schema.base import Artifact
from autotester.schema.enums import Participant, Severity

# Which ground-truth provenance forms the recall denominator for each corpus mode. The
# AI-assisted known-bugs list is its own population: never "human_independent" (bench.md K12).
DENOMINATOR_PROVENANCE = {
    "fixture": "fixture_seeded",
    "human_confirmed": "human_independent",
    "known_bugs_ai_assisted": "ai_video_review",
}


class SeededBug(BaseModel):
    """A deliberately introduced defect with known ground truth."""

    model_config = ConfigDict(extra="forbid")

    id: str
    description: str
    severity: Severity = Severity.S2
    location: str = Field(description="route/screen where it manifests")
    detect_hint: str = Field(description="what a correct finding must state")
    provenance: Literal[
        "fixture_seeded", "human_independent", "human_prompted", "ai_video_review", "unknown"
    ] = "unknown"


class Finding(BaseModel):
    """One reported defect from a participant, matched against ground truth."""

    model_config = ConfigDict(extra="forbid")

    text: str
    matched_bug_id: str | None = Field(default=None, description="None means false positive")
    evidence_refs: list[str] = Field(default_factory=list)
    reported_at_s: float | None = None
    provenance: Literal["independent", "prompted", "unknown"] = "unknown"
    source: Literal["case", "crawl"] = Field(
        default="case",
        description="where the finding came from: a FAIL verdict on a case, or a crawl issue "
        "(stages/crawl_findings.py), so a report can tell them apart",
    )


class BenchCorpus(Artifact):
    """A build with known seeded defects and the material pack given to testers."""

    id: str
    app: str
    build_ref: str
    seeded_bugs: list[SeededBug] = Field(default_factory=list)
    material_refs: list[str] = Field(default_factory=list, description="videos/docs handed over")
    mode: Literal["fixture", "human_confirmed", "known_bugs_ai_assisted", "unknown"] = "unknown"

    @model_validator(mode="after")
    def validate_truth(self) -> BenchCorpus:
        """Refuse ambiguous identities and contradictory declared ground truth."""
        if len({bug.id for bug in self.seeded_bugs}) != len(self.seeded_bugs):
            raise ValueError("duplicate ground-truth bug IDs")
        allowed = {
            "fixture": {"fixture_seeded", "unknown"},
            "human_confirmed": {"human_independent", "human_prompted", "unknown"},
            "known_bugs_ai_assisted": {"ai_video_review"},
            "unknown": {"unknown"},
        }
        if any(bug.provenance not in allowed[self.mode] for bug in self.seeded_bugs):
            raise ValueError("corpus mode contradicts ground-truth provenance")
        return self


class BenchTrial(Artifact):
    """One participant's attempt on one corpus."""

    id: str
    corpus_id: str
    participant: Participant
    participant_label: str = ""
    findings: list[Finding] = Field(default_factory=list)
    kind: Literal["autotester", "human_live", "human_oracle", "unknown"] = "unknown"
    ordering: Literal[
        "independent_parallel", "human_read_ai_first", "ai_read_human_first", "unknown"
    ] = "unknown"
    duration_s: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    crawl_ids_scanned: list[str] = Field(
        default_factory=list,
        description="crawls whose recorded issues were converted to findings; non-empty makes "
        "'0 product issues' a measured fact rather than a missing input",
    )

    @model_validator(mode="after")
    def validate_participant(self) -> BenchTrial:
        """A synthetic oracle cannot become a live human by relabeling it."""
        expected = {
            "autotester": Participant.AUTOTESTER,
            "human_live": Participant.HUMAN,
            "human_oracle": Participant.HUMAN,
        }
        if self.kind in expected and self.participant != expected[self.kind]:
            raise ValueError("participant contradicts kind")
        return self

    def _eligible_truth(self, corpus: BenchCorpus) -> tuple[dict[str, SeededBug], str | None]:
        """Select the declared denominator; missing evidence never becomes a zero."""
        if self.ordering == "unknown":
            return {}, "ordering not recorded"
        if self.kind == "unknown":
            return {}, "participant kind not recorded"
        if self.participant == Participant.AUTOTESTER and self.ordering == "ai_read_human_first":
            return {}, "AutoTester read human findings first"
        if corpus.mode == "unknown":
            return {}, "corpus mode not recorded"
        if any(bug.provenance == "unknown" for bug in corpus.seeded_bugs):
            return {}, "ground-truth provenance not recorded"
        provenance = DENOMINATOR_PROVENANCE[corpus.mode]
        truth = {bug.id: bug for bug in corpus.seeded_bugs if bug.provenance == provenance}
        if not truth:
            return truth, "no eligible ground truth"
        if self.kind == "human_live" and any(
            finding.provenance == "unknown" for finding in self.findings
        ):
            return truth, "human finding provenance not recorded"
        return truth, None

    def score(self, corpus: BenchCorpus) -> dict[str, float | int | str | None]:
        """Detection rate, false-positive rate, and severity-weighted recall."""
        if corpus.id != self.corpus_id:
            raise ValueError("trial corpus_id does not match corpus")
        if self.kind == "human_oracle" and corpus.mode != "fixture":
            raise ValueError("oracle requires fixture corpus")
        seeded, unavailable = self._eligible_truth(corpus)
        matched = {f.matched_bug_id for f in self.findings if f.matched_bug_id in seeded
                   and (self.kind != "human_live" or f.provenance == "independent")}
        all_ids = {bug.id for bug in corpus.seeded_bugs}
        false_positives = [f for f in self.findings if f.matched_bug_id not in all_ids]
        weights = {Severity.S1: 3.0, Severity.S2: 2.0, Severity.S3: 1.0}
        total_weight = sum(weights[b.severity] for b in seeded.values())
        found_weight = sum(weights[seeded[b].severity] for b in matched)
        reported = len(self.findings)
        return {
            "detected": len(matched),
            "seeded": len(seeded),
            "detection_rate": len(matched) / len(seeded) if unavailable is None else None,
            "detection_rate_unavailable_reason": unavailable,
            "false_positives": len(false_positives),
            "false_positive_rate": len(false_positives) / reported if reported else None,
            "false_positive_rate_unavailable_reason": None if reported else "no reported findings",
            "false_positive_population": "all_reported_findings",
            "severity_weighted_recall": (
                found_weight / total_weight if unavailable is None else None
            ),
            "severity_weighted_recall_unavailable_reason": unavailable,
            "duration_s": self.duration_s,
            "duration_s_unavailable_reason": (
                None if self.duration_s is not None else "timing not recorded"
            ),
            "kind": self.kind,
            "ordering": self.ordering,
            "denominator_mode": corpus.mode,
            "denominator_population": DENOMINATOR_PROVENANCE.get(corpus.mode, "unknown"),
            "denominator_unavailable_reason": unavailable,
        }
