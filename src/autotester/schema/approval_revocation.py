"""A signed withdrawal of one `RunApproval` (D-018 follow-up, AT-110 key).

Approvals are append-only and `approvals.jsonl` is never edited, so consent is
withdrawn by appending a separate, HMAC-signed row to the sibling file
`approval_revocations.jsonl`. Existing loaders of `approvals.jsonl` are untouched.

A revocation counts only when its signature verifies under `AUTOTESTER_APPROVAL_KEY`:
an unsigned or forged one is ignored, so nobody without the key can revoke (or,
by deleting a revocation, un-revoke without leaving the file visibly changed).
"""

from __future__ import annotations

from collections.abc import Iterable

from autotester.core.ids import SigningKeyMissing, sign_payload, verify_payload
from autotester.schema.approval import RunApproval
from autotester.schema.base import Artifact


class ApprovalRevocation(Artifact):
    """One human's withdrawal of consent previously granted by `approval_id`."""

    approval_id: str
    revoked_by: str
    revoked_at: str
    reason: str
    signature: str = ""

    def _bound_payload(self) -> dict[str, object]:
        return {"kind": "approval_revocation", "approval_id": self.approval_id,
                "revoked_by": self.revoked_by, "revoked_at": self.revoked_at,
                "reason": self.reason}

    def sign(self) -> ApprovalRevocation:
        """Revocation time only; raises `SigningKeyMissing` without the key."""
        object.__setattr__(self, "signature", sign_payload(self._bound_payload()))
        return self

    @property
    def is_valid(self) -> bool:
        """True only for a signature that verifies. Unsigned, forged, or no key -> False."""
        if not self.signature:
            return False
        try:
            return verify_payload(self._bound_payload(), self.signature)
        except SigningKeyMissing:
            return False


def revoked_ids(revocations: Iterable[ApprovalRevocation]) -> set[str]:
    return {r.approval_id for r in revocations if r.is_valid}


def drop_revoked(
    approvals: list[RunApproval], revocations: Iterable[ApprovalRevocation] | None,
) -> list[RunApproval]:
    """`approvals` without any row carrying a valid signed revocation."""
    if not revocations:
        return approvals
    gone = revoked_ids(revocations)
    return [a for a in approvals if a.id not in gone]
