"""CATALOG: derive, per `CaseClass`, whether it applies, whether it can run
right now, and — when it cannot — the one `BlockedReason` plus the action
that clears it.

Contract: qa/contracts/catalog.md CT1-CT8 (D-039). Pure: reads only artifacts
already on disk (the FlowSpec, declared `SecretRef`s, `.env` key presence,
`write_policy`) — no `Provider` call, no network call, no write of anything
it reads. Same inputs on disk -> byte-identical `Catalog`, every call (CT1).
"""

from __future__ import annotations

from autotester.browser.secrets import SecretStore
from autotester.core.paths import ProjectPaths
from autotester.core.redact import PLACEHOLDER_RE
from autotester.schema.catalog import (
    TIER_BY_CLASS,
    TIER_ORDER,
    BlockedReason,
    Catalog,
    CatalogEntry,
    Tier,
)
from autotester.schema.enums import Action, CaseClass, ReviewStatus, WritePolicy
from autotester.schema.flowspec import FlowSpec
from autotester.schema.project import Project
from autotester.store.project_store import ProjectStore

# CT5/plan.md 5A: only the classes that fill in a declared credential need one
# present. Matches `stages/expand.py::_has_auth_field`'s gate on the same pair.
_AUTH_CLASSES = frozenset({CaseClass.AUTH_WRONG_CREDS, CaseClass.AUTH_EXPIRED_SESSION})

# The one class whose whole purpose is a repeated MUTATING submit -- a
# READ_ONLY project cannot run it (D-039 `needs_write_policy`). Every other
# class either does not submit at all, or submits at most once, which is
# already how the system runs a READ_ONLY case today (no other class is
# blocked here: widening this set is a contract amendment, not a T-125 fix —
# see catalog.md's no-fire list).
_NEEDS_WRITE_CLASSES = frozenset({CaseClass.DOUBLE_SUBMIT})


def _auth_secret_keys(spec: FlowSpec) -> list[str]:
    """Every `{{SECRET:KEY}}` key referenced by a FILL step, across every
    flow, in first-seen order. Never returns a value (C5) — only key names."""
    keys: list[str] = []
    for flow in spec.flows:
        for step in flow.steps:
            if step.action is not Action.FILL or not step.value:
                continue
            for key in PLACEHOLDER_RE.findall(step.value):
                if key not in keys:
                    keys.append(key)
    return keys


def _missing_keys(project: Project, keys: list[str]) -> list[str]:
    """Declared keys among `keys` that have no value in the repo-root `.env`.
    Reads presence only (`SecretStore.has_value`) — the value itself never
    passes through this stage (C5)."""
    store = SecretStore.load(project, ProjectPaths(project.slug).env_file, strict=False)
    return [key for key in keys if not store.has_value(key)]


def _blocked(
    case_class: CaseClass, *, applicable: bool, reason: BlockedReason, action: str
) -> CatalogEntry:
    return CatalogEntry(
        case_class=case_class, tier=TIER_BY_CLASS[case_class], applicable=applicable,
        runnable=False, blocked_reason=reason, unblock_action=action,
    )


def _no_flowspec_catalog(project: Project) -> Catalog:
    action = (
        f"record a source (video, doc, or URL) for '{project.slug}' and run INGEST "
        "(or explore it) to produce a FlowSpec"
    )
    entries = [
        _blocked(cc, applicable=False, reason=BlockedReason.NO_FLOWSPEC, action=action)
        for cc in CaseClass
    ]
    return Catalog(project=project.slug, entries=entries)


def _not_approved_catalog(project: Project) -> Catalog:
    action = f"review and approve the FlowSpec at /projects/{project.slug}/flowspec"
    entries = [
        _blocked(cc, applicable=True, reason=BlockedReason.FLOWSPEC_NOT_APPROVED, action=action)
        for cc in CaseClass
    ]
    return Catalog(project=project.slug, entries=entries)


def _entry_for(
    case_class: CaseClass, project: Project, missing_auth_keys: list[str]
) -> CatalogEntry:
    tier = TIER_BY_CLASS[case_class]
    if case_class in _AUTH_CLASSES and missing_auth_keys:
        action = "set " + ", ".join(missing_auth_keys) + " in the repo-root .env"
        return CatalogEntry(
            case_class=case_class, tier=tier, applicable=True, runnable=False,
            blocked_reason=BlockedReason.MISSING_CREDENTIAL, unblock_action=action,
        )
    if case_class in _NEEDS_WRITE_CLASSES and project.write_policy is WritePolicy.READ_ONLY:
        action = (
            f"raise '{project.slug}'s write_policy from read_only to test_account "
            f"(or allow_writes) to run {case_class.value}"
        )
        return CatalogEntry(
            case_class=case_class, tier=tier, applicable=True, runnable=False,
            blocked_reason=BlockedReason.NEEDS_WRITE_POLICY, unblock_action=action,
        )
    return CatalogEntry(case_class=case_class, tier=tier, applicable=True, runnable=True)


def catalog(project: Project, spec: FlowSpec | None, store: ProjectStore | None = None) -> Catalog:
    """The project's whole catalog: every `CaseClass`, exactly once (CT2).

    `store` is accepted (per D-039's `catalog(project, spec, store)` shape)
    but unused today — every fact this stage needs already lives on `project`
    and `spec`; a store-backed fact (e.g. a persisted `RunApproval`) is a
    future widening, not something this signature should have to change for.
    """
    if spec is None or not spec.flows:
        return _no_flowspec_catalog(project)
    if spec.review.status is not ReviewStatus.APPROVED:
        return _not_approved_catalog(project)
    missing_auth_keys = _missing_keys(project, _auth_secret_keys(spec))
    entries = [_entry_for(cc, project, missing_auth_keys) for cc in CaseClass]
    return Catalog(project=project.slug, entries=entries)


def tiers_to_run(cat: Catalog) -> list[Tier]:
    """Cheap -> expensive ordering (CT6). Walk `TIER_ORDER` and STOP at the
    first tier with zero runnable entries — a cheap structural failure (e.g.
    every STATIC entry blocked) is visible before an expensive tier is paid
    for, even when that later tier itself has runnable entries.

    Pure and total over `Catalog.entries` — a caller that wants "did tier X
    actually get dispatched" iterates this list in order, which IS the call
    order (CT6: "observed via call order not just final state").

    Not yet wired into `ui/routes_runs.py::trigger_run` — that endpoint's
    `qa/contracts/ui-run.md` RU3 is ACTIVE and requires "every case in
    `store.list_cases()` gets a real result + verdict saved", which tiered
    filtering would break. Reconciling RU3 with tiered stopping is a
    contract-level call outside D-039's Changes-authorized scope (only
    `qa/contracts/catalog.md`), so it is left as a named gap, not silently
    resolved either direction."""
    result: list[Tier] = []
    for tier in TIER_ORDER:
        if not cat.runnable_in_tier(tier):
            break
        result.append(tier)
    return result
