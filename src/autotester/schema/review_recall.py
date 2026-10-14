"""The TA16 evidence record: a video review measured against an oracle, in numbers (T-206).

Contract: qa/contracts/team-loop-acceptance.md TA16. Numbers only; no pass threshold exists
(intent Q3), and the oracle's provenance label travels with every figure (D-094).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from autotester.schema.base import Artifact


class OracleRef(BaseModel):
    """Where the denominator came from. Never a claim of independence."""

    model_config = ConfigDict(extra="forbid")

    corpus_id: str
    mode: str
    provenance: str
    recall_basis: str = Field(description="e.g. 'AI-assisted video review, not independent'")
    severity: str
    file_sha256: str


class ReviewRecall(Artifact):
    """`recall.json`. `k` and `unconfirmed_count` must be re-derivable from the id lists."""

    id: str
    claim: str = "measured on {n_sources} videos"
    oracle: OracleRef
    independent: bool = False
    threshold: str = "none (intent Q3 carried)"
    match_method: str = "automatic lexical (conservative, untuned)"
    match_thresholds: dict[str, float] = Field(default_factory=dict)
    n: int = Field(ge=0, description="oracle rows at the chosen severity")
    k: int = Field(ge=0, description="of those, rows with at least one matched review item")
    recall: float | None = None
    found_ids: list[str] = Field(default_factory=list)
    missed_ids: list[str] = Field(default_factory=list)
    matches: dict[str, list[str]] = Field(default_factory=dict)
    items_total: int = 0
    unconfirmed_ids: list[str] = Field(default_factory=list)
    unconfirmed_count: int = 0
    sources: list[str] = Field(default_factory=list)
    review_ids: list[str] = Field(default_factory=list)
    redaction_windows: dict[str, list[tuple[float, float]]] = Field(default_factory=dict)
    not_reviewed: dict[str, list[tuple[float, float]]] = Field(default_factory=dict)
    review_status: dict[str, str] = Field(default_factory=dict)
    calls: int = 0
    cost_usd: float = 0.0
    time_to_review_s: float | None = None
    time_to_review_note: str = ""
    request_log_ref: str | None = None
    request_log_sha256: str | None = None
