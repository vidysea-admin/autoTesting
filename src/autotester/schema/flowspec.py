"""The FlowSpec — the system's understanding of the product under test.

Produced by INGEST from videos/docs/text, reviewed and editable by a human, and
consumed by EXPAND. Every step carries provenance back to its source timestamp
so a human can watch the exact second the system learned a step from.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from autotester.core.ids import content_id
from autotester.schema.base import Artifact
from autotester.schema.enums import Action, ReviewStatus


class SourceRef(BaseModel):
    """Where a piece of understanding came from — a video second, a doc line."""

    model_config = ConfigDict(extra="forbid")

    source_id: str
    t_start: float | None = Field(default=None, description="seconds into a video")
    t_end: float | None = None
    locator: str | None = Field(default=None, description="page/section for a doc")


class FieldConstraints(BaseModel):
    """What the UI says a field accepts. Drives boundary/edge case generation."""

    model_config = ConfigDict(extra="forbid")

    min: float | None = None
    max: float | None = None
    min_length: int | None = None
    max_length: int | None = None
    pattern: str | None = None
    enum: list[str] | None = None


class InputField(BaseModel):
    """One input on a screen."""

    model_config = ConfigDict(extra="forbid")

    name: str
    label: str | None = None
    type: str = Field(default="text", description="text, email, password, select, file…")
    required: bool = False
    secret_key: str | None = Field(default=None, description="SecretRef key if sensitive")
    constraints: FieldConstraints = Field(default_factory=FieldConstraints)


class ExpectedState(BaseModel):
    """What must be true for a step to have succeeded.

    `visual_signal` exists because the DOM does not always say it — the brain's
    canonical example is "the thumbs-up turns yellow when a post is liked".
    """

    model_config = ConfigDict(extra="forbid")

    url: str | None = Field(default=None, description="exact URL or glob pattern")
    visible_text: list[str] = Field(default_factory=list)
    absent_text: list[str] = Field(default_factory=list)
    dom_asserts: list[str] = Field(default_factory=list, description="selectors that must exist")
    visual_signal: str | None = None
    network: list[str] = Field(default_factory=list, description="expected request patterns")


FlowKind = Literal["ideal", "narrated", "variant"]
"""`ideal` is a task's reference path; `narrated` walks the same path in another
recording; `variant` diverges from it -- an "another possibility", not an error."""
IdealBasis = Literal["crawl", "modal", "only"]


class Step(BaseModel):
    """One browser action plus what it should produce."""

    model_config = ConfigDict(extra="forbid")

    order: int
    action: Action
    target: str = Field(description="semantic locator: role/name/label, not a brittle CSS path")
    value: str | None = Field(default=None, description="literal, or {{SECRET:KEY}} placeholder")
    expected: ExpectedState = Field(default_factory=ExpectedState)
    source_ref: SourceRef | None = None
    note: str | None = None
    screen_id: str | None = Field(default=None, description="the Screen this step acted on")
    narration: str | None = Field(default=None, description="the presenter's words, verbatim")
    on_screen_text: str | None = None


class Screen(BaseModel):
    """A distinguishable page/state of the product."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    url_pattern: str | None = None
    signals: list[str] = Field(default_factory=list, description="cues that identify this screen")
    fields: list[InputField] = Field(default_factory=list)
    screenshot_ref: str | None = None
    source_ref: SourceRef | None = Field(
        default=None, description="video second this screen was first learned from"
    )
    video_only: bool = Field(
        default=False, exclude_if=lambda v: not v,
        description="reconcile found no crawl/spec screen for it -- learned from video alone")


class Flow(BaseModel):
    """An end-to-end journey through screens."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    entry_screen: str
    exit_screen: str | None = None
    preconditions: list[str] = Field(default_factory=list)
    steps: list[Step] = Field(default_factory=list)
    requires_auth: bool = False
    kind: FlowKind | None = Field(default=None, description="set by reconcile (D-070)")
    ideal_basis: IdealBasis | None = None
    variant_of: str | None = Field(default=None, description="the ideal Flow.id it diverges from")
    diverges_at: int | None = Field(default=None, description="Step.order of first divergence")

    @property
    def source_id(self) -> str | None:
        """The recording this flow was learned from: its first sourced step."""
        return next((s.source_ref.source_id for s in self.steps if s.source_ref), None)


class Review(BaseModel):
    """The human gate. A flowspec drives nothing until a person approves it."""

    model_config = ConfigDict(extra="forbid")

    status: ReviewStatus = ReviewStatus.DRAFT
    by: str | None = None
    at: str | None = None
    note: str | None = None


class Conflict(BaseModel):
    """Sources disagreed. Flagged for a human — never silently merged."""

    model_config = ConfigDict(extra="forbid")

    subject: str
    claims: list[str]
    source_refs: list[SourceRef] = Field(default_factory=list)


class FlowSpec(Artifact):
    """The reviewed understanding of one project's UI."""

    project: str
    version: int = 1
    screens: list[Screen] = Field(default_factory=list)
    flows: list[Flow] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    conflicts: list[Conflict] = Field(default_factory=list)
    review: Review = Field(default_factory=Review)
    app_overview: str | None = Field(
        default=None, description="what the product is, from a video's own summary"
    )

    @property
    def fingerprint(self) -> str:
        """Content id of the semantic payload — changes only when meaning changes."""
        payload = {
            "screens": [s.model_dump(mode="json") for s in self.screens],
            "flows": [f.model_dump(mode="json") for f in self.flows],
        }
        return content_id("fs", payload)

    def flow(self, flow_id: str) -> Flow | None:
        return next((f for f in self.flows if f.id == flow_id), None)

    def screen(self, screen_id: str) -> Screen | None:
        return next((s for s in self.screens if s.id == screen_id), None)


# -- reconcile (D-070 part 2): video knowledge graph -> product knowledge graph --
Band = Literal["matched", "ambiguous", "new"]


class ScreenJudgement(BaseModel):
    """The judge's answer for ONE ambiguous screen pair -- the only call reconcile makes."""

    model_config = ConfigDict(extra="forbid")

    same_screen: bool
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = ""


class ScreenMatch(BaseModel):
    """One canonical video screen scored against its best candidate (RC5)."""

    model_config = ConfigDict(extra="forbid")

    screen_id: str
    candidate: str | None = Field(default=None, description="ScreenNode.id or Screen.id")
    candidate_kind: Literal["crawl", "spec"] | None = None
    route: float = 0.0
    title: float = 0.0
    elements: float = 0.0
    total: float = 0.0
    band: Band
    decided_by: Literal["rules", "judge"] = "rules"
    note: str | None = Field(default=None, description="why a row stayed ambiguous")


class StepRef(BaseModel):
    """A step the report points a human at: which flow, which step, which second."""

    model_config = ConfigDict(extra="forbid")

    flow_id: str
    order: int
    source_ref: SourceRef | None = None
    reason: str | None = None


class Possibility(BaseModel):
    """A variant flow -- another way the task was done, never an error (RC10)."""

    model_config = ConfigDict(extra="forbid")

    flow_id: str
    ideal_flow_id: str
    diverges_at: int | None = None
    source_ref: SourceRef | None = None
    quote: str | None = Field(default=None, description="verified narration at the divergence")


class ReconcileReport(BaseModel):
    """What reconcile decided, in a form a human can audit. No timestamps (RC11)."""

    model_config = ConfigDict(extra="forbid")

    matches: list[ScreenMatch] = Field(default_factory=list)
    folded: dict[str, str] = Field(default_factory=dict, description="folded id -> canonical id")
    unresolved_steps: list[StepRef] = Field(default_factory=list)
    narration_unverified: list[StepRef] = Field(default_factory=list)
    possibilities: list[Possibility] = Field(default_factory=list)
    kinds: dict[str, int] = Field(default_factory=dict)
    flows_in: int = 0
    flows_out: int = 0
