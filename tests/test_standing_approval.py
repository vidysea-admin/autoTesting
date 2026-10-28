"""D-111: a crawl approval may be STANDING -- valid until a signed revocation names it.

The schema and the consent gate. The CLI and UI grant paths are in
`test_standing_approval_grant.py`. What must hold: a standing crawl row passes the gate
with no expiry; an adversarial one never does; the signature binds `standing` so a dated
row cannot be re-read as standing; every per-run cap and the production flag still bind;
a signed revocation ends it.

Contract: qa/contracts/consent.md CN3-CN4 (the CN4 expiry criterion is amended by the
checker, D-111).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from autotester.core.consent import (
    ApprovalRequired,
    require_approval,
    validate_grant_bounds,
)
from autotester.schema.approval import RunApproval
from autotester.schema.approval_revocation import ApprovalRevocation
from autotester.schema.enums import ApprovalKind

URL = "https://demo.test/"
FAR_FUTURE = datetime(2099, 1, 1, tzinfo=UTC)


def _row(*, standing: bool, kind: ApprovalKind = ApprovalKind.CRAWL, **over: object) -> RunApproval:
    fields: dict[str, object] = dict(
        project="demo", run_kind=kind, target=URL, scope="s", max_actions=50, max_probes=5,
        wall_clock_s=600.0, granted_by="umesh", granted_at="2026-10-28",
        expires_at=None if standing else (datetime.now(UTC) + timedelta(days=3)).isoformat(),
        standing=standing)
    fields.update(over)
    return RunApproval(**fields).sign()


def _check(row: RunApproval, *, kind: ApprovalKind = ApprovalKind.CRAWL,
           now: datetime | None = None, **run: object) -> RunApproval:
    args: dict[str, object] = dict(actions=10, probes=1, wall_clock_s=60.0)
    args.update(run)
    return require_approval([row], project="demo", kind=kind, target=URL, now=now, **args)


def test_standing_crawl_passes_with_no_expiry_however_late() -> None:
    row = _row(standing=True)
    assert row.expires_at is None
    assert _check(row).id == row.id
    assert _check(row, now=FAR_FUTURE).id == row.id


def test_standing_adversarial_is_refused() -> None:
    row = _row(standing=True, kind=ApprovalKind.ADVERSARIAL)
    with pytest.raises(ApprovalRequired, match=r"adversarial|expir|standing"):
        _check(row, kind=ApprovalKind.ADVERSARIAL)


@pytest.mark.parametrize("kind", [ApprovalKind.LIVE_CASE, ApprovalKind.READ,
                                  ApprovalKind.VIDEO_REVIEW])
def test_standing_is_for_crawl_only(kind: ApprovalKind) -> None:
    with pytest.raises(ApprovalRequired):
        _check(_row(standing=True, kind=kind), kind=kind)


def test_a_row_with_no_expiry_and_no_standing_is_expired_never_eternal() -> None:
    row = _row(standing=False, expires_at=None)
    assert row.is_expired(datetime.now(UTC))
    with pytest.raises(ApprovalRequired):
        _check(row)


def test_flipping_standing_on_a_signed_dated_row_breaks_it() -> None:
    dated = _row(standing=False)
    assert _check(dated).id == dated.id
    flipped = dated.model_copy(update={"standing": True})
    assert not flipped.is_intact
    with pytest.raises(ApprovalRequired, match=r"edited|signature"):
        _check(flipped)
    # even with the id repaired, the signature over the old payload refuses it
    repaired = flipped.model_copy(update={"expires_at": None})
    repaired = repaired.model_copy(update={"id": repaired.computed_id})
    assert repaired.is_intact and not repaired.is_signed_and_verified
    with pytest.raises(ApprovalRequired, match="signature"):
        _check(repaired)


def test_dropping_standing_or_adding_an_expiry_to_a_standing_row_breaks_it() -> None:
    standing = _row(standing=True)
    for update in ({"standing": False}, {"expires_at": "2099-01-01T00:00:00+00:00"}):
        with pytest.raises(ApprovalRequired):
            _check(standing.model_copy(update=update))


def test_dated_row_payload_is_unchanged_so_existing_signatures_still_verify() -> None:
    dated = _row(standing=False)
    assert "standing" not in dated._bound_payload()
    assert _row(standing=True)._bound_payload()["standing"] is True


def test_row_written_before_standing_existed_loads_as_dated() -> None:
    legacy = RunApproval.model_validate_json(
        '{"project":"demo","run_kind":"crawl","target":"https://demo.test/","scope":"s",'
        '"granted_by":"u","granted_at":"2026-10-01","expires_at":"2026-10-21"}')
    assert legacy.standing is False and legacy.is_expired(datetime(2026, 10, 28, tzinfo=UTC))


def test_standing_still_capped_per_run_and_by_the_production_flag() -> None:
    row = _row(standing=True)
    with pytest.raises(ApprovalRequired, match="actions 51 > approved 50"):
        _check(row, actions=51)
    with pytest.raises(ApprovalRequired, match="wall clock"):
        _check(row, wall_clock_s=601.0)
    with pytest.raises(ApprovalRequired, match="production"):
        require_approval([row], project="demo", kind=ApprovalKind.CRAWL, target=URL,
                         production=True)
    assert _check(_row(standing=True, production=True), production=True)


def test_standing_must_still_name_the_exact_target() -> None:
    with pytest.raises(ApprovalRequired):
        require_approval([_row(standing=True)], project="demo", kind=ApprovalKind.CRAWL,
                         target="https://other.test/")


def test_unsigned_standing_is_refused() -> None:
    row = _row(standing=True)
    with pytest.raises(ApprovalRequired, match="signature"):
        _check(row.model_copy(update={"signature": ""}))


def test_signed_revocation_ends_a_standing_grant() -> None:
    row = _row(standing=True)
    rev = ApprovalRevocation(approval_id=row.id, revoked_by="umesh", reason="done",
                             revoked_at="2026-10-29T00:00:00+00:00").sign()
    with pytest.raises(ApprovalRequired, match="revoked"):
        require_approval([row], project="demo", kind=ApprovalKind.CRAWL, target=URL,
                         revocations=[rev])


def test_grant_bounds_standing_skips_only_the_expiry_ceiling() -> None:
    validate_grant_bounds(100, 600.0, None, kind=ApprovalKind.CRAWL)
    with pytest.raises(ValueError, match="2000"):
        validate_grant_bounds(2001, 600.0, None, kind=ApprovalKind.CRAWL)
    with pytest.raises(ValueError, match="24h"):
        validate_grant_bounds(100, 86401.0, None, kind=ApprovalKind.CRAWL)


def test_grant_bounds_standing_refused_for_other_kinds_and_when_kind_unstated() -> None:
    for kind in (ApprovalKind.ADVERSARIAL, ApprovalKind.LIVE_CASE, None):
        with pytest.raises(ValueError, match="standing"):
            validate_grant_bounds(100, 600.0, None, kind=kind)


def test_grant_bounds_dated_still_capped_at_30_days() -> None:
    far = datetime.now(UTC) + timedelta(days=31)
    with pytest.raises(ValueError, match="30 days"):
        validate_grant_bounds(100, 600.0, far)
    with pytest.raises(ValueError, match="30 days"):
        validate_grant_bounds(100, 600.0, far, kind=ApprovalKind.CRAWL)
    validate_grant_bounds(100, 600.0, datetime.now(UTC) + timedelta(days=29))
