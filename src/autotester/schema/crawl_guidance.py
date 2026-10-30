"""Shapes for model-guided crawl ordering (qa/contracts/crawl-guidance.md G1-G8, D-118).

A model may ORDER one screen's controls and nothing else. Every field here is additive and its
default reproduces the pre-guidance serialized form (G5): the optional fields are `None`, which
`filestore.write_json` omits, and a guidance bound of `None` or 0 means OFF.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

DEFAULT_MODEL_CALL_TIMEOUT_S = 20.0
"""G6: the per-call cap used when `CrawlBounds.model_call_timeout_s` is unset but guidance is on."""
DEFAULT_MODEL_TOTAL_S = 120.0
"""G6: the whole-crawl model-time cap used when `CrawlBounds.model_total_s` is unset."""
MAX_REASON_CHARS = 200


class GuidanceOptIn(BaseModel):
    """G5/D-118 item 3: the per-project egress switch. Absent (None on `Project`) means OFF."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(
        default=False,
        description="True only when the project owner allows redacted control text of this "
                    "product to be sent to the pinned guidance models (G3, D-118 answer a)",
    )


class NextActionRanking(BaseModel):
    """What the model returns for ONE screen: indices into the numbered candidate list, best
    first. Indices only (G1): the model can order a control, never add or describe one."""

    model_config = ConfigDict(extra="forbid")

    ranked: list[int] = Field(description="candidate indices, best first")
    reason: str = Field(default="", description="a short why; scrubbed and capped before storage")

    @field_validator("reason", mode="before")
    @classmethod
    def _cap_reason(cls, value: object) -> object:
        return value[:MAX_REASON_CHARS] if isinstance(value, str) else value


class GuidanceAnnotation(BaseModel):
    """G7: an ADVISORY ranking stored on a knowledge-graph screen node. Never read as coverage,
    identity, a verdict or an approval; what a control does comes from the crawl's own edges."""

    model_config = ConfigDict(extra="forbid")

    source: Literal["model"] = "model"
    candidate_hash: str = Field(description="content hash of the numbered candidate set")
    prompt_version: str = Field(description="skill version + body hash the ranking was made under")
    model: str = Field(description="exact model tag that produced this ranking")
    ranking: list[int] = Field(description="a permutation of the candidate indices")
    reason: str = ""


class GuidanceFallback(BaseModel):
    """One recorded reason a screen used rule order, and how many screens it hit (G4)."""

    model_config = ConfigDict(extra="forbid")

    reason: str
    count: int = 0


class CrawlGuidance(BaseModel):
    """G8: what guidance did during one crawl. Present only when guidance was active."""

    model_config = ConfigDict(extra="forbid")

    mode: Literal["guided", "rule-only (model unavailable)"]
    models_served: list[str] = Field(default_factory=list)
    calls: int = 0
    kg_hits: int = 0
    fallbacks: list[GuidanceFallback] = Field(default_factory=list)
    model_seconds: float = 0.0
    input_tokens: int | None = None
    output_tokens: int | None = None
    stopped: str | None = Field(default=None, description="the cap or breaker that ended guidance")
