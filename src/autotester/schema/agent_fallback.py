"""Typed shapes for the browser-use fallback actuator (T-177, qa/contracts/agent-fallback.md).

One job: say exactly what an agent-driven attempt on an unknown screen may return. The actuator
reports what it did and saw; it never carries a verdict (C7) -- `FallbackStatus` has no PASS.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class FallbackActionKind(StrEnum):
    CLICK = "click"
    FILL = "fill"
    SELECT = "select"
    UPLOAD = "upload"
    NAVIGATE = "navigate"
    PRESS_KEY = "press_key"
    SCROLL = "scroll"
    BACK = "back"
    WAIT = "wait"


class FallbackAction(BaseModel):
    """One action the agent chose, as the guards see it (AF3)."""

    model_config = ConfigDict(extra="forbid")

    kind: FallbackActionKind
    target: str = Field(default="", description="the control's accessible name, or a locator")
    role: str = "button"
    value: str | None = None
    url: str | None = Field(
        default=None,
        description="the destination of a navigate, or the page URL after the action (X7)")
    is_form_submit: bool = False


class ActuatorResult(BaseModel):
    """What a backend returns after driving the page: the actions taken, what it observed and
    where the evidence is (AF2). Free text alone is not a result -- every field is required."""

    model_config = ConfigDict(extra="forbid")

    actions: list[FallbackAction] = Field(min_length=1)
    observed: str = Field(min_length=1, description="what the page showed afterwards")
    evidence_ref: str = Field(min_length=1, description="run-relative screenshot or DOM path")
    resolved: bool = Field(description="the agent believes the screen is now understood")


class FallbackStatus(StrEnum):
    """How an invocation ended. Deliberately no PASS: only `grade.py` writes a verdict."""

    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    BOUND_EXHAUSTED = "bound_exhausted"
    REFUSED = "refused"
    MALFORMED = "malformed"
    FAILED = "failed"


class FallbackOutcome(BaseModel):
    """The adapter's whole answer for one invocation. `reason` names the bound, the refusal or
    the malformed field, so an inconclusive end is never silent (O4)."""

    model_config = ConfigDict(extra="forbid")

    status: FallbackStatus
    reason: str = ""
    steps_used: int = Field(default=0, ge=0)
    result: ActuatorResult | None = None
    vetted: list[FallbackAction] = Field(default_factory=list)
    refusals: list[str] = Field(default_factory=list)
