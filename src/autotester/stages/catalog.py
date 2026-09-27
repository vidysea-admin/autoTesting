"""CATALOG: derive, per `CaseClass`, whether it applies, whether it can run
right now, and — when it cannot — the one `BlockedReason` plus the action
that clears it.

Contract: qa/contracts/catalog.md CT1-CT8 (D-039). Pure: reads only artifacts
already on disk (the FlowSpec, declared `SecretRef`s, `.env` key presence,
`write_policy`) — no `Provider` call, no network call, no write of anything
it reads. Same inputs on disk -> byte-identical `Catalog`, every call (CT1).
"""

from __future__ import annotations

from collections.abc import Callable

from autotester.browser.secrets import SecretStore
from autotester.core.paths import ProjectPaths
from autotester.core.redact import PLACEHOLDER_RE
from autotester.schema.catalog import (
    TIER_BY_CLASS,
    TIER_ORDER,
    BlockedReason,
    Catalog,
    CatalogEntry,
    PackEntry,
    StandardPack,
    Tier,
)
from autotester.schema.enums import Action, CaseClass, ReviewStatus, WritePolicy
from autotester.schema.flowspec import FlowSpec, Step
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


def _auth_secret_keys(spec: FlowSpec, *, only: set[str] | None = None) -> list[str]:
    """`{{SECRET:KEY}}` keys referenced by a FILL step, in first-seen order.

    `only` restricts the walk to those flow ids. ISS-t125-2: collecting across
    every flow made each blocked row advertise the UNION of every unset key in
    the project, so an `auth_wrong_creds` row told the operator to set a
    sign-up-only token that has nothing to do with signing in — worse than
    vague, because one of the two named actions is a no-op for that row.
    Never returns a value (C5) — only key names."""
    keys: list[str] = []
    for flow in spec.flows:
        if only is not None and flow.id not in only:
            continue
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


def _no_flowspec_action(project: Project) -> str:
    return (
        f"record a source (video, doc, or URL) for '{project.slug}' and run INGEST "
        "(or explore it) to produce a FlowSpec"
    )


def _not_approved_action(project: Project) -> str:
    return f"review and approve the FlowSpec at /projects/{project.slug}/flowspec"


def _no_flowspec_catalog(project: Project) -> Catalog:
    action = _no_flowspec_action(project)
    entries = [
        _blocked(cc, applicable=False, reason=BlockedReason.NO_FLOWSPEC, action=action)
        for cc in CaseClass
    ]
    return Catalog(project=project.slug, entries=entries, packs=_pack_entries(project, None, []))


def _not_approved_catalog(project: Project, spec: FlowSpec) -> Catalog:
    action = _not_approved_action(project)
    entries = [
        _blocked(cc, applicable=True, reason=BlockedReason.FLOWSPEC_NOT_APPROVED, action=action)
        for cc in CaseClass
    ]
    return Catalog(project=project.slug, entries=entries, packs=_pack_entries(project, spec, []))


# -- AT-588: standard packs on top of the generic CaseClass taxonomy --------


def _text_of(step: Step) -> str:
    """Lower-cased target+value+note, for keyword-based signal detection."""
    return " ".join(filter(None, [step.target, step.value, step.note])).lower()


def _oauth_signup_flow_ids(spec: FlowSpec) -> set[str]:
    """Ids of the flows that carry the Pack-1 signal: a CLICK/NAVIGATE step
    naming a Google OAuth sign-up. Per-flow rather than a whole-spec bool so a
    blocked row can name the keys of the flow it is actually about
    (ISS-t125-2)."""
    ids: set[str] = set()
    for flow in spec.flows:
        for step in flow.steps:
            if step.action not in (Action.CLICK, Action.NAVIGATE):
                continue
            text = _text_of(step)
            if "google" in text or "oauth" in text or "accounts.google.com" in text:
                ids.add(flow.id)
                break
    return ids


def _has_oauth_signup_carryover(spec: FlowSpec) -> bool:
    """Pack 1 applicability — the spec-level view of `_oauth_signup_flow_ids`."""
    return bool(_oauth_signup_flow_ids(spec))


def _has_date_picker_month_year(spec: FlowSpec) -> bool:
    """Pack 2: a field typed date/month/year, or a step naming one."""
    for screen in spec.screens:
        for field in screen.fields:
            if field.type.lower() in {"date", "month", "year"}:
                return True
    for flow in spec.flows:
        for step in flow.steps:
            text = _text_of(step)
            if "date picker" in text or ("month" in text and "year" in text):
                return True
    return False


def _has_excel_column_mapping(spec: FlowSpec) -> bool:
    """Pack 3: an UPLOAD step naming a spreadsheet file."""
    for flow in spec.flows:
        for step in flow.steps:
            if step.action is Action.UPLOAD and any(
                ext in _text_of(step) for ext in (".xlsx", ".xls", ".csv", "excel")
            ):
                return True
    return False


_PACK_SIGNAL: dict[StandardPack, Callable[[FlowSpec], bool]] = {
    StandardPack.OAUTH_SIGNUP_CARRYOVER: _has_oauth_signup_carryover,
    StandardPack.DATE_PICKER_MONTH_YEAR: _has_date_picker_month_year,
    StandardPack.EXCEL_COLUMN_MAPPING: _has_excel_column_mapping,
}


def _blocked_pack(
    pack: StandardPack, *, applicable: bool, reason: BlockedReason, action: str
) -> PackEntry:
    return PackEntry(
        pack=pack, applicable=applicable, runnable=False, blocked_reason=reason,
        unblock_action=action,
    )


def _pack_entries(
    project: Project, spec: FlowSpec | None, missing_oauth_keys: list[str]
) -> list[PackEntry]:
    """One `PackEntry` per `StandardPack` (AT-588): same blocking states as the
    CaseClass table (`no_flowspec` / `flowspec_not_approved`), plus a
    missing-credential check on the OAuth pack (it signs in against a real
    Google account). A pack whose structural signal is absent from the
    approved spec is simply not applicable — that is not a block."""
    if spec is None or not spec.flows:
        action = _no_flowspec_action(project)
        return [
            _blocked_pack(p, applicable=False, reason=BlockedReason.NO_FLOWSPEC, action=action)
            for p in StandardPack
        ]
    if spec.review.status is not ReviewStatus.APPROVED:
        action = _not_approved_action(project)
        return [
            _blocked_pack(
                p, applicable=detector(spec), reason=BlockedReason.FLOWSPEC_NOT_APPROVED,
                action=action,
            )
            for p, detector in _PACK_SIGNAL.items()
        ]
    entries: list[PackEntry] = []
    for pack, detector in _PACK_SIGNAL.items():
        if not detector(spec):
            entries.append(PackEntry(pack=pack, applicable=False, runnable=False))
            continue
        if pack is StandardPack.OAUTH_SIGNUP_CARRYOVER and missing_oauth_keys:
            action = "set " + ", ".join(missing_oauth_keys) + " in the repo-root .env"
            entries.append(PackEntry(
                pack=pack, applicable=True, runnable=False,
                blocked_reason=BlockedReason.MISSING_CREDENTIAL, unblock_action=action,
            ))
            continue
        entries.append(PackEntry(pack=pack, applicable=True, runnable=True))
    return entries


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
        return _not_approved_catalog(project, spec)
    # ISS-t125-2: two scopes, not one union. The OAuth pack is about the flow
    # that signs up through Google; the generic auth classes are about the
    # product's own credential form, i.e. every OTHER flow. A spec whose only
    # flow is the OAuth one falls back to all of its keys rather than naming
    # none — an empty action would read as "nothing unblocks this".
    oauth_ids = _oauth_signup_flow_ids(spec)
    other_ids = {f.id for f in spec.flows} - oauth_ids
    missing_oauth = _missing_keys(project, _auth_secret_keys(spec, only=oauth_ids))
    missing_auth = _missing_keys(
        project, _auth_secret_keys(spec, only=other_ids or None)
    )
    entries = [_entry_for(cc, project, missing_auth) for cc in CaseClass]
    packs = _pack_entries(project, spec, missing_oauth)
    return Catalog(project=project.slug, entries=entries, packs=packs)


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
