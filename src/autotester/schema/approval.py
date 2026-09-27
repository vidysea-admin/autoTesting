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
problem. Signing happens once, explicitly, at grant time (`sign()`, called
from `cli_crawl.approve_cmd` and the UI grant route) — never implicitly on
load, so listing or displaying existing approvals never requires the key, and
a forged row loaded through the normal read path is never quietly re-signed
by the reader that happens to hold the key.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import Field

from autotester.core.ids import content_id, sign_payload, verify_payload
from autotester.schema.base import Artifact
from autotester.schema.enums import ApprovalKind


class RunApproval(Artifact):
    """One human's authorisation for one kind of run against one target."""

    id: str = ""
    project: str
    run_kind: ApprovalKind
    target: str = Field(description="the exact base_url or endpoint this authorises")
    scope: str = Field(description="what will be read, clicked or sent — in the human's words")
    max_actions: int = 0
    max_probes: int = 0
    wall_clock_s: float = 0.0
    production: bool = Field(
        default=False,
        description="an adversarial run against production requires this to be explicitly true",
    )
    granted_by: str
    granted_at: str
    expires_at: str = Field(description="ISO date/datetime; consent is never open-ended")
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

    def is_expired(self, now: datetime) -> bool:
        try:
            expiry = datetime.fromisoformat(self.expires_at)
        except ValueError:
            return True  # an unparseable expiry is an expired one, never an eternal one
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=UTC)
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)
        return now.astimezone(UTC) > expiry.astimezone(UTC)
