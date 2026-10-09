"""Track C check vocabulary: which behavioural checks exist for an AI target (D-017).

Closed enums only. Which checks apply to a target kind is decided by a literal table in
`stages/ai_catalog.py`, never by a model; how a check is decided (code or judge) is a
literal fact recorded there as well.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from autotester.schema.base import Artifact


class AiCheckKind(StrEnum):
    """One behavioural check an AI target can be put through. Enum order is report order."""

    RESPONSE_SHAPE = "response_shape"
    LATENCY_BUDGET = "latency_budget"
    GROUND_TRUTH_ANSWER = "ground_truth_answer"
    TOOL_USE = "tool_use"
    HANDOFF_ORDER = "handoff_order"


class AiCheckMethod(StrEnum):
    """Who decides a check: code from recorded facts, or the independent judge (C7)."""

    COMPUTED = "computed"
    JUDGED = "judged"


class AiReply(BaseModel):
    """What an AI endpoint answered, as the transport seam hands it to the capturer."""

    model_config = ConfigDict(extra="forbid")

    status: int | None = None
    text: str = ""
    tools_called: list[str] = Field(default_factory=list)
    handoffs: list[str] = Field(default_factory=list)


class AiExchange(BaseModel):
    """One prompt and what was observed of its answer. Facts only: no verdict lives here (C7).
    Every string has passed `Redactor.scrub` before it is stored (C5)."""

    model_config = ConfigDict(extra="forbid")

    prompt: str
    response: str = ""
    status: int | None = None
    latency_s: float = Field(ge=0, allow_inf_nan=False)
    tools_called: list[str] = Field(default_factory=list)
    handoffs: list[str] = Field(default_factory=list)
    is_json: bool = False
    missing_keys: list[str] = Field(default_factory=list)
    error: str | None = Field(
        default=None, description="fixed transport category, never exception text"
    )


class AiCapture(Artifact):
    """A captured run of one check against one endpoint: observation, never judgement."""

    project: str
    endpoint: str
    check: AiCheckKind
    expected_keys: list[str] = Field(default_factory=list)
    exchanges: list[AiExchange] = Field(default_factory=list)
    unsent_prompts: int = Field(default=0, ge=0, description="prompts the wall clock cut off")
