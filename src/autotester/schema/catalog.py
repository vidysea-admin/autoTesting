"""The test catalog: schema for `stages/catalog.py::catalog()`'s output.

Contract: qa/contracts/catalog.md CT1-CT8, authorized by D-039. Says, per
`CaseClass`, whether it applies to this project, whether it can run right now,
and — when it cannot — the one reason (a closed vocabulary) plus the one
action that clears it. `BlockedReason` and `Tier` live here, not in
`schema/enums.py`, because D-039 names this file as their home and CT7 checks
for exactly one definition of each in `src/`.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from autotester.schema.ai_check import AiCheckKind, AiCheckMethod
from autotester.schema.base import Artifact
from autotester.schema.enums import CaseClass


class BlockedReason(StrEnum):
    """Why a `CatalogEntry` is not runnable. Closed by D-039 — exactly six
    values, no more, no fewer (CT3)."""

    NO_FLOWSPEC = "no_flowspec"
    FLOWSPEC_NOT_APPROVED = "flowspec_not_approved"
    MISSING_CREDENTIAL = "missing_credential"
    NO_GROUND_TRUTH = "no_ground_truth"
    NEEDS_WRITE_POLICY = "needs_write_policy"
    NO_LIVE_ENDPOINT = "no_live_endpoint"


class Tier(StrEnum):
    """Cheap -> expensive ordering (D-039). `routes_runs.py`'s tiered dispatch
    runs STATIC, then BEHAVIOURAL, then ADVERSARIAL, including empty tiers (CT6)."""

    STATIC = "static"
    BEHAVIOURAL = "behavioural"
    ADVERSARIAL = "adversarial"


TIER_ORDER: tuple[Tier, ...] = (Tier.STATIC, Tier.BEHAVIOURAL, Tier.ADVERSARIAL)

TIER_BY_CLASS: dict[CaseClass, Tier] = {
    # STATIC: a rendered/filled form, no deliberate failure or repeated action.
    CaseClass.HAPPY: Tier.STATIC,
    CaseClass.INPUT_EMPTY: Tier.STATIC,
    CaseClass.INPUT_BOUNDARY: Tier.STATIC,
    CaseClass.INPUT_UNICODE_OVERSIZE: Tier.STATIC,
    CaseClass.VIEWPORT_MOBILE: Tier.STATIC,
    CaseClass.LOCALE_I18N: Tier.STATIC,
    CaseClass.REGRESSION_ANCHOR: Tier.STATIC,
    # BEHAVIOURAL: a sequence across time/tabs/history, still no injected failure.
    CaseClass.DOUBLE_SUBMIT: Tier.BEHAVIOURAL,
    CaseClass.BACK_REFRESH_MIDFLOW: Tier.BEHAVIOURAL,
    CaseClass.DEEPLINK_UNAUTH: Tier.BEHAVIOURAL,
    CaseClass.CONCURRENT_TAB: Tier.BEHAVIOURAL,
    # ADVERSARIAL: a deliberately broken credential, session or backend/network.
    CaseClass.AUTH_WRONG_CREDS: Tier.ADVERSARIAL,
    CaseClass.AUTH_EXPIRED_SESSION: Tier.ADVERSARIAL,
    CaseClass.SERVER_ERROR: Tier.ADVERSARIAL,
    CaseClass.NETWORK_OFFLINE_SLOW: Tier.ADVERSARIAL,
}
"""Every `CaseClass` maps to exactly one tier (CT6: a total ordering). A test
pins that this dict's key set equals `set(CaseClass)`."""


class CatalogEntry(BaseModel):
    """One `CaseClass`'s standing for one project: applicable, runnable, and
    — when blocked — why, and the one action that clears it (CT8)."""

    model_config = ConfigDict(extra="forbid")

    case_class: CaseClass
    tier: Tier
    applicable: bool
    runnable: bool
    blocked_reason: BlockedReason | None = None
    unblock_action: str | None = Field(
        default=None,
        description="human text naming the one action that clears blocked_reason; "
                    "set exactly when blocked_reason is set (CT3, CT8)",
    )


class StandardPack(StrEnum):
    """A named flow pattern the team's own release checklist calls out, on top
    of the generic `CaseClass` taxonomy (AT-588, 2026-09-26 meeting review):
    Google OAuth sign-up data carry-over, a month/year picker, and an Excel
    upload with column mapping. Detected structurally from the `FlowSpec` in
    `stages/catalog.py` — never guessed by a model (same discipline as
    `CaseClass`)."""

    OAUTH_SIGNUP_CARRYOVER = "oauth_signup_carryover"
    DATE_PICKER_MONTH_YEAR = "date_picker_month_year"
    EXCEL_COLUMN_MAPPING = "excel_column_mapping"


class PackEntry(BaseModel):
    """One `StandardPack`'s standing for one project. Reuses `BlockedReason`
    (CT7: no second such enum lives in this repo) rather than inventing
    pack-specific reasons. `applicable=False, blocked_reason=None` means the
    FlowSpec simply does not contain this pattern — distinct from *blocked*,
    where the pattern exists but the pack cannot run yet."""

    model_config = ConfigDict(extra="forbid")

    pack: StandardPack
    applicable: bool
    runnable: bool
    blocked_reason: BlockedReason | None = None
    unblock_action: str | None = Field(
        default=None,
        description="human text naming the one action that clears blocked_reason; "
                    "set exactly when blocked_reason is set",
    )


class AiCheckEntry(BaseModel):
    """One Track C `AiCheckKind`'s standing for one AI target (T-152, ai-target.md AI4-AI5).
    Reuses `BlockedReason` (CT7: no second enum). `applicable=False` means the target's kind
    does not take this check, which is distinct from *blocked*: an applicable check that
    cannot run always names its one reason and the one action that clears it."""

    model_config = ConfigDict(extra="forbid")

    kind: AiCheckKind
    tier: Tier
    method: AiCheckMethod
    applicable: bool
    runnable: bool
    blocked_reason: BlockedReason | None = None
    unblock_action: str | None = None

    @model_validator(mode="after")
    def _blocked_means_named(self) -> AiCheckEntry:
        blocked = self.applicable and not self.runnable
        if blocked != (self.blocked_reason is not None) or blocked != (
                self.unblock_action is not None):
            raise ValueError("a blocked check carries a reason and an action; no other does")
        if self.runnable and not self.applicable:
            raise ValueError("a check that does not apply cannot be runnable")
        return self


class Catalog(Artifact):
    """One project's whole catalog: every `CaseClass`, exactly once (CT2),
    plus the AT-588 standard packs."""

    project: str
    entries: list[CatalogEntry] = Field(default_factory=list)
    packs: list[PackEntry] = Field(default_factory=list)
    ai_checks: list[AiCheckEntry] = Field(default_factory=list)
    """Track C (T-152): empty for a web-only project; filled by `stages/ai_catalog.match`."""

    def ai_check(self, kind: AiCheckKind) -> AiCheckEntry | None:
        return next((c for c in self.ai_checks if c.kind == kind), None)

    @property
    def ai_runnable_count(self) -> int:
        return sum(1 for c in self.ai_checks if c.runnable)

    def runnable_ai_in_tier(self, tier: Tier) -> list[AiCheckEntry]:
        return [c for c in self.ai_checks if c.tier == tier and c.runnable]

    def entry(self, case_class: CaseClass) -> CatalogEntry | None:
        return next((e for e in self.entries if e.case_class == case_class), None)

    def pack(self, pack: StandardPack) -> PackEntry | None:
        return next((p for p in self.packs if p.pack == pack), None)

    @property
    def runnable_count(self) -> int:
        return sum(1 for e in self.entries if e.runnable)

    def runnable_in_tier(self, tier: Tier) -> list[CatalogEntry]:
        return [e for e in self.entries if e.tier == tier and e.runnable]
