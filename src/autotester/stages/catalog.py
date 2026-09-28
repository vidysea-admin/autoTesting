"""CATALOG: derive, per `CaseClass`, whether it applies, whether it can run
right now, and — when it cannot — the one `BlockedReason` plus the action
that clears it.

Contract: qa/contracts/catalog.md CT1-CT8 (D-039). Pure: reads only artifacts
already on disk (the FlowSpec, declared `SecretRef`s, `.env` key presence,
`write_policy`) — no `Provider` call, no network call, no write. Same inputs
-> byte-identical `Catalog`, every call (CT1)."""

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
# class submits at most once, which is already how a READ_ONLY case runs
# today; widening this set is a contract amendment, not a T-125 fix (see
# catalog.md's no-fire list).
_NEEDS_WRITE_CLASSES = frozenset({CaseClass.DOUBLE_SUBMIT})


# Field names meaning "this FILL is a credential for signing in". Judged per
# FILL step, never by partitioning flows: a flow can be BOTH a Google sign-up
# and the product's own login (ISS-t125-3), and an unrelated import flow's
# unset key must not block signing in (ISS-t125-5).
_LOGIN_FIELD_WORDS = ("password", "passwd", "pwd", "passphrase", "username",
                      "user name", "email", "e-mail", "login", "log in",
                      "sign in", "signin", "otp")


def _auth_secret_keys(
    spec: FlowSpec, *, only: set[str] | None = None, login_fields: bool = False
) -> list[str]:
    """`{{SECRET:KEY}}` keys referenced by a FILL step, in first-seen order.

    `only` restricts the walk to those flow ids (the OAuth pack's own scope).
    `login_fields` keeps only keys filled into a credential-named field, and
    GATES the generic auth rows. It matches `target`/`note`, never `value` —
    the value IS the `{{SECRET:...}}` placeholder, so matching it would
    re-admit every `*_PASSWORD`-shaped key. Never returns a value (C5)."""
    keys: list[str] = []
    for flow in spec.flows:
        if only is not None and flow.id not in only:
            continue
        for step in flow.steps:
            if step.action is not Action.FILL or not step.value:
                continue
            field = " ".join(filter(None, [step.target, step.note])).lower()
            if login_fields and not any(w in field for w in _LOGIN_FIELD_WORDS):
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
        runnable=False, blocked_reason=reason, unblock_action=action)


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
    blocked row can name the keys of the flow it is about (ISS-t125-2)."""
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
    return PackEntry(pack=pack, applicable=applicable, runnable=False,
                     blocked_reason=reason, unblock_action=action)


def _pack_entries(
    project: Project, spec: FlowSpec | None, blocking_keys: list[str]
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
            _blocked_pack(p, applicable=detector(spec), action=action,
                          reason=BlockedReason.FLOWSPEC_NOT_APPROVED)
            for p, detector in _PACK_SIGNAL.items()
        ]
    entries: list[PackEntry] = []
    for pack, detector in _PACK_SIGNAL.items():
        if not detector(spec):
            entries.append(PackEntry(pack=pack, applicable=False, runnable=False))
            continue
        if pack is StandardPack.OAUTH_SIGNUP_CARRYOVER and blocking_keys:
            action = "set " + ", ".join(blocking_keys) + " in the repo-root .env"
            entries.append(PackEntry(
                pack=pack, applicable=True, runnable=False, unblock_action=action,
                blocked_reason=BlockedReason.MISSING_CREDENTIAL))
            continue
        entries.append(PackEntry(pack=pack, applicable=True, runnable=True))
    return entries


def _entry_for(
    case_class: CaseClass, project: Project, blocking_keys: list[str]
) -> CatalogEntry:
    tier = TIER_BY_CLASS[case_class]
    if case_class in _AUTH_CLASSES and blocking_keys:
        action = "set " + ", ".join(blocking_keys) + " in the repo-root .env"
        return CatalogEntry(
            case_class=case_class, tier=tier, applicable=True, runnable=False,
            blocked_reason=BlockedReason.MISSING_CREDENTIAL, unblock_action=action)
    if case_class in _NEEDS_WRITE_CLASSES and project.write_policy is WritePolicy.READ_ONLY:
        action = (
            f"raise '{project.slug}'s write_policy from read_only to test_account "
            f"(or allow_writes) to run {case_class.value}"
        )
        return CatalogEntry(
            case_class=case_class, tier=tier, applicable=True, runnable=False,
            blocked_reason=BlockedReason.NEEDS_WRITE_POLICY, unblock_action=action)
    return CatalogEntry(case_class=case_class, tier=tier, applicable=True, runnable=True)


def catalog(project: Project, spec: FlowSpec | None, store: ProjectStore | None = None) -> Catalog:
    """The project's whole catalog: every `CaseClass`, exactly once (CT2).

    `store` is accepted (per D-039's `catalog(project, spec, store)` shape) but
    unused today — every fact this stage needs lives on `project` and `spec`; a
    store-backed fact (e.g. a persisted `RunApproval`) is a future widening,
    not something this signature should have to change for."""
    if spec is None or not spec.flows:
        return _no_flowspec_catalog(project)
    if spec.review.status is not ReviewStatus.APPROVED:
        return _not_approved_catalog(project, spec)
    # Each row is gated on the keys ITS OWN concern reads and worded with that
    # same list, so gate and wording can no longer disagree (ISS-t125-2/5).
    # Auth rows take the credential-named FILLs anywhere in the spec (a hybrid
    # OAuth+password flow keeps its key, ISS-t125-3); the OAuth pack takes its
    # own flows'. No recognisable credential field -> fall back to every
    # declared key: "nothing unblocks this" is the worse lie.
    login_keys = _auth_secret_keys(spec, login_fields=True)
    all_missing = _missing_keys(project, _auth_secret_keys(spec))
    missing_login = _missing_keys(project, login_keys) if login_keys else all_missing
    oauth_ids = _oauth_signup_flow_ids(spec)
    missing_oauth = _missing_keys(project, _auth_secret_keys(spec, only=oauth_ids))
    entries = [_entry_for(cc, project, missing_login) for cc in CaseClass]
    return Catalog(
        project=project.slug, entries=entries,
        packs=_pack_entries(project, spec, missing_oauth),
    )


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
