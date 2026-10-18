"""The CEO-benchmark inputs: the private atomic list and the run's matched findings (MP29, MP30).

One job: the typed inputs `stages/ceo_benchmark.py` scores. The atomic list is one row per defect
with only an id, a priority, a detection technique and a seeded-data flag -- no finding text, so a
model dumped to a committed file cannot leak a CEO finding (MPI6). The closed `Technique`
vocabulary lives here, in this unit's own schema file (`schema/enums.py` is at its cap and
`schema/multi_role_enums.py` belongs to T-207). `Priority` is reused, never redefined.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from autotester.schema.multi_role_enums import Priority

ATOMIC_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$"
SHA256_PATTERN = r"^[0-9a-f]{64}$"


class Technique(StrEnum):
    """The CEO's detection techniques (intent "Scoring"); the stage maps each to its owner unit."""

    MULTI_ROLE_COMPARISON = "multi_role_comparison"
    COPY_BRANDING = "copy_branding"
    INBOX = "inbox"
    STATE_AFTER = "state_after"
    CROSS_ROLE_CONSISTENCY = "cross_role_consistency"
    NEGATIVE_INPUT = "negative_input"
    HANDOFF_CHAIN = "handoff_chain"
    NOTIFICATION_ABSENCE = "notification_absence"
    CROSS_TENANT = "cross_tenant"
    API_ERROR = "api_error"
    ANSWER_KEY = "answer_key"
    RESPONSIVE = "responsive"
    PAYMENT = "payment"
    REQUEST_COUNT = "request_count"


class AtomicFinding(BaseModel):
    """One atomic defect of the CEO list: identity and categories only, never its text."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=ATOMIC_ID_PATTERN)
    priority: Priority
    technique: Technique
    needs_seeded_data: bool = Field(
        default=False, description="needs data the run was not given; excluded from the "
                                   "'excluding seeded data' recall")


class AtomicList(BaseModel):
    """The split list. The file stays private under `.work/`; only its count and hash travel."""

    model_config = ConfigDict(extra="forbid")

    items: list[AtomicFinding] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique_ids(self) -> AtomicList:
        if len({item.id for item in self.items}) != len(self.items):
            raise ValueError("duplicate atomic finding ids")
        return self


class RunFinding(BaseModel):
    """One AutoTester finding, as matched to the list. `matched_atomic_id` is the one-to-one match.

    An unmatched finding is `unadjudicated` until Umesh rules; only `false_positive` counts as an
    FP, and nothing unmatched ever counts as a true positive."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=ATOMIC_ID_PATTERN)
    matched_atomic_id: str | None = None
    adjudication: Literal["false_positive", "unadjudicated"] | None = None
    scenario_id: str | None = None

    @model_validator(mode="after")
    def _adjudication_fits_match(self) -> RunFinding:
        if self.matched_atomic_id is not None and self.adjudication is not None:
            raise ValueError("a matched finding carries no adjudication")
        if self.matched_atomic_id is None and self.adjudication is None:
            self.adjudication = "unadjudicated"
        return self


class ScenarioLabel(BaseModel):
    """Marks a scenario written from a specific finding; its matches leave recall (MP30)."""

    model_config = ConfigDict(extra="forbid")

    scenario_id: str = Field(min_length=1, max_length=64)
    derived_from_finding: bool


class OrderingRecord(BaseModel):
    """When the list's hash was committed against when the run started (T-136 gate, MP30)."""

    model_config = ConfigDict(extra="forbid")

    list_sha256: str = Field(pattern=SHA256_PATTERN)
    committed_at: datetime
    run_started_at: datetime

    @model_validator(mode="after")
    def _aware(self) -> OrderingRecord:
        if self.committed_at.tzinfo is None or self.run_started_at.tzinfo is None:
            raise ValueError("ordering times must carry a timezone")
        return self


class CeoRunInput(BaseModel):
    """Everything the scorecard is built from; `atomic_sha256` is the hash of the list file."""

    model_config = ConfigDict(extra="forbid")

    atomic: AtomicList
    atomic_sha256: str = Field(pattern=SHA256_PATTERN)
    findings: list[RunFinding] = Field(default_factory=list)
    labels: list[ScenarioLabel] = Field(default_factory=list)
    ordering: OrderingRecord | None = None
    duration_s: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    runner_ran: bool = Field(
        default=False, description="the cross-role runner (T-210/T-211) ran in this run")

    @model_validator(mode="after")
    def _matches_are_one_to_one(self) -> CeoRunInput:
        known = {item.id for item in self.atomic.items}
        matched = [f.matched_atomic_id for f in self.findings if f.matched_atomic_id]
        if any(m not in known for m in matched):
            raise ValueError("a finding matches an atomic id that is not in the list")
        if len(set(matched)) != len(matched):
            raise ValueError("matching is one-to-one: an atomic id is matched twice")
        if len({f.id for f in self.findings}) != len(self.findings):
            raise ValueError("duplicate run finding ids")
        return self
