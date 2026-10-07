"""The advisory UX artifacts: `UXFinding`, `UXCaseOutcome`, `UXReport` (PU2).

Findings are a SEPARATE artifact, persisted at `projects/<slug>/runs/<run_id>/ux_report.json`
beside -- never inside -- a case's result or verdict file. Nothing here is, or feeds, a
`Verdict`/`Judgment`; there is deliberately no score, no aggregate and no pass/fail field
(persona-ux-advisory.md "Out of scope"). Severity reuses `schema.enums.Severity` (C3).
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from autotester.schema.base import Artifact
from autotester.schema.enums import Severity


class UXFinding(BaseModel):
    """One advisory observation about one case, cited to real evidence."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    persona_id: str
    severity: Severity
    finding: str = Field(min_length=1, max_length=600)
    step_order: int | None = None
    evidence_path: str | None = Field(default=None, description="run-relative, from RawResult")

    @model_validator(mode="after")
    def _must_cite_something(self) -> UXFinding:
        if self.step_order is None and self.evidence_path is None:
            raise ValueError("a UX finding must cite a step_order or an evidence_path")
        return self


class UXDraft(BaseModel):
    """What the model returns for one finding -- validated against the real evidence before it
    becomes a `UXFinding` (a finding citing evidence that does not exist is dropped)."""

    model_config = ConfigDict(extra="forbid")

    severity: Severity
    finding: str = Field(min_length=1, max_length=600)
    step_order: int | None = None
    evidence_path: str | None = None


class UXJudgment(BaseModel):
    """The provider's structured answer for one case (the `Provider.judge` schema)."""

    model_config = ConfigDict(extra="forbid")

    findings: list[UXDraft] = Field(default_factory=list)


class UXCaseStatus(StrEnum):
    """How one case's UX pass ended. Only `ANALYZED` can carry findings."""

    ANALYZED = "analyzed"
    SKIPPED_BUDGET = "skipped_budget"
    NO_PERSONA = "no_persona"
    MISSING_PERSONA = "missing_persona"
    REFUSED_CONDITION = "refused_condition"
    NO_EVIDENCE = "no_evidence"
    WITHHELD = "withheld"
    PROVIDER_ERROR = "provider_error"


class UXCaseOutcome(BaseModel):
    """One case's advisory record: its status, why, and any findings."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    persona_id: str | None = None
    status: UXCaseStatus
    reason: str | None = None
    dropped_findings: int = Field(default=0, ge=0, description="model findings citing no real "
                                  "evidence, discarded rather than recorded")
    findings: list[UXFinding] = Field(default_factory=list)

    @model_validator(mode="after")
    def _only_analyzed_has_findings(self) -> UXCaseOutcome:
        if self.findings and self.status is not UXCaseStatus.ANALYZED:
            raise ValueError("only an ANALYZED case may carry findings")
        return self


class UXReport(Artifact):
    """One run's advisory UX pass. `complete=False` means the pass was cut short; an absent
    file means UX was never requested -- exports must keep those three states distinct."""

    run_id: str
    project: str
    provider: str = Field(description="`Provider.label` that served the UX calls")
    max_calls: int = Field(ge=0)
    calls_used: int = Field(ge=0)
    complete: bool = True
    cases: list[UXCaseOutcome] = Field(default_factory=list)

    def findings_for(self, case_id: str) -> list[UXFinding]:
        return [f for c in self.cases if c.case_id == case_id for f in c.findings]

    def outcome_for(self, case_id: str) -> UXCaseOutcome | None:
        return next((c for c in self.cases if c.case_id == case_id), None)
