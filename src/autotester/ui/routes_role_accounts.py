"""Onboard and edit N role accounts across M platforms (T-208, MP4-MP6).

Routes: `GET/POST /onboard/roles` (a new project, `project.create`, exactly as `POST /onboard`) and
`GET/POST /projects/{slug}/accounts` (an existing project: `project.edit` for the declarations,
and `credentials.edit` on top for any value written to the repo-root `.env`, MP6 / auth.md AU21).
The route policy rows are in `auth/policy.py`; the extra credentials.edit check is
`_require_credentials_edit`, run before anything is saved -- for a value, and for any submission
that re-points an already-declared key (`ro.rescoped_keys`). Values go to `.env` only through
`stages.role_onboarding.write_values` (the env editor) and are never echoed, logged or listed.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from html import escape
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError

from autotester.auth.access import authorize, resource_for, set_owner
from autotester.auth.context import current_principal
from autotester.browser.secrets import SecretStore, parse_env
from autotester.core.paths import ProjectPaths
from autotester.schema.auth import PermissionKey
from autotester.schema.platform import Platform
from autotester.schema.project import Project
from autotester.schema.role_account import RoleAccount
from autotester.stages import role_onboarding as ro
from autotester.store.project_store import ProjectStore
from autotester.ui import role_accounts_view as view
from autotester.ui import theme
from autotester.ui.credential_guard import _refuse_unsafe_submission, refuse_reserved_slug
from autotester.ui.helpers import _load_project_or_404, _require_project_name, _require_slug

router = APIRouter()

_PLAT = ("platform_id", "platform_name", "platform_base_url", "platform_domains",
         "platform_subdomains")
_ACCT = ("account_id", "account_role", "account_platform", "account_tenant", "account_scope",
         "account_user_key", "account_user_value", "account_pass_key", "account_pass_value")
_VALUE_COLUMNS = ("account_user_value", "account_pass_value")
_MAX_PLATFORMS, _MAX_ACCOUNTS = 16, 128


def _rows(form: Mapping[str, object], fields: Sequence[str], limit: int) -> list[dict[str, str]]:
    """Repeated form columns as row dicts. Values are never stripped; a value column that is
    absent (a submitter without credentials.edit gets no value inputs) reads as all blank."""
    cols = {f: [str(v) if f in _VALUE_COLUMNS else str(v).strip()
                for v in form.getlist(f)] for f in fields}  # type: ignore[attr-defined]
    height = max(len(c) for c in cols.values())
    for name in _VALUE_COLUMNS:
        if name in cols and not cols[name]:
            cols[name] = [""] * height
    if len({len(c) for c in cols.values()}) != 1:
        raise HTTPException(400, "the rows are incomplete")
    rows = [dict(zip(fields, vals, strict=True)) for vals in zip(*cols.values(), strict=True)]
    rows = [r for r in rows if any(v for k, v in r.items() if k != "platform_subdomains")]
    if len(rows) > limit:
        raise HTTPException(400, f"at most {limit} rows are accepted in one submission")
    return rows


def parse_platforms(rows: Sequence[dict[str, str]]) -> list[Platform]:
    out: list[Platform] = []
    for n, row in enumerate(rows, 1):
        if not all(row[k] for k in ("platform_id", "platform_name", "platform_base_url",
                                    "platform_domains")):
            raise HTTPException(400, f"platform row {n} is incomplete: id, name, URL and "
                                     "allowed domains are all required")
        try:
            out.append(Platform(
                id=row["platform_id"], name=row["platform_name"],
                base_url=row["platform_base_url"],
                allowed_domains=[d.strip() for d in row["platform_domains"].split(",")
                                 if d.strip()],
                include_subdomains=row["platform_subdomains"] != "no"))
        except ValidationError as exc:
            raise HTTPException(400, f"platform row {n}: "
                                     f"{ro.safe_validation_message(exc)}") from exc
    return out


def parse_accounts(rows: Sequence[dict[str, str]]) -> tuple[
        list[RoleAccount], dict[str, list[str]], dict[str, str]]:
    """Accounts, the typed per-account scopes, and the env values (key -> value)."""
    accounts: list[RoleAccount] = []
    scopes: dict[str, list[str]] = {}
    values: dict[str, str] = {}
    for n, row in enumerate(rows, 1):
        if not all(row[k] for k in ("account_id", "account_role", "account_platform",
                                    "account_user_key", "account_pass_key")):
            raise HTTPException(400, f"account row {n} is incomplete: id, role, platform and "
                                     "both keys are required")
        try:
            acct = RoleAccount(
                id=row["account_id"], role=row["account_role"], platform_id=row["account_platform"],
                tenant_label=row["account_tenant"] or None,
                username_key=row["account_user_key"], password_key=row["account_pass_key"])
        except ValidationError as exc:
            raise HTTPException(400, f"account row {n}: "
                                     f"{ro.safe_validation_message(exc)}") from exc
        accounts.append(acct)
        scopes[acct.id] = [d.strip() for d in row["account_scope"].split(",") if d.strip()]
        for key, col in ((acct.username_key, "account_user_value"),
                         (acct.password_key, "account_pass_value")):
            if row[col]:
                values[key] = row[col]
    return accounts, scopes, values


def _require_credentials_edit(slug: str) -> None:
    """MP6 / AU21: writing a value needs credentials.edit on this project, on top of the
    project.edit the route policy already demanded."""
    who = current_principal()
    if who is None or not authorize(who, PermissionKey.CREDENTIALS_EDIT, resource_for(slug)):
        raise HTTPException(403, "you do not have permission for this action "
                                 f"({PermissionKey.CREDENTIALS_EDIT.value})")


def _texts(platforms: Sequence[Platform], accounts: Sequence[RoleAccount],
           scopes: Mapping[str, Sequence[str]]) -> list[tuple[str, str]]:
    """Every free-text field a person typed, for the pasted-credential scan."""
    out = [(f"platform {p.id}", " ".join((p.name, p.base_url, *p.allowed_domains)))
           for p in platforms]
    out += [(f"account {a.id}", " ".join((a.role, a.tenant_label or "", *scopes.get(a.id, ()))))
            for a in accounts]
    return out


def _guard(project: Project, platforms: Sequence[Platform], accounts: Sequence[RoleAccount],
           scopes: Mapping[str, Sequence[str]], values: dict[str, str],
           present: dict[str, str], *, fresh: bool) -> None:
    """Key namespace, `.env` collision (new project only), and no credential in a text field."""
    refs = project.secrets
    try:
        ro.check_key_namespace(project, refs)
        ro.check_values(values)
    except ro.OnboardingError as exc:
        raise HTTPException(400, str(exc)) from exc
    if fresh and {r.key for r in refs} & set(present):
        raise HTTPException(400, "a credential key is already in use; choose a project-specific "
                                 "key")
    store = SecretStore(project, values, present)
    _refuse_unsafe_submission(_texts(platforms, accounts, scopes), project, store)


def _env_now(slug: str) -> dict[str, str]:
    path = ProjectPaths(slug).env_file
    return parse_env(path.read_text(encoding="utf-8")) if path.exists() else {}


@router.get("/onboard/roles", response_class=HTMLResponse)
def onboard_roles_form() -> str:
    body = (theme.breadcrumb(("Projects", "/"), ("Onboard", "/onboard"), ("Role accounts", None))
            + "<h1>Onboard a project with role accounts</h1>"
            "<p class='subtitle'>Declare the platforms, then one test account per role. Use "
            "this for a product where several kinds of user sign in.</p>"
            + theme.card(view.form_html("/onboard/roles", new_project=True)))
    return theme.page("Onboard with role accounts", body)


@router.post("/onboard/roles")
async def onboard_roles_submit(request: Request) -> RedirectResponse:
    form = await request.form()
    slug, name = str(form.get("slug", "")), str(form.get("name", ""))
    _require_slug(slug)
    _require_project_name(name)
    if ProjectStore(slug).load_project() is not None:
        raise HTTPException(400, "a project with this slug already exists")
    refuse_reserved_slug(slug)
    platforms = parse_platforms(_rows(form, _PLAT, _MAX_PLATFORMS))
    accounts, scopes, values = parse_accounts(_rows(form, _ACCT, _MAX_ACCOUNTS))
    if not platforms:
        raise HTTPException(400, "declare at least one platform")
    try:
        refs = ro.validate_accounts(platforms, accounts, scopes, values)
    except ro.OnboardingError as exc:
        raise HTTPException(400, str(exc)) from exc
    domains = list(dict.fromkeys(d for p in platforms for d in p.allowed_domains))
    project = Project(slug=slug, name=name, base_url=platforms[0].base_url,
                      allowed_domains=domains, platforms=platforms, role_accounts=accounts,
                      secrets=refs)
    _guard(project, platforms, accounts, scopes, values, _env_now(slug), fresh=True)
    who = current_principal()
    _commit(ProjectStore(slug), project, None, values,   # AU8 vocabulary: the creator owns it
            who.user_id if who is not None and who.user_id else None)
    return RedirectResponse(f"/projects/{slug}/accounts", status_code=303)


def _restore(env_path: Path, snapshot: bytes | None, store: ProjectStore,
             previous: Project | None) -> None:
    """Put `.env` and project.json back as they were before a failed commit."""
    if snapshot is None:
        env_path.unlink(missing_ok=True)
    else:
        env_path.write_bytes(snapshot)
    if previous is None:
        store.paths.config.unlink(missing_ok=True)
    else:
        store.save_project(previous)


def _commit(store: ProjectStore, updated: Project, previous: Project | None,
            values: dict[str, str], owner_id: int | None) -> None:
    """`.env` first (atomic), then project.json, then the owner grant. A failure after the
    first write restores both files, so a failed write never leaves a saved project -- and a
    new project never exists without its owner."""
    env_path = store.paths.env_file
    snapshot = env_path.read_bytes() if env_path.exists() else None
    try:
        if values:
            ro.write_values(env_path, values)
        store.save_project(updated)
        if owner_id is not None:
            set_owner(store.paths.slug, owner_id)
    except Exception:
        _restore(env_path, snapshot, store, previous)
        raise


def _scope_of(project: Project, acct: RoleAccount) -> list[str]:
    """The domains a stored account's username key is scoped to (an untouched account keeps it)."""
    ref = project.secret(acct.username_key)
    return list(ref.domains) if ref is not None else []


def _merged(project: Project, platforms: list[Platform], accounts: list[RoleAccount],
            scopes: dict[str, list[str]]) -> tuple[list[Platform], list[RoleAccount]]:
    """The project after the submission; accounts it did not mention keep their stored scope."""
    base = project.effective_platforms()
    merged_platforms = ro.merge_by_id(base, platforms) if platforms else base
    merged_accounts = ro.merge_by_id(project.role_accounts or [], accounts)
    for acct in project.role_accounts or []:
        scopes.setdefault(acct.id, _scope_of(project, acct))
    return merged_platforms, merged_accounts


@router.post("/projects/{slug}/accounts")
async def accounts_submit(slug: str, request: Request) -> RedirectResponse:
    store, project = _load_project_or_404(slug)
    form = await request.form()
    new_platforms = parse_platforms(_rows(form, _PLAT, _MAX_PLATFORMS))
    new_accounts, scopes, values = parse_accounts(_rows(form, _ACCT, _MAX_ACCOUNTS))
    if values:
        _require_credentials_edit(slug)  # MP6: before any write, project.json included
    platforms, accounts = _merged(project, new_platforms, new_accounts, scopes)
    try:
        refs = ro.validate_accounts(platforms, accounts, scopes, values)
    except ro.OnboardingError as exc:
        raise HTTPException(400, str(exc)) from exc
    env_now = _env_now(slug)
    if ro.rescoped_keys(project, refs, accounts, env_now):
        _require_credentials_edit(slug)  # MP6: re-pointing a key is a credential action
    kept = [s for s in project.secrets if s.key not in {r.key for r in refs}]
    domains = list(dict.fromkeys([*project.allowed_domains,
                                  *(d for p in new_platforms for d in p.allowed_domains)]))
    updated = project.model_copy(update={
        "platforms": platforms if (project.platforms or new_platforms) else None,
        "role_accounts": accounts, "secrets": [*kept, *refs],
        "allowed_domains": domains})
    _guard(updated.model_copy(update={"secrets": refs}), platforms, accounts,
           scopes, values, env_now, fresh=False)
    _commit(store, updated, project, values, None)
    return RedirectResponse(f"/projects/{slug}/accounts", status_code=303)


@router.get("/projects/{slug}/accounts", response_class=HTMLResponse)
def accounts_view(slug: str) -> str:
    _store, project = _load_project_or_404(slug)
    who = current_principal()
    res = resource_for(slug)
    may_edit = who is not None and authorize(who, PermissionKey.PROJECT_EDIT, res)
    may_values = who is not None and authorize(who, PermissionKey.CREDENTIALS_EDIT, res)
    safe, name = escape(slug), escape(project.name)
    parts = [theme.breadcrumb(("Projects", "/"), (name, f"/projects/{safe}"),
                              ("Role accounts", None)),
             "<h1>Role accounts</h1>", view.platforms_card(project),
             view.accounts_card(project)]
    if may_edit:
        pairs = [(a, ", ".join(_scope_of(project, a))) for a in project.role_accounts or []]
        parts.append(theme.card(view.form_html(
            f"/projects/{safe}/accounts", platforms=project.platforms or [], accounts=pairs,
            new_project=False, values=may_values, min_platforms=1, min_accounts=2),
            title="Add or change accounts"))
    return theme.page(f"{name} - role accounts", "".join(parts), active_slug=slug)
