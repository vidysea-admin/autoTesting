"""Consent as an artifact, not a habit (D-018).

`write_policy` and the HUMAN_GATE files already reach for this informally. This
makes it a file a human writes once and a runner checks every time: what may be
touched, how much of it, until when, and who said so.

The id is content-addressed over **every bound field**, so `core/consent.py`
recomputes it and refuses a row whose id no longer matches its contents.

**What the id alone does and does not buy (AT-110, found by a checker who did
it).** `core.ids.content_id` is an UNKEYED sha256, so the id is recomputable by
anyone who can write the file — including the agent this gate exists to bound.
Deleting the `id` field is enough: `model_post_init` mints a matching one. So
the id detects a **careless or accidental edit**, not a determined forger; a
checker widened a 12-action grant to 9999 with `production` flipped true,
dropped the id, and ran a 500-action crawl on it.

**What closes that (AT-110, Umesh's decision, `qa/gates/at110-approval-forgery.md`,
option 1).** `signature` is a separate HMAC-SHA256 over the same bound payload,
keyed from `AUTOTESTER_APPROVAL_KEY` in the repo-root `.env` (`core.ids.sign_payload`
/ `verify_payload`). `core/consent.py` refuses a row whose signature is missing
or does not verify. **The honest guarantee: tamper-proof against anyone who
does not hold the `.env` key** — an operator's careless edit AND a confused or
adversarial agent that can write `approvals.jsonl` are both stopped, because
neither can produce a valid signature without the key. **It is not proof
against an agent that can edit the code itself** (e.g. `core/consent.py`, or
this file) — that agent could as easily remove the check as forge a row, and
no on-disk scheme defends against a party that can rewrite the checker. That
is out of scope for a consent *file*; it is a different, code-integrity
problem.

**Standing grants (D-111).** A crawl approval (explore runs under it) may carry
`standing=True` and no `expires_at`: it is valid until a signed `ApprovalRevocation`
names it. `standing` joins the bound payload ONLY when true, so every existing dated
row keeps the id and signature it was granted under, while flipping it on a dated row
changes both and is refused. Any other kind with no expiry (adversarial above all) reads
as expired, never eternal. Per-run caps are unchanged.

Signing happens once, explicitly, at grant time (`sign()`, called
from `cli_crawl.approve_cmd` and the UI grant route) — never implicitly on
load, so listing or displaying existing approvals never requires the key, and
a forged row loaded through the normal read path is never quietly re-signed
by the reader that happens to hold the key.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import NamedTuple

from pydantic import Field

from autotester.core.ids import content_id, sign_payload, verify_payload
from autotester.schema.base import Artifact
from autotester.schema.enums import ApprovalKind

STANDING_KINDS = frozenset({ApprovalKind.CRAWL})
"""D-111: the run kinds that may be granted standing. Explore runs under CRAWL. ADVERSARIAL is
deliberately absent -- it fires hostile input and keeps a required expiry."""

PROBES_PER_ACTION = 20
MAX_GRANT_ACTIONS = 2000
MAX_GRANT_WALL_CLOCK_S = 86400.0
MAX_GRANT_DAYS = 30
MAX_GRANT_PROBES = MAX_GRANT_ACTIONS * PROBES_PER_ACTION  # the UI form's cap (AT-675)
GRANT_SAFETY_MARGIN = 1.25   # headroom a derived LIVE_CASE grant adds over the planned run


class GrantBounds(NamedTuple):
    actions: int
    probes: int
    wall_clock_s: float


def derive_grant_bounds(
    kind: ApprovalKind, actions: int, probes: int, wall_clock_s: float,
) -> GrantBounds:
    """The ONE derivation of the bounds a grant carries (D-112 item 2); the refusal hint,
    `approve` with the flags omitted and the UI pre-fill all call it. A LIVE_CASE run's planned
    actions and time get `GRANT_SAFETY_MARGIN`, in whole units, within the grant ceilings;
    probes are `max(floor, actions x PROBES_PER_ACTION)` (the D-068 brake) up to
    `MAX_GRANT_PROBES`. 0 means not asked; any other kind passes through unchanged."""
    if kind is not ApprovalKind.LIVE_CASE:
        return GrantBounds(actions, probes, wall_clock_s)
    wide = min(math.ceil(actions * GRANT_SAFETY_MARGIN), MAX_GRANT_ACTIONS) if actions else 0
    wall = (min(float(math.ceil(wall_clock_s * GRANT_SAFETY_MARGIN)), MAX_GRANT_WALL_CLOCK_S)
            if wall_clock_s and math.isfinite(wall_clock_s) else wall_clock_s)
    wide_probes = min(max(probes, wide * PROBES_PER_ACTION), MAX_GRANT_PROBES) if probes else 0
    return GrantBounds(wide, wide_probes, wall)


class RunApproval(Artifact):
    """One human's authorisation for one kind of run against one target."""

    id: str = ""
    project: str
    run_kind: ApprovalKind
    target: str = Field(description="the exact base_url or endpoint this authorises")
    scope: str = Field(description="what will be read, clicked or sent — in the human's words")
    max_actions: int = Field(
        default=0,
        description="how many actions this run may spend in total. ZERO MEANS ZERO: an approval "
                    "that grants 0 authorises no action at all, it does not mean 'unbounded' "
                    "(AT-660/CN10 — `core/consent.py::_shortfalls` always read it this way; "
                    "`RunBudget.try_consume` used to read the same 0 as unlimited, and the "
                    "permissive side governed the run). Chosen by the AT-570 build as the "
                    "fail-closed direction; awaiting ratification.",
    )
    max_probes: int = Field(
        default=0,
        description="how many probes this run may spend in total. ZERO MEANS ZERO, as above. "
                    "Every row in `projects/pathlynks/approvals.jsonl` carries 0 here, so this "
                    "is the field where the old truthiness guard was live on disk.",
    )
    wall_clock_s: float = Field(
        default=0.0, allow_inf_nan=False,
        description="how many seconds this run may take in total. ZERO MEANS ZERO, as above: an "
                    "approval granting 0 seconds authorises no time. Present-and-non-zero is not "
                    "the same as plausible — the live pathlynks row grants 600000000.0s (19 "
                    "years) and nothing here rejects it; CN10 requires that bound be REPORTED "
                    "(`schema/run.py::RunBounds`), not capped, because the ceiling is a gate "
                    "decision and not a build's.",
    )
    production: bool = Field(
        default=False,
        description="an adversarial run against production requires this to be explicitly true",
    )
    granted_by: str
    granted_at: str
    expires_at: str | None = Field(
        default=None,
        description="ISO date/datetime the grant lapses. None is valid ONLY for a STANDING "
                    "grant (D-111); a non-standing row with none reads as expired, never eternal",
    )
    standing: bool = Field(
        default=False,
        description="D-111: valid until a signed `ApprovalRevocation` names it, instead of until "
                    "a date. Crawl (and so explore) only -- an adversarial approval keeps a "
                    "required expiry. Bound into the signed payload, so a dated row cannot be "
                    "re-read as standing.",
    )
    note: str | None = None
    signature: str = Field(
        default="",
        description="HMAC-SHA256 of the bound payload, keyed from AUTOTESTER_APPROVAL_KEY "
                    "(AT-110). Empty means unsigned — legacy or forged, either way refused.",
    )

    def _bound_payload(self) -> dict[str, object]:
        """Every field that limits what the run may do. Changing any of them
        changes the id, which is how tampering is detected."""
        return {
            "project": self.project, "run_kind": str(self.run_kind), "target": self.target,
            "scope": self.scope, "max_actions": self.max_actions, "max_probes": self.max_probes,
            "wall_clock_s": self.wall_clock_s, "production": self.production,
            "granted_by": self.granted_by, "granted_at": self.granted_at,
            "expires_at": self.expires_at,
            # Only when true: a dated row keeps the exact payload (so id and signature) it
            # was granted under, while flipping `standing` on it changes both (D-111).
            **({"standing": True} if self.standing else {}),
        }

    def model_post_init(self, _context: object) -> None:
        if not self.id:
            object.__setattr__(self, "id", content_id("appr", self._bound_payload()))

    @property
    def computed_id(self) -> str:
        return content_id("appr", self._bound_payload())

    @property
    def is_intact(self) -> bool:
        """False when the row was edited after it was granted — the point of
        content-addressing it. `note` is deliberately outside the payload, so a
        human may annotate an approval without invalidating it."""
        return self.id == self.computed_id

    def sign(self) -> RunApproval:
        """Attach this approval's HMAC signature — GRANT TIME ONLY.

        Explicit and never automatic: `model_post_init` mints `id` for every
        freshly-built row (including a forged one loaded with its `id` key
        removed), so auto-signing there would let the read path itself
        re-sign a forged row the instant the *reader's* environment holds the
        key — which is exactly the party AT-110 needs the signature to bind
        against, not the party doing the forging. Only an explicit `sign()`
        call from a real grant (the CLI `approve` command, the UI grant
        route) may produce a valid signature.

        Raises `SigningKeyMissing` if `AUTOTESTER_APPROVAL_KEY` is not
        configured — callers must refuse the grant rather than write an
        unsigned row. Returns `self` so a call site can write
        `RunApproval(...).sign()` in one expression."""
        object.__setattr__(self, "signature", sign_payload(self._bound_payload()))
        return self

    @property
    def is_signed_and_verified(self) -> bool:
        """False for an empty signature — never raises for that case; a
        legacy or forged row simply reads as unverifiable. A MISSING KEY still
        raises `SigningKeyMissing`: "no key configured" and "this row has no
        signature" are different problems, and a caller must be able to tell
        an operator which one it is rather than silently treating both as
        acceptance."""
        if not self.signature:
            return False
        return verify_payload(self._bound_payload(), self.signature)

    @property
    def is_standing(self) -> bool:
        """A grant with no end date that the gate may honour (D-111): crawl kind only,
        and carrying no expiry. Anything else with no expiry is expired, never eternal."""
        return self.standing and self.expires_at is None and self.run_kind in STANDING_KINDS

    def is_expired(self, now: datetime) -> bool:
        if self.is_standing:
            return False  # ends only by a signed revocation
        if self.expires_at is None:
            return True
        try:
            expiry = datetime.fromisoformat(self.expires_at)
        except ValueError:
            return True  # an unparseable expiry is an expired one, never an eternal one
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=UTC)
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)
        return now.astimezone(UTC) > expiry.astimezone(UTC)
