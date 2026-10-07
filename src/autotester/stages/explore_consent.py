"""The crawl's consent pre-flight (D-018 gate 2) — split from `explore.py`
for the 300-line cap (AT-507/AT-460: the stage was at its line budget).

One job: answer "may this crawl start" BEFORE a browser opens, and raise
`ApprovalRequired` naming exactly what is missing. `run_crawl` and both
production pre-flights (CLI, UI) call `require_consent`; nothing else decides
consent. X10-b condition 3 (AT-535) lives here too: a synthetic-typing run
against an approval that says `production: true` is refused before the
browser opens — D-029's four conditions are enforced where the run begins,
not discovered mid-crawl.
"""

from __future__ import annotations

from autotester.browser.secrets import SecretStore
from autotester.core.consent import (
    ACCOUNT_KINDS,
    ApprovalRequired,
    account_probe_budget,
    is_account_derived,
    prepare_account_grant,
    require_approval,
    validate_account_bounds,
    validate_account_scope,
)
from autotester.core.ids import SigningKeyMissing, ensure_approval_key
from autotester.core.redact import placeholder_keys
from autotester.schema.approval import RunApproval
from autotester.schema.crawl import CrawlBounds, SafetyPolicy
from autotester.schema.enums import ApprovalKind
from autotester.schema.project import Project
from autotester.store.project_store import ProjectStore


def covering_approval(project: Project, store: ProjectStore, bounds: CrawlBounds,
                      *, kind: ApprovalKind = ApprovalKind.CRAWL,
                      secrets: SecretStore | None = None,
                      account_keys: set[str] | None = None) -> RunApproval:
    """The RunApproval covering this run, or `ApprovalRequired`.

    `kind` defaults to `CRAWL` so every existing caller is unchanged, and the
    UI case-run preflight passes `LIVE_CASE` (AT-570). One gate, one place: a
    second `covering_approval` for cases would be C3's one-concept-two-places,
    and the enum member it checks has existed unused since D-018.

    D-068: when no human-granted row covers the run and the project declares
    credentials, provisioned credentials ARE the approval -- a signed row is minted
    (or an earlier account-derived row reused) with no human step. `account_keys`
    narrows the credentials checked to those the run references."""
    rows = store.list_approvals()
    if kind not in ACCOUNT_KINDS or not project.secrets:
        return _require(rows, project, kind, bounds)
    try:
        return _credential_approval(project, store, bounds, kind, rows, secrets, account_keys)
    except ApprovalRequired as why:
        try:  # credentials unavailable: a human-granted row can still cover it, as before D-068
            return _require(rows, project, kind, bounds)
        except ApprovalRequired as human_refusal:
            raise ApprovalRequired(
                f"{human_refusal}\n(credential-derived approval unavailable: {why})") from None


def _require(rows: list[RunApproval], project: Project, kind: ApprovalKind,
             bounds: CrawlBounds, probes: int = 0) -> RunApproval:
    return require_approval(
        rows, project=project.slug, kind=kind, target=project.base_url,
        actions=bounds.max_actions, probes=probes, wall_clock_s=bounds.wall_clock_s)


def _credential_approval(
    project: Project, store: ProjectStore, bounds: CrawlBounds, kind: ApprovalKind,
    rows: list[RunApproval], secrets: SecretStore | None, account_keys: set[str] | None,
) -> RunApproval:
    """D-068/CN11: validate first (a refusal writes nothing), reuse any row that covers the
    run (human-granted first, and with the probes this run needs: a probe-less row would stop
    it at the first fill), else mint one new signed row. Never signs, re-signs or repairs a
    loaded row."""
    secrets = secrets or SecretStore.load(project, store.paths.env_file, strict=False)
    keys = account_keys or _default_account_keys(project, store, secrets)
    probes = account_probe_budget(bounds.max_actions)
    validate_account_scope(project, secrets, account_keys=keys)
    validate_account_bounds(bounds.max_actions, probes, bounds.wall_clock_s)
    try:
        return _require(sorted(rows, key=is_account_derived), project, kind, bounds, probes)
    except ApprovalRequired:
        pass
    try:
        ensure_approval_key(store.paths.env_file, lambda: _approval_history(store))
        approval = prepare_account_grant(
            project, secrets, kind=kind, account_keys=keys, actions=bounds.max_actions,
            probes=probes, wall_clock_s=bounds.wall_clock_s)
        return store.add_approval(approval)
    except (SigningKeyMissing, ValueError, OSError, TimeoutError) as exc:
        # Never echo malformed history rows, file contents or env values.
        raise ApprovalRequired(f"the approval key is unavailable ({type(exc).__name__})") from None


def _default_account_keys(project: Project, store: ProjectStore, secrets: SecretStore) -> set[str]:
    """The login case's referenced keys, else every provisioned declared key."""
    case = store.get_case(project.login_case_id) if project.login_case_id else None
    referenced = {key for step in (case.steps if case else [])
                  for text in (step.target, step.value or "") for key in placeholder_keys(text)}
    return referenced or {ref.key for ref in project.secrets if secrets.has_value(ref.key)}


def _approval_history(store: ProjectStore) -> list[RunApproval]:
    """Repository-wide typed history, read only inside key creation's lock."""
    return [row for directory in store.paths.dir.parent.iterdir() if directory.is_dir()
            for row in ProjectStore(directory.name, store.paths.root).list_approvals()]


def require_consent(project: Project, store: ProjectStore, bounds: CrawlBounds,
                    policy: SafetyPolicy | None = None) -> None:
    """D-018 gate 2, plus X10-b condition 3 (AT-535): a synthetic-typing crawl
    must be covered by an approval whose target is NOT production — typing on
    a production system is the one thing D-029's four conditions exist to
    prevent. Raises `ApprovalRequired` naming the approval's id.

    `policy` is optional so every existing caller stays valid; `run_crawl`
    always passes the run's policy, so the runtime seam holds even when a
    pre-flight caller forgets to."""
    approval = covering_approval(project, store, bounds)
    if policy is not None and policy.synthetic_typing and approval.production:
        raise ApprovalRequired(
            f"{approval.id}: synthetic typing (X10-b) is refused against a "
            "production target — grant a dev-environment approval "
            "(production: false) instead"
        )