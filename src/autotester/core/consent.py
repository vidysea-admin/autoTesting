"""The consent gate (D-018): nothing outward-facing starts without a human's
`RunApproval` on disk that is intact, unexpired, and at least as wide as the run.

Gate 1 (`ApprovalKind.READ`) covers reading outside the project. Gate 2 covers
every outward-facing run — the live crawl and, above all, the adversarial pass.

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
from autotester.schema.approval import RunApproval
from autotester.schema.enums import ApprovalKind
from autotester.schema.project import Project


class ApprovalRequired(RuntimeError):
    """Raised instead of doing the thing. Carries the grant command verbatim."""


ACCOUNT_KINDS = frozenset({ApprovalKind.LIVE_CASE, ApprovalKind.CRAWL, ApprovalKind.READ})
"""D-068: the run kinds provisioned credentials authorise. ADVERSARIAL is deliberately absent."""
ACCOUNT_GRANTOR = "account-derived:D-068"
PROBES_PER_ACTION = 20


def is_account_derived(approval: RunApproval) -> bool:
    return approval.granted_by.startswith("account-derived:")


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


def _grant_command(
    project: str, kind: ApprovalKind, target: str,
    actions: int, probes: int, wall_clock_s: float, production: bool,
) -> str:
    """The command that would actually let THIS run proceed.

    Found by running it: the first version omitted the bounds, so an operator who
    followed the printed command verbatim got a second refusal — `--max-actions`
    defaults to 0, and every real crawl exceeds 0. A suggestion that does not
    work is worse than no suggestion, because it spends the reader's trust.
    """
    parts = [
        f"uv run autotester approve {project} --kind {kind.value}",
        f'--target "{target}"',
        '--scope "<what this run may touch>"',
        "--granted-by <name> --expires <YYYY-MM-DD>",
    ]
    if actions:
        parts.append(f"--max-actions {actions}")
    if probes:
        parts.append(f"--max-probes {probes}")
    if wall_clock_s:
        parts.append(f"--wall-clock {wall_clock_s}")
    if production:
        parts.append("--production")
    return " ".join(parts)


def _shortfalls(
    approval: RunApproval, actions: int, probes: int, wall_clock_s: float
) -> list[str]:
    short = []
    if actions > approval.max_actions:
        short.append(f"actions {actions} > approved {approval.max_actions}")
    if probes > approval.max_probes:
        short.append(f"probes {probes} > approved {approval.max_probes}")
    if wall_clock_s > approval.wall_clock_s:
        short.append(f"wall clock {wall_clock_s}s > approved {approval.wall_clock_s}s")
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
        return f"{approval.id}: expired {approval.expires_at}"
    if production and not approval.production:
        return f"{approval.id}: target is production and the approval does not say production"
    short = _shortfalls(approval, actions, probes, wall_clock_s)
    if short:
        return f"{approval.id}: narrower than this run — " + "; ".join(short)
    return None


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
) -> RunApproval:
    """Return the approval covering this run, or raise `ApprovalRequired`.

    Target matching is EXACT. A prefix match would let an approval for one
    endpoint authorise another under the same host, which is the whole thing
    this gate exists to prevent.
    """
    now = now or datetime.now(UTC)
    candidates = [
        a for a in approvals
        if a.project == project and a.run_kind is kind and a.target == target
    ]
    rejections = []
    for approval in candidates:
        reason = _reject_reason(approval, now, actions, probes, wall_clock_s, production)
        if reason is None:
            return approval
        rejections.append(reason)

    detail = (
        "no approval exists for it" if not rejections
        else "the approvals that exist do not cover it:\n  - " + "\n  - ".join(rejections)
    )
    raise ApprovalRequired(
        f"refusing to start a {kind.value} run against {target} — {detail}\n"
        "Grant one with:\n  "
        f"{_grant_command(project, kind, target, actions, probes, wall_clock_s, production)}"
    )
