"""Grading. An independent, stateless judge reads evidence against a rubric.

The executor never grades itself: the context that took a shortcut will not
catch the shortcut. A PASS requires cited evidence.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from autotester.schema.base import Artifact
from autotester.schema.enums import Result


class Criterion(BaseModel):
    """One checkable bar. If it can be argued about, it is not a criterion."""

    model_config = ConfigDict(extra="forbid")

    id: str
    text: str
    evidence_required: bool = True

    @property
    def fingerprint(self) -> str:
        """What the criterion says. A bug opened on it remembers this, so an edited criterion is
        detected (T-199b, TB4) and a bug is never closed against a different bar."""
        from autotester.core.ids import content_id

        return content_id("crit", self.model_dump(mode="json"))


class Rubric(Artifact):
    """The grading contract for a case. More specific than the case itself.

    `no_fire` is what stops a grader inventing work: style nits, pre-existing
    issues, and anything out of scope are named and excluded up front.
    """

    id: str
    case_id: str | None = None
    criteria: list[Criterion] = Field(default_factory=list)
    no_fire: list[str] = Field(default_factory=list)
    feedback_format: str = Field(
        default="Line 1: `Criteria N/M met.` Then one bullet per failure: "
        "`<criterion id> — <what is wrong>. <what to do>.`"
    )

    @property
    def fingerprint(self) -> str:
        from autotester.core.ids import content_id

        return content_id(
            "rub",
            {
                "criteria": [c.model_dump(mode="json") for c in self.criteria],
                "no_fire": self.no_fire,
            },
        )


class Failure(BaseModel):
    """One unmet criterion, with the evidence that shows it."""

    model_config = ConfigDict(extra="forbid")

    criterion_id: str
    reason: str
    evidence_refs: list[str] = Field(default_factory=list)
    fix_hint: str | None = None


class Judgment(BaseModel):
    """Raw judge output for one grading call — the stage fills in run_id, case_id,
    grader_provider and rubric_hash afterward; the model is not asked to invent them."""

    model_config = ConfigDict(extra="forbid")

    result: Result
    scoreboard: str = Field(default="")
    criteria_met: int = 0
    criteria_total: int = 0
    failures: list[Failure] = Field(default_factory=list)
    note: str | None = None
    defect_observed: bool | None = Field(
        default=None,
        description="Did the evidence show a product defect? Authoritative over `note`; None = "
                    "the judge omitted it (grade() then falls back to the note guard).")
    defect_summary: str | None = Field(
        default=None, description="One sentence naming the defect when defect_observed is true")

    @field_validator("defect_observed", mode="before")
    @classmethod
    def _coerce_defect_observed(cls, value: object) -> object:
        """Accept bool-like strings/ints from a model; anything else fails validation."""
        if value is None or isinstance(value, bool):
            return value
        text = str(value).strip().lower()
        if text in {"true", "yes", "1"}:
            return True
        if text in {"false", "no", "0"}:
            return False
        raise ValueError(f"defect_observed must be a boolean, got {value!r}")


class Verdict(Artifact):
    """The judge's output for one case in one run."""

    run_id: str
    case_id: str
    result: Result
    scoreboard: str = Field(default="", description="e.g. 'Criteria 5/7 met.'")
    criteria_met: int = 0
    criteria_total: int = 0
    failures: list[Failure] = Field(default_factory=list)
    grader_provider: str = ""
    rubric_hash: str = ""
    note: str | None = None
    images_requested: int = Field(
        default=0, description="SCREENSHOT evidence rows this case offered the judge"
    )
    images_seen: int = Field(
        default=0, description="of those, the files that actually existed and were sent"
    )

    @property
    def is_actionable_failure(self) -> bool:
        """FAIL with at least one cited failure — what a human should look at."""
        return self.result is Result.FAIL and bool(self.failures)

    @property
    def graded_on_partial_evidence(self) -> bool:
        """The judge saw fewer screenshots than the evidence claimed (AT-366).

        All three providers drop a non-existent path in silence, so before this
        pair of counts existed a verdict rendered on none of its images looked
        exactly like one rendered on all of them. A `True` here does not mean the
        verdict is wrong — it means nobody can tell, which is the thing that was
        previously invisible."""
        return self.images_seen < self.images_requested
