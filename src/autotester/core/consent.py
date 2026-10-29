"""The consent gate (D-018): nothing outward-facing starts without a human's
`RunApproval` on disk that is intact, unexpired, and at least as wide as the run.

Gate 1 (`READ`) covers reading outside the project; gate 2 every outward-facing run.

The gate **fails closed and says exactly what is missing**: a refusal that only
says "no" teaches the operator nothing, and the next thing they do is guess.
"""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

from autotester.browser.secrets import SecretStore, _host_matches, host_of
from autotester.core.ids import SigningKeyMissing
from autotester.schema.approval import (
    MAX_GRANT_ACTIONS,
    MAX_GRANT_DAYS,
    MAX_GRANT_WALL_CLOCK_S,
    PROBES_PER_ACTION,
    STANDING_KINDS,
    RunApproval,
    _shown,
    derive_grant_bounds,
    grant_clamp_warning,
    invalid_bounds_message,
)
from autotester.schema.approval_revocation import ApprovalRevocation, revoked_ids
from autotester.schema.enums import ApprovalKind
from autotester.schema.project import Project


class ApprovalRequired(RuntimeError):
    """Raised instead of doing the thing. Carries the grant command verbatim."""


ACCOUNT_KINDS = frozenset({ApprovalKind.LIVE_CASE, ApprovalKind.CRAWL, ApprovalKind.READ})
"""D-068: the run kinds provisioned credentials authorise. ADVERSARIAL is deliberately absent."""
ACCOUNT_GRANTOR = "account-derived:D-068"


def is_account_derived(approval: RunApproval) -> bool:
    return approval.granted_by.startswith("account-derived:")


def validate_grant_bounds(
    actions: int, wall_clock_s: float, expires_at: datetime | None,
    now: datetime | None = None, *, kind: ApprovalKind | None = None,
) -> None:
    """The ONE cap on a NEW human grant, shared by the UI route and the CLI `approve`:
    at most 2000 actions, 24h wall clock, 30 days to expiry. Raises ValueError naming the
    limit. Grant time only; rows already on disk are never re-judged.

    D-111: `expires_at=None` is a STANDING grant. It skips only the 30-day ceiling (the
    per-run caps still apply) and only for a `kind` in `STANDING_KINDS`; an unstated or
    other kind is refused, so adversarial always needs a date."""
    if expires_at is None and kind not in STANDING_KINDS:
        raise ValueError("only a crawl approval may be standing; this kind needs an expiry")
    if actions > MAX_GRANT_ACTIONS:
        raise ValueError(f"max actions {actions} exceeds the limit of {MAX_GRANT_ACTIONS}")
    if wall_clock_s > MAX_GRANT_WALL_CLOCK_S:
        raise ValueError(f"wall clock {wall_clock_s:g}s exceeds the limit of "
                         f"{MAX_GRANT_WALL_CLOCK_S:g}s (24h)")
    if expires_at is not None and expires_at > (now or datetime.now(UTC)) + timedelta(
            days=MAX_GRANT_DAYS):
        raise ValueError(f"expiry is more than {MAX_GRANT_DAYS} days away")


def account_probe_budget(actions: int) -> int:
    """The system-selected probe brake for an account-derived grant (CN11: positive, finite)."""
    return max(1, actions * PROBES_PER_ACTION)


def validate_account_scope(
    project: Project, secrets: SecretStore, *, account_keys: set[str],
) -> str:
    """Validate selected declared account metadata without retrieving raw values."""
    host = host_of(project.base_url)
    if (not host or urlparse(project.base_url).scheme not in {"http", "https"}
            or not project.allows_domain(host) or secrets._project != project):
        raise ApprovalRequired("account authorization target or project is invalid")
    if not account_keys:
        raise ApprovalRequired("account authorization needs selected account keys")
    domains = {}
    for key in sorted(account_keys):
        ref = project.secret(key)
        if (ref is None or not secrets.has_value(key)
                or secrets._refs.get(key) != ref
                or not any(_host_matches(host, d, ref.include_subdomains) for d in ref.domains)):
            raise ApprovalRequired(f"referenced account key {key} is unavailable or out of scope")
        domains[key] = {"domains": ref.domains, "include_subdomains": ref.include_subdomains}
    return json.dumps({"keys": sorted(account_keys), "domains": domains},
                      sort_keys=True, separators=(",", ":"))


def validate_account_bounds(
    actions: int, probes: int, wall_clock_s: float, *, now: datetime | None = None,
) -> datetime:
    """Return an aware expiry or refuse nonpositive, nonfinite or overflowing brakes."""
    try:
        finite_wall = type(wall_clock_s) in {int, float} and math.isfinite(wall_clock_s)
    except OverflowError:
        finite_wall = False
    if (type(actions) is not int or type(probes) is not int or actions <= 0 or probes <= 0
            or not finite_wall or wall_clock_s <= 0):
        raise ApprovalRequired("account authorization bounds must be positive and finite")
    moment = now or datetime.now(UTC)
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ApprovalRequired("account authorization clock must be offset-aware")
    try:
        expiry = moment + timedelta(seconds=wall_clock_s)
        if expiry <= moment:
            raise ValueError("expiry did not advance")
        return expiry
    except (ValueError, OverflowError):
        raise ApprovalRequired("account authorization expiry is outside supported range") from None


def prepare_account_grant(
    project: Project, secrets: SecretStore, *, kind: ApprovalKind, account_keys: set[str],
    actions: int, probes: int, wall_clock_s: float, now: datetime | None = None,
) -> RunApproval:
    """Mint and verify one NEW exact account-derived row (D-068), never loaded rows.

    Covers any run of the same (project, kind, target); the scope is the validated
    account/domain scope, not a case-set key. ADVERSARIAL never gets an automatic grant."""
    if kind not in ACCOUNT_KINDS:
        raise ApprovalRequired(f"no automatic account grant exists for {kind.value} runs")
    scope = validate_account_scope(project, secrets, account_keys=account_keys)
    moment = now or datetime.now(UTC)
    expiry = validate_account_bounds(actions, probes, wall_clock_s, now=moment)
    candidate = RunApproval(project=project.slug, run_kind=kind,
        target=project.base_url, scope=scope, max_actions=actions, max_probes=probes,
        wall_clock_s=wall_clock_s, production=False, granted_by=ACCOUNT_GRANTOR,
        granted_at=moment.isoformat(), expires_at=expiry.isoformat()).sign()
    return require_approval([candidate], project=project.slug, kind=kind,
                            target=project.base_url, actions=actions, probes=probes,
                            wall_clock_s=wall_clock_s, now=moment)


def _grant_advice(
    project: str, kind: ApprovalKind, target: str,
    actions: int, probes: int, wall_clock_s: float, production: bool,
) -> str:
    """The tail of a refusal. A malformed bound is NAMED with its reason and no `approve` command
    follows (`approve` would reject it); else the command that lets THIS run proceed."""
    if note := invalid_bounds_message(actions, probes, wall_clock_s):
        return note
    bounds = derive_grant_bounds(kind, actions, probes, wall_clock_s)
    parts = [
        f"uv run autotester approve {project} --kind {kind.value}",
        f'--target "{target}"',
        '--scope "<what this run may touch>"',
        "--granted-by <name> --expires <YYYY-MM-DD>",
    ]
    parts += [f"{flag} {value}" for flag, value in zip(
        ("--max-actions", "--max-probes", "--wall-clock"), bounds, strict=True) if value]
    if production:
        parts.append("--production")
    keep = ("\nTo keep it valid until revoked, replace --expires <YYYY-MM-DD> with --standing."
            if kind in STANDING_KINDS else "")
    return (grant_clamp_warning(kind, actions, probes, wall_clock_s)
            + "\nGrant one with:\n  " + " ".join(parts) + keep)


def _shortfalls(
    approval: RunApproval, actions: int, probes: int, wall_clock_s: float
) -> list[str]:
    short = []
    if actions > approval.max_actions:
        short.append(f"actions {_shown(actions)} > approved {approval.max_actions}")
    if probes > approval.max_probes:
        short.append(f"probes {_shown(probes)} > approved {approval.max_probes}")
    if wall_clock_s > approval.wall_clock_s:
        short.append(f"wall clock {_shown(wall_clock_s)}s > approved {approval.wall_clock_s}s")
    return short


def _reject_reason(
    approval: RunApproval, now: datetime, actions: int, probes: int, wall_clock_s: float,
    production: bool,
) -> str | None:
    """Why this candidate approval does not cover the run, or None if it does."""
    if not approval.is_intact:
        return f"{approval.id}: edited after it was granted (content id no longer matches)"
    try:
        signed_and_verified = approval.is_signed_and_verified
    except SigningKeyMissing as exc:
        # Fail closed: no key configured means NOTHING can be verified, so
        # every approval is refused, never silently honoured (AT-110).
        return f"{approval.id}: cannot verify — {exc}"
    if not signed_and_verified:
        if not approval.signature:
            return (
                f"{approval.id}: no signature — granted before signing was required, "
                "or the row was forged; re-grant it with `uv run autotester approve`"
            )
        return f"{approval.id}: signature does not verify — the row was edited or forged"
    if approval.is_expired(now):
        if approval.expires_at is None:  # D-111: standing is for crawl only
            return (f"{approval.id}: has no expiry and is not a standing crawl approval -- "
                    "only a crawl approval may be standing (adversarial needs an expiry)")
        return f"{approval.id}: expired {approval.expires_at}"
    if production and not approval.production:
        return f"{approval.id}: target is production and the approval does not say production"
    short = _shortfalls(approval, actions, probes, wall_clock_s)
    if short:
        return f"{approval.id}: narrower than this run — " + "; ".join(short)
    return None


def _width(approval: RunApproval) -> tuple[bool, float, int, int]:
    """Sort key for the widest of several covering approvals: human-granted first."""
    return (not is_account_derived(approval), approval.wall_clock_s,
            approval.max_probes, approval.max_actions)


def require_approval(
    approvals: list[RunApproval],
    *,
    project: str,
    kind: ApprovalKind,
    target: str,
    actions: int = 0,
    probes: int = 0,
    wall_clock_s: float = 0.0,
    production: bool = False,
    now: datetime | None = None,
    revocations: list[ApprovalRevocation] | None = None,
) -> RunApproval:
    """Return the approval covering this run, or raise `ApprovalRequired`.

    A row with a valid SIGNED `ApprovalRevocation` is dropped; an unsigned or forged
    revocation is ignored (it cannot revoke). `ProjectStore.list_approvals` applies the same
    filter, so callers that pass its output are covered without passing `revocations`.

    Target matching is EXACT. A prefix match would let an approval for one
    endpoint authorise another under the same host, which is the whole thing
    this gate exists to prevent.
    """
    now = now or datetime.now(UTC)
    revoked = revoked_ids(revocations or [])
    same = [a for a in approvals
            if a.project == project and a.run_kind is kind and a.target == target]
    candidates = [a for a in same if a.id not in revoked]
    rejections = [f"{a.id}: revoked" for a in same if a.id in revoked]
    covering = []
    for approval in candidates:
        reason = _reject_reason(approval, now, actions, probes, wall_clock_s, production)
        if reason is None:
            covering.append(approval)
        else:
            rejections.append(reason)
    if covering:  # several cover the run: a human row first, then the widest (ties keep order)
        return max(covering, key=_width)

    detail = (
        "no approval exists for it" if not rejections
        else "the approvals that exist do not cover it:\n  - " + "\n  - ".join(rejections)
    )
    raise ApprovalRequired(
        f"refusing to start a {kind.value} run against {target} — {detail}"
        f"{_grant_advice(project, kind, target, actions, probes, wall_clock_s, production)}"
    )


def require_project_approval(
    approvals: list[RunApproval], *, project: Project, kind: ApprovalKind, target: str,
    actions: int = 0, probes: int = 0, wall_clock_s: float = 0.0,
    now: datetime | None = None, production: bool = False,
    revocations: list[ApprovalRevocation] | None = None,
) -> RunApproval:
    """The ONE rule for acting on a project's live target (D-088). A project declared
    `production` is covered only by a signed, human-granted `production: true` row for this
    exact target and run kind: an account-derived (D-068) or `production: false` row is never
    accepted and the refusal names why. Any other project is checked as before (`production`
    stays the caller's own stated flag, e.g. an adversarial run's `--production`)."""
    if not project.production:
        return require_approval(
            approvals, project=project.slug, kind=kind, target=target, actions=actions,
            probes=probes, wall_clock_s=wall_clock_s, production=production, now=now,
            revocations=revocations)
    human = [row for row in approvals if not is_account_derived(row)]
    try:
        return require_approval(
            human, project=project.slug, kind=kind, target=target, actions=actions,
            probes=probes, wall_clock_s=wall_clock_s, production=True, now=now,
            revocations=revocations)
    except ApprovalRequired as why:
        skipped = [row.id for row in approvals if row.project == project.slug
                   and row.run_kind is kind and row.target == target
                   and (is_account_derived(row) or not row.production)]
        note = (f"\n(production gate, D-088: {project.slug} is declared production; "
                f"account-derived or production:false rows are refused: {', '.join(skipped)})"
                if skipped else "\n(production gate, D-088: only a human-granted "
                "production:true row for this target and run kind is accepted)")
        raise ApprovalRequired(f"{why}{note}") from None
