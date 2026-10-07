"""The consent gate (D-018, T-124). Contract: qa/contracts/adversarial.md (to be
authored) + explore.md.

Consent used to be a habit — `write_policy` defaults and HUMAN_GATE files that a
careful operator honoured. These tests are about the cases where care is not
enough: an approval edited on disk, one that expired, one for a different
endpoint, and one that is simply absent while the run starts anyway.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from autotester.browser.secrets import SecretStore
from autotester.core.consent import ApprovalRequired, prepare_account_grant, require_approval
from autotester.schema.approval import RunApproval
from autotester.schema.enums import ApprovalKind
from autotester.schema.project import Project, SecretRef
from autotester.store.project_store import ProjectStore

NOW = datetime(2026, 9, 8, 12, 0, 0)
TARGET = "https://www.vidysea.com/erp"


def approval(**overrides: object) -> RunApproval:
    fields: dict[str, object] = {
        "project": "erp", "run_kind": ApprovalKind.CRAWL, "target": TARGET,
        "scope": "read-only crawl of the trainer module", "max_actions": 150,
        "wall_clock_s": 900.0, "granted_by": "umesh", "granted_at": "2026-09-08",
        "expires_at": "2026-09-09",
    }
    fields.update(overrides)
    return RunApproval(**fields).sign()  # type: ignore[arg-type]


def require(approvals: list[RunApproval], **kw: object) -> RunApproval:
    args: dict[str, object] = {
        "project": "erp", "kind": ApprovalKind.CRAWL, "target": TARGET,
        "actions": 150, "wall_clock_s": 900.0, "now": NOW,
    }
    args.update(kw)
    return require_approval(approvals, **args)  # type: ignore[arg-type]


# -- the happy path, and what a refusal must teach ---------------------------

def test_a_covering_approval_is_returned() -> None:
    granted = approval()
    assert require([granted]).id == granted.id


def test_no_approval_at_all_names_the_command_that_grants_one() -> None:
    """A refusal that only says no teaches the operator nothing, and the next
    thing they do is guess."""
    with pytest.raises(ApprovalRequired) as exc:
        require([])
    message = str(exc.value)
    assert "no approval exists for it" in message
    assert "autotester approve erp --kind crawl" in message
    assert TARGET in message


# -- the cases where being careful is not enough ------------------------------

def test_an_approval_edited_to_widen_itself_is_refused() -> None:
    """The reason the id is content-addressed. Hand-editing approvals.jsonl to
    raise max_actions must not silently take effect."""
    granted = approval(max_actions=10)
    widened = granted.model_copy(update={"max_actions": 100_000})

    assert widened.is_intact is False
    with pytest.raises(ApprovalRequired, match="edited after it was granted"):
        require([widened], actions=50)


def test_annotating_an_approval_does_not_invalidate_it() -> None:
    """`note` is deliberately outside the bound payload — a human may write on
    an approval without having to re-grant it."""
    annotated = approval().model_copy(update={"note": "watched this one live"})
    assert annotated.is_intact is True
    assert require([annotated]).id == annotated.id


def test_an_expired_approval_is_refused_and_says_when() -> None:
    with pytest.raises(ApprovalRequired, match="expired 2026-09-01"):
        require([approval(expires_at="2026-09-01")])


def test_an_unparseable_expiry_is_treated_as_expired_never_as_eternal() -> None:
    with pytest.raises(ApprovalRequired):
        require([approval(expires_at="whenever")])


@pytest.mark.parametrize(("expiry", "now", "expired"), [
    ("2026-09-10T12:00:00+10:00", datetime(2026, 9, 10, 1, 59), False),
    ("2026-09-10T12:00:00+10:00", datetime(2026, 9, 10, 2, 1), True),
    ("2026-09-10T12:00:00-10:00", datetime(2026, 9, 10, 21, 59), False),
    ("2026-09-10T12:00:00-10:00", datetime(2026, 9, 10, 22, 1), True),
])
def test_offset_expiry_is_compared_as_a_utc_instant(
    expiry: str, now: datetime, expired: bool,
) -> None:
    assert approval(expires_at=expiry).is_expired(now) is expired


def test_a_pre_existing_bare_date_row_still_lapses_at_the_start_of_its_day() -> None:
    """CN4 (at147 answered C, D-048): only a NEW grant gets end-of-day treatment
    (see `tests/test_approve_cli.py`). A bare `expires_at` already on disk keeps
    reading through `fromisoformat` as MIDNIGHT -- option B, retroactively
    widening every approval already granted, was declined."""
    row = approval(expires_at="2026-09-26")
    assert row.is_expired(datetime(2026, 9, 26, 0, 0, 0)) is False
    assert row.is_expired(datetime(2026, 9, 26, 0, 0, 1)) is True


def test_runtime_default_clock_is_utc_aware(monkeypatch: pytest.MonkeyPatch) -> None:
    class HostClock(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return cls(2026, 9, 10, 8, 25)
            return cls(2026, 9, 10, 2, 55, tzinfo=tz)

    monkeypatch.setattr("autotester.core.consent.datetime", HostClock)
    granted = approval(expires_at="2026-09-10T03:55:00+00:00")
    assert require_approval(
        [granted], project="erp", kind=ApprovalKind.CRAWL, target=TARGET,
    ).id == granted.id


def test_an_approval_narrower_than_the_run_is_refused_with_the_shortfall() -> None:
    with pytest.raises(ApprovalRequired, match="actions 150 > approved 20"):
        require([approval(max_actions=20)])


def test_a_longer_run_than_approved_is_refused_on_wall_clock() -> None:
    with pytest.raises(ApprovalRequired, match="wall clock"):
        require([approval(wall_clock_s=60.0)])


def test_target_matching_is_exact_not_a_prefix() -> None:
    """A prefix match would let an approval for one endpoint authorise another
    under the same host — the whole thing this gate exists to prevent."""
    with pytest.raises(ApprovalRequired):
        require([approval(target="https://www.vidysea.com")], target=TARGET + "/admin")


def test_an_approval_for_another_kind_of_run_does_not_transfer() -> None:
    """Consent to read is not consent to fire adversarial probes."""
    with pytest.raises(ApprovalRequired):
        require([approval(run_kind=ApprovalKind.READ)])


def test_an_approval_for_another_project_does_not_transfer() -> None:
    with pytest.raises(ApprovalRequired):
        require([approval(project="pathlynks")])


def test_adversarial_against_production_needs_production_said_explicitly() -> None:
    granted = approval(run_kind=ApprovalKind.ADVERSARIAL, max_probes=50)
    with pytest.raises(ApprovalRequired, match="does not say production"):
        require([granted], kind=ApprovalKind.ADVERSARIAL, probes=10, production=True)

    said = approval(run_kind=ApprovalKind.ADVERSARIAL, max_probes=50, production=True)
    assert require([said], kind=ApprovalKind.ADVERSARIAL, probes=10, production=True).id == said.id


def test_one_bad_approval_does_not_hide_a_good_one() -> None:
    """An expired row sitting beside a valid one must not cause a refusal."""
    assert require([approval(expires_at="2026-01-01"), approval()]).id == approval().id


def test_every_rejection_reason_is_reported_not_just_the_first() -> None:
    with pytest.raises(ApprovalRequired) as exc:
        require([approval(expires_at="2026-01-01"), approval(max_actions=5)])
    message = str(exc.value)
    assert "expired" in message
    assert "narrower than this run" in message


# -- it survives a round trip through the store ------------------------------

def test_an_approval_round_trips_through_the_store_intact(tmp_path: Path) -> None:
    store = ProjectStore("erp", tmp_path)
    store.add_approval(approval())

    loaded = store.list_approvals()

    assert len(loaded) == 1
    assert loaded[0].is_intact is True
    assert require(loaded).id == approval().id


def test_the_suggested_grant_command_would_actually_cover_this_run() -> None:
    """Found by running it: the first version of the message omitted the bounds,
    so an operator who pasted the printed command got a SECOND refusal —
    `--max-actions` defaults to 0 and every real crawl exceeds 0. A suggestion
    that does not work is worse than none, because it spends the reader's trust
    on the way to the same dead end."""
    with pytest.raises(ApprovalRequired) as exc:
        require([], actions=150, wall_clock_s=900.0)
    command = str(exc.value)

    assert "--max-actions 150" in command
    assert "--wall-clock 900.0" in command


def test_the_grant_command_says_production_when_the_run_needs_it() -> None:
    with pytest.raises(ApprovalRequired) as exc:
        require([], kind=ApprovalKind.ADVERSARIAL, probes=25, production=True)
    command = str(exc.value)

    assert "--production" in command
    assert "--max-probes 25" in command


@pytest.mark.parametrize("mode", ["valid", "unused", "missing", "undeclared", "scope", "target",
                                  "actions", "probes", "wall", "infinite", "overflow", "other",
                                  "bigint"])
def test_account_grant_is_new_exact_and_bounded(mode) -> None:
    project = Project(slug="demo", name="Demo", base_url="https://demo.test/app",
        allowed_domains=["demo.test"], secrets=[
            SecretRef(key="USER", domains=["demo.test"], include_subdomains=False),
            SecretRef(key="UNUSED", domains=["other.test"])])
    values = {"USER": "synthetic-account-value"}
    keys = {"USER"}
    bounds = dict(actions=10, probes=20, wall_clock_s=30.0)
    values = {} if mode == "missing" else values
    keys = {"UNKNOWN"} if mode == "undeclared" else keys
    if mode == "scope":
        project.secrets[0].domains = ["sibling.test"]
    if mode == "target":
        project.base_url = "https://evil.test"
    if mode in {"actions", "probes", "wall", "infinite", "overflow", "bigint"}:
        field = {"wall": "wall_clock_s", "infinite": "wall_clock_s",
                 "overflow": "wall_clock_s", "bigint": "wall_clock_s"}.get(mode, mode)
        bounds[field] = {"infinite": float("inf"), "overflow": 1e300,
                         "bigint": 10**1000}.get(mode, 0)
    secrets = SecretStore(project, values)
    if mode == "other":
        secrets = SecretStore(project.model_copy(update={"slug": "other"}), values)
    args = dict(kind=ApprovalKind.LIVE_CASE, account_keys=keys,
                now=NOW.replace(tzinfo=UTC), **bounds)
    historical = approval()
    before = historical.model_dump_json()
    if mode not in {"valid", "unused"}:
        with pytest.raises((ApprovalRequired, ValueError)):
            prepare_account_grant(project, secrets, **args)
        assert historical.model_dump_json() == before
        return
    row = prepare_account_grant(project, secrets, **args)
    assert row.project == project.slug and row.target == project.base_url
    assert row.run_kind is ApprovalKind.LIVE_CASE
    assert row.is_intact and row.is_signed_and_verified
    assert row.production is False
    assert not row.is_expired(args["now"])
    scope = json.loads(row.scope)
    assert scope["keys"] == ["USER"] and "cases" not in scope  # D-068: scope is not a case-set key
    assert "synthetic-account-value" not in row.model_dump_json()
    assert "UNUSED" not in row.scope
    assert historical.model_dump_json() == before
