"""Crawl-safety and crawl-envelope primitives (Track B).

`DialogEvent` shipped at B1. B2 adds the schema the crawl stage itself
(B3) and the safety layer (B4) need: bounds that actually stop a BFS,
a policy the explorer consults before every action, and the envelope
artifact persisted per crawl.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from autotester.core.ids import content_id, run_id
from autotester.schema.base import Artifact
from autotester.schema.enums import CrawlStatus, IssueKind, TraversalStrategy, WritePolicy


class DialogEvent(BaseModel):
    """One JS dialog (`alert`/`confirm`/`prompt`/`beforeunload`) the observer saw."""

    model_config = ConfigDict(extra="forbid")

    dialog_type: str
    message: str = ""
    accepted: bool = False


# D-016's default deny-list: destructive-name patterns a READ_ONLY/TEST_ACCOUNT
# crawl never clicks. Word-bounded so "Deliverables" doesn't match "deliver".
DEFAULT_DENY_PATTERNS = (
    r"\bdelete\b", r"\bremove\b", r"\bdeactivate\b", r"\bdisable\b", r"\barchive\b",
    r"\bpurge\b", r"\bdrop\b", r"\breset\b", r"\brevoke\b", r"\bterminate\b",
    r"\bcancel subscription\b", r"\bpay\b", r"\bcheckout\b", r"\bsend\b", r"\bsubmit\b",
    r"\bapprove\b", r"\breject\b", r"\bpublish\b", r"\bunsubscribe\b",
    r"\b(?:close|cancel|end|stop)\b (?:\w+ ){0,3}(?:account|subscriptions?|memberships?|plan|"
    r"auto ?renew\w*)\b"
    r"(?! settings$)",
    r"\bturn off (?:\w+ )?auto ?renew",
)

# Never clicked at ANY write_policy, including ALLOW_WRITES. The [\s\w]{0,10}
# gap tolerates "Log me out"/"Sign yourself out" without over-matching an
# unrelated sentence (bounded width, not `.*`).
DEFAULT_NEVER_CLICK_PATTERNS = (
    r"\blog ?out\b", r"\blog\b[\s\w]{0,10}\bout\b",
    r"\bsign ?out\b", r"\bsignout\b", r"\bsign\b[\s\w]{0,10}\bout\b",
)

# Third-party hosts whose failed requests are noise, never an issue.
DEFAULT_THIRD_PARTY_IGNORE = (
    "google-analytics.com", "googletagmanager.com", "doubleclick.net",
    "facebook.net", "connect.facebook.net", "hotjar.com", "clarity.ms",
    "sentry.io", "segment.io", "intercom.io", "fonts.gstatic.com", "fonts.googleapis.com",
)


class CrawlBounds(BaseModel):
    """Bounds the BFS actually stops on — every field must be able to end
    the crawl and name itself as `Crawl.stop_reason` (X4)."""

    model_config = ConfigDict(extra="forbid")

    max_screens: int = 30
    max_actions: int = 200
    wall_clock_s: float = 600.0
    max_depth: int = 6
    per_node_action_cap: int = 25
    dialog_repeat_limit: int = 3
    settle_ms: int = Field(
        default=2500,
        description="per-action settle ceiling. Deliberately far below the 8s a graded "
        "test case waits: a crawl performs hundreds of actions, and a page whose "
        "third-party requests never resolve would otherwise cost the full ceiling every "
        "single time (measured: a 60-action crawl of the fixture site took >5 minutes at "
        "8s, because one page fetches unreachable analytics hosts)",
    )
    heartbeat_every_actions: int = 5
    """AT-483: `explore_node` re-persists the crawl envelope after the 1st action and
    every Nth one after that -- the liveness signal `explore_status.displayed_status`
    checks, paired with `heartbeat_stale_after_s` below rather than compared against
    `started_at` alone (a legitimately long crawl must never be misjudged as dead)."""
    heartbeat_stale_after_s: float = 90.0
    """AT-483: how many seconds `Crawl.heartbeat_at` may sit unmoved before a RUNNING
    crawl displays as interrupted -- comfortably above `heartbeat_every_actions`
    actions at the measured ~2.8s/action pace. Display-only; `crawl.json` is never
    rewritten because of this."""


class SafetyPolicy(BaseModel):
    """What the explorer will and won't click, given a project's `write_policy`."""

    model_config = ConfigDict(extra="forbid")

    write_policy: WritePolicy = WritePolicy.READ_ONLY
    deny_patterns: list[str] = Field(default_factory=lambda: list(DEFAULT_DENY_PATTERNS))
    never_click_patterns: list[str] = Field(
        default_factory=lambda: list(DEFAULT_NEVER_CLICK_PATTERNS)
    )
    third_party_ignore: list[str] = Field(
        default_factory=lambda: list(DEFAULT_THIRD_PARTY_IGNORE)
    )
    click_unnamed: bool = False
    synthetic_typing: bool = Field(
        default=False,
        description="X10-b (D-029): the crawler may type SYNTHETIC, non-PII, "
        "deterministic values into post-login form fields. Deliberately OFF by "
        "default — a run sets it only when all four conditions hold "
        "(TEST_ACCOUNT/ALLOW_WRITES + synthetic values + non-production target + "
        "non-destructive); typing_allowed() is the one gate that reads it.",
    )


class CrawlIssue(Artifact):
    """One problem the crawl noticed — console error, failed first-party
    request, an off-domain navigation attempt, or a dialog storm."""

    id: str = ""
    crawl_id: str
    project: str
    kind: IssueKind
    node_id: str
    detail: str
    first_party: bool = True

    def model_post_init(self, _context: object) -> None:
        if not self.id:
            payload = {"crawl_id": self.crawl_id, "node_id": self.node_id,
                       "kind": str(self.kind), "detail": self.detail}
            object.__setattr__(self, "id", content_id("cissue", payload))


class CoverageHole(BaseModel):
    """One control the crawl discovered and did not perform, with the ONE reason why (V7b)."""

    model_config = ConfigDict(extra="forbid")

    node_id: str
    url_template: str
    selector: str
    name: str = ""
    reason: str = Field(description="bound:<name> | policy:<rule> | unnamed | off_domain | "
                                    "error | login_wall | not_visited | skipped_unchanged | "
                                    "not_reached")


class PermittedControl(BaseModel):
    """One control the supplied account's role PERMITS (coverage.md V9).

    Declared per project, because nothing we test offers role introspection: the
    permitted surface is either declared or unknown, and a figure computed against
    what a bounded crawl happened to reach must SAY it is not permission coverage
    rather than pass itself off as one.
    """

    model_config = ConfigDict(extra="forbid")

    url_template: str
    selector: str
    name: str = ""
    destructive: bool = Field(
        default=False,
        description="the account may do it, but it is undone by nothing (delete/send/pay). "
                    "Still part of the denominator (V9: a blocked control never counts as "
                    "covered, it is REPORTED blocked); a run below ALLOW_WRITES lists it as "
                    "policy:destructive under <write_policy> rather than dropping it.",
    )


class CrawlCoverage(BaseModel):
    """What a crawl covered, stated by the crawl itself (coverage.md V7). The books balance:
    `controls_exercised + len(holes) == controls_discovered`."""

    model_config = ConfigDict(extra="forbid")

    controls_discovered: int = 0
    controls_exercised: int = 0
    screens_reached: int = 0
    screens_queued_unvisited: int = 0
    percent: int = Field(default=0, description="floor(exercised / discovered * 100); never "
                                                "100 for a crawl that did not complete (V7d)")
    holes: list[CoverageHole] = Field(default_factory=list)
    screens_not_entered: list[CoverageHole] = Field(
        default_factory=list, description="screens a link led to that a bound kept the crawl "
                                          "from entering (max_depth / max_screens) — AT-470")
    denominator_basis: Literal["permitted", "screens-reached"] = Field(
        default="screens-reached",
        description="V9: what `percent` is a fraction OF. `permitted` = the controls the "
                    "supplied account's role permits (project.permitted_surface). "
                    "`screens-reached` = the controls a bounded crawl happened to find, which "
                    "is NOT permission coverage and every surface must say so.")
    permitted_total: int | None = None
    permitted_exercised: int | None = None
    permitted_holes: list[CoverageHole] = Field(
        default_factory=list,
        description="V9: every PERMITTED control not exercised, each named, each with one "
                    "closed-set reason. `not_reached` is a reason, not an absence of one.")
    spec_screens_reached: int | None = None
    spec_screens_total: int | None = None
    spec_error: str | None = Field(default=None, description="why the FlowSpec could not be "
                                                             "read for the spec counts (AT-472)")
    error: str | None = Field(default=None, description="why coverage could not be computed; "
                                                        "the crawl record is kept regardless")

    def by_reason(self) -> dict[str, int]:
        return _tally(self.holes)

    def permitted_by_reason(self) -> dict[str, int]:
        """V9's breakdown: the permitted controls NOT exercised, by reason."""
        return _tally(self.permitted_holes)


def _tally(holes: list[CoverageHole]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for hole in holes:
        counts[hole.reason] = counts.get(hole.reason, 0) + 1
    return dict(sorted(counts.items()))


class NoiseCount(BaseModel):
    """One third-party host's dropped-request tally (never an issue, X9)."""

    model_config = ConfigDict(extra="forbid")

    host: str
    count: int = 0


class Crawl(Artifact):
    """The envelope for one bounded BFS run — `stages/explore.py`'s output."""

    id: str = Field(default_factory=lambda: run_id("crawl"))
    project: str
    status: CrawlStatus = CrawlStatus.RUNNING
    bounds: CrawlBounds = Field(default_factory=CrawlBounds)
    policy: SafetyPolicy = Field(default_factory=SafetyPolicy)
    login_case_id: str | None = None
    strategy: TraversalStrategy = TraversalStrategy.BFS
    """CR1: `bfs` is byte-identical to the original FIFO frontier; `hybrid` adds a
    bounded depth-first descent per workflow under the SAME X4 bounds."""
    incremental: bool = False
    """CR3: whether this crawl was seeded from `portal_persona.json` (a screen whose
    stored `(key, signature)` still matches is skipped). OFF by default."""
    skipped_unchanged: int = 0
    """CR3/CR5: screens skipped as unchanged. Counted APART from `screens` for the
    same reason `tool_failures` is counted apart from `issues`: a number a human
    reads as "screens explored" must never silently include screens nobody looked
    at. A non-zero value here means this crawl did NOT explore the whole portal."""
    approval_id: str | None = Field(
        default=None, description="the RunApproval whose check passed at the start gate; "
                                  "None only on a crawl recorded before this field existed")
    approval_production: bool | None = Field(
        default=None, description="that approval's `production` flag, copied at the gate")
    provider: str | None = Field(
        default=None,
        description="the model provider that judged this crawl; None for every shipped crawl, "
        "which makes no model call (explore.md X4). A record written before this field was "
        "honest says 'mock' (the old schema default, not a stub judge) and reads back as None",
    )
    started_at: str | None = None
    finished_at: str | None = None
    stop_reason: str | None = None
    screens: int = 0
    edges: int = 0
    actions: int = 0
    denied: int = 0
    issues: int = 0
    """Problems found in the PRODUCT under test. `IssueKind.EVIDENCE` is
    deliberately excluded — see `tool_failures` (AT-120)."""
    tool_failures: int = 0
    """Times the crawler itself failed to record something. Counted apart for
    the same reason `noise_counts` is: a number a human reads as "bugs in my
    product" must not silently include the tool's own failures. Kept as a
    count rather than dropped so "we did not report it" stays auditable."""
    noise_counts: list[NoiseCount] = Field(default_factory=list)
    coverage: CrawlCoverage | None = Field(
        default=None, description="V7; None on a crawl recorded before coverage existed")
    @field_validator("provider", mode="before")
    @classmethod
    def _legacy_mock_default(cls, value: object) -> object:
        return None if value == "mock" else value

    heartbeat_at: str | None = None
    """AT-483: refreshed mid-BFS by `explore_node`, alongside a fresh snapshot of the
    progress counts above -- absent (None, and so omitted from disk by `write_json`'s
    `exclude_none`) on every crawl.json written before this unit, which is exactly the
    X18(d) legacy shape: nothing to compare, so it is never flagged."""
