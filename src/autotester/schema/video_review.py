"""The typed review of one recording: summary, confirm-list, what was and was not looked at (T-197).

Contract: qa/contracts/team-video-review.md TV3-TV8, TV10. `VideoReview` is what is stored and
exported; `ReviewReply` is the (lenient) shape a model is asked to return, validated item by item
in `stages/video_review_items.py` so one bad item never sinks the review (TV3).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from autotester.schema.base import Artifact
from autotester.schema.enums import Severity
from autotester.schema.video_pointer import PointerLine

Origin = Literal["pointer", "narration", "visual", "suspected"]
ORIGINS: tuple[str, ...] = ("pointer", "narration", "visual", "suspected")
HumanStatus = Literal["open", "confirmed", "dismissed", "fixed"]
ReviewStatus = Literal["ok", "partial", "failed", "unreadable"]
NarrationState = Literal["none", "unreadable", "speech"]
Span = tuple[float, float]
MAX_ITEMS = 5


class RedactionWindow(BaseModel):
    """`[start_s, end_s]` of one source a human blanked out (frames) and muted (audio)."""

    model_config = ConfigDict(extra="forbid")

    start_s: float = Field(ge=0)
    end_s: float

    @model_validator(mode="after")
    def _ordered(self) -> RedactionWindow:
        if self.end_s <= self.start_s:
            raise ValueError("a redaction window must end after it starts")
        return self


class FramePlan(BaseModel):
    """Which seconds will be looked at, and which stretches the reviewer pointed at."""

    model_config = ConfigDict(extra="forbid")

    times: list[float]
    pointer_windows: list[Span] = Field(default_factory=list)


class Spans(BaseModel):
    """`analysed` and `not_reviewed` tile `[0, duration_s]` exactly: no gap, no overlap."""

    model_config = ConfigDict(extra="forbid")

    analysed: list[Span] = Field(default_factory=list)
    not_reviewed: list[Span] = Field(default_factory=list)


class ReviewPlan(BaseModel):
    """The `--dry-run` preview: what a run WOULD do. Producing it makes zero provider calls."""

    model_config = ConfigDict(extra="forbid")

    frame_count: int
    redacted_frame_count: int = 0
    call_count: int
    est_cost_usd: float
    windows: list[RedactionWindow] = Field(default_factory=list)
    pointer_windows: list[Span] = Field(default_factory=list)


class ReplyItem(BaseModel):
    """One item as a model returned it: every field optional, nothing trusted yet."""

    model_config = ConfigDict(extra="ignore")

    time_s: Any = None
    screen: Any = None
    seen: Any = None
    suggestion: Any = None
    severity: Any = None
    source_id: Any = None
    origin: Any = None
    quote: Any = None
    pointer_line: Any = None


class ReviewReply(BaseModel):
    """The shape asked of the model. A reply that does not validate is a `failed` review."""

    model_config = ConfigDict(extra="ignore")

    summary: str = ""
    items: list[ReplyItem] = Field(default_factory=list)


class ConfirmItem(BaseModel):
    """One line of the confirm-list. `status` is a human's; a model can never set it."""

    model_config = ConfigDict(extra="forbid")

    id: str
    time_s: float = Field(ge=0)
    screen: str = Field(min_length=1)
    seen: str = Field(min_length=1)
    suggestion: str = Field(min_length=1)
    severity: Severity
    source_id: str = Field(min_length=1)
    origin: Origin
    quote: str | None = Field(default=None, description="verbatim narration, origin=narration")
    pointer_line: int | None = Field(default=None, description="origin=pointer: its line")
    narration_note: str | None = Field(default=None, description="TV6: what narration there was")
    downgrade: str | None = Field(default=None, description="TV5: why origin became suspected")
    status: HumanStatus = "open"


class RejectedItem(BaseModel):
    """An item that failed validation. Kept with its reason, never rendered, never blank."""

    model_config = ConfigDict(extra="forbid")

    reason: str
    item: dict[str, Any] = Field(default_factory=dict)


class VideoReview(Artifact):
    """The stored review. `id` is derived from content (TV10), never from a clock."""

    id: str
    source_id: str
    status: ReviewStatus
    reason: str | None = Field(default=None, description="why failed / unreadable / partial")
    summary: str = ""
    items: list[ConfirmItem] = Field(default_factory=list, max_length=MAX_ITEMS)
    overflow: list[ConfirmItem] = Field(default_factory=list)
    rejected: list[RejectedItem] = Field(default_factory=list)
    count_note: str | None = None
    narration_state: NarrationState = "none"
    narration_note: str = ""
    coverage_note: str = ""
    duration_s: float = 0.0
    source_sha256: str = ""
    transcript_hash: str = ""
    pointers: list[PointerLine] = Field(default_factory=list)
    redaction_windows: list[RedactionWindow] = Field(default_factory=list)
    frame_times: list[float] = Field(default_factory=list)
    analysed: list[Span] = Field(default_factory=list)
    not_reviewed: list[Span] = Field(default_factory=list)
    calls: int = 0
    cost_usd: float = 0.0

    @model_validator(mode="after")
    def _summary_when_usable(self) -> VideoReview:
        if self.status in ("ok", "partial") and not self.summary.strip():
            raise ValueError("an ok or partial review needs a non-empty flow summary")
        return self
