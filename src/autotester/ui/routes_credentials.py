"""The credentials editor: values shown (editable, passwords masked with a
show/hide toggle), custom-credential declaration, and the platform URL.

Contract: qa/contracts/ui.md U3 as amended 2026-09-21 by Umesh (Approver):
stored values render INTO the field for owner verification/editing; an empty
Save is refused, never a wipe.
"""

from __future__ import annotations

from html import escape

from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from autotester.auth.access import authorize
from autotester.auth.context import current_principal
from autotester.browser.secrets import SecretStore, host_of, parse_env
from autotester.core.env import resolve_credentials
from autotester.core.paths import ProjectPaths, repo_root
from autotester.schema.auth import PermissionKey
from autotester.schema.case import Case
from autotester.schema.project import Project, SecretRef
from autotester.stages.role_onboarding import login_keys
from autotester.stages.run_gates import derive_live_case_grant, planned_cases
from autotester.store.project_store import ProjectStore
from autotester.ui import theme
from autotester.ui.credential_guard import refuse_server_key
from autotester.ui.env_editor import InvalidEnvValue, save_credentials, validate_env_values
from autotester.ui.helpers import _load_project_or_404, _refuse_unsafe_submission
from autotester.ui.role_accounts_view import (
    account_login_card,
    custom_credential_card,
    env_table,
    redisplayable_key,
)
from autotester.ui.routes_crawl_approval import _approvals_card, _crawl_approval_form
from autotester.ui.routes_project_edit import build_secret_ref

router = APIRouter()



def can_view_credentials() -> bool:
    """T-204 G4 / auth.md AU21: saved values render only for `credentials.view`.
    Outside a request (no principal) nothing is rendered either."""
    who = current_principal()
    return who is not None and authorize(who, PermissionKey.CREDENTIALS_VIEW)


def _platform_url_card(slug: str, project: object) -> str:
    """Edit the platform's own URL (base_url) and allowed domains inline.

    2026-09-21 (Umesh): the URL is a credential-adjacent fact an operator
    fixes on the same page as the values — no trip to the project settings
    form, which needs the name and every field re-entered."""
    safe = escape(slug)
    domains = ", ".join(project.allowed_domains)
    return theme.card(
        f"<form method='post' action='/projects/{safe}/env/url'>"
        f"<div class='field'><label for='pu-base-url'>Platform URL (base URL)</label>"
        f"<input id='pu-base-url' name='base_url' "
        f"value='{escape(project.base_url)}' required></div>"  # type: ignore[attr-defined]"
        f"<div class='field'><label for='pu-domains'>Allowed domains (comma-separated — the "
        f"browser's hard boundary)</label>"
        f"<input id='pu-domains' name='allowed_domains' value='{escape(domains)}' required></div>"
        "<button class='btn' type='submit'>Save URL</button></form>",
        title="Platform URL",
    )


@router.post("/projects/{slug}/env/url")
def env_url_submit(
    slug: str, base_url: str = Form(...), allowed_domains: str = Form(...),
) -> Response:
    """Update the platform URL + allowed domains from the credentials page.

    Reuses the project-settings write path's guards verbatim (reachability,
    the unsafe-submission scan) — a second implementation would drift."""
    store, project = _load_project_or_404(slug)
    domains = [d.strip() for d in allowed_domains.split(",") if d.strip()]
    if not domains:
        raise HTTPException(400, "a project needs at least one allowed domain")
    from autotester.ui.helpers import _require_reachable_base_url

    _require_reachable_base_url(base_url, domains)
    _refuse_unsafe_submission(
        [("the base URL", base_url), ("allowed domains", allowed_domains)],
        project, SecretStore.load(project, ProjectPaths(slug).env_file, strict=False),
        exempt={"the base URL": project.base_url,
                "allowed domains": ", ".join(project.allowed_domains)},
    )
    store.save_project(project.model_copy(update={
        "base_url": base_url.strip(), "allowed_domains": domains,
    }))
    return RedirectResponse(f"/projects/{slug}/env", status_code=303)


def refuse_pasted_secrets(
    project: Project, texts: list[tuple[str, str]], submitted: list[str],
) -> None:
    """Refuse a field that is about to be shown again if it holds a real credential: whatever
    `.env` and the credential store hold, plus the values in this very submission (E3.5)."""
    fresh = {f"SUBMITTED_{n}": v for n, v in enumerate(submitted) if v.strip()}
    for held in (SecretStore.load(project, ProjectPaths(project.slug).env_file, strict=False),
                 SecretStore(project, {}, fresh)):
        _refuse_unsafe_submission(
            texts, project, held, exempt={"the scope": ", ".join(project.allowed_domains)})


def login_submission(
    project: Project, email: str, password: str, scope: str,
) -> tuple[list[SecretRef], dict[str, str]]:
    """The "Test account login" block (E3.3/E3.4) -> its two generated declarations and values.
    Scope defaults to the project URL host and goes through `build_secret_ref`, so it can never
    leave the allowed domains. A wholly empty block means "no login" (onboarding may skip it)."""
    if not email.strip() and not password.strip():
        return [], {}
    if not email.strip() or not password.strip():
        raise HTTPException(400, "give both the email or username and the password")
    keys = login_keys(project.slug)
    what = ("test account email or username", "test account password")
    refs = [build_secret_ref(project, key, scope.strip() or host_of(project.base_url), note,
                             mask_in_screenshot=True)
            for key, note in zip(keys, what, strict=True)]
    return refs, dict(zip(keys, (email.strip(), password), strict=True))


def _save_login(
    slug: str, store: ProjectStore, project: Project, form: dict[str, str],
) -> Response:
    refs, values = login_submission(
        project, form["login_email"], form["login_password"], form["login_scope"])
    if not values:
        raise HTTPException(400, "type the email or username and the password")
    validate_env_values(values)
    kept = [r for r in project.secrets if r.key not in values]  # a resubmit replaces, never adds
    store.save_project(project.model_copy(update={"secrets": [*kept, *refs]}))
    save_credentials(slug, repo_root() / ".env", values)
    return RedirectResponse(f"/projects/{slug}/env", status_code=303)


def _save_custom(
    slug: str, store: ProjectStore, project: Project, form: dict[str, str],
) -> Response:
    ref = build_secret_ref(project, form["key"], form["domains"], form["description"])
    if project.secret(ref.key) is not None:
        raise HTTPException(400, f"'{ref.key}' is already declared on this project")
    if not form["value"].strip():
        raise HTTPException(400, "a credential needs a value")
    _refuse_unsafe_submission(
        [("the value", form["value"])], project,
        SecretStore.load(project, ProjectPaths(slug).env_file, strict=False),
    )
    validate_env_values({ref.key: form["value"]})
    store.save_project(project.model_copy(update={"secrets": [*project.secrets, ref]}))
    save_credentials(slug, repo_root() / ".env", {ref.key: form["value"]})
    return RedirectResponse(f"/projects/{slug}/env", status_code=303)


@router.post("/projects/{slug}/env/add")
def env_add_credential(
    slug: str, key: str = Form(""), value: str = Form(""), domains: str = Form(""),
    description: str = Form(""), block: str = Form(""), login_email: str = Form(""),
    login_password: str = Form(""), login_scope: str = Form(""),
) -> Response:
    """Save the "Test account login" block (`block=login`) or declare a custom credential AND
    save its value in one step. Declaration reuses `build_secret_ref` (the same validators the
    settings page uses); values go through the one legitimate `.env` write path. A refusal that
    only concerns what was typed (bad key, scope outside the allowed domains, a half-filled login)
    re-renders this page with a plain message and the NON-secret fields kept; a value is never
    echoed (AT-1417, C5). A SecretRef can never widen the browser's boundary."""
    store, project = _load_project_or_404(slug)
    form = {"key": key, "value": value, "domains": domains, "description": description,
            "login_email": login_email, "login_password": login_password,
            "login_scope": login_scope}
    scan = [("the scope", login_scope)] if block == "login" else [
        ("the key", key), ("the description", description), ("the scope", domains)]
    # a pasted secret in a field that is about to be shown again is refused BEFORE it is shown
    refuse_pasted_secrets(project, scan, [value, login_email, login_password])
    try:
        return (_save_login if block == "login" else _save_custom)(slug, store, project, form)
    except InvalidEnvValue as exc:
        problem = HTTPException(400, str(exc))
    except HTTPException as exc:
        if exc.status_code != 400:
            raise
        problem = exc
    typed = {k: form[k] for k in ("domains", "description", "login_scope")}
    typed["key"] = redisplayable_key(key)
    return HTMLResponse(env_editor_view(slug, error=str(problem.detail), typed=typed),
                        status_code=400)


_GRANT_SCRIPT = (
    "<script>(()=>{const f=document.querySelector(\"[name='expires_at']\").form,d={};"
    "const live={max_actions:f.dataset.liveActions,max_probes:f.dataset.liveProbes,"
    "wall_clock_s:f.dataset.liveWall},base={max_actions:200,max_probes:4000,wall_clock_s:600};"
    "for(const n in live)f[n].addEventListener('input',()=>{d[n]=1;});"
    "f.kind.addEventListener('change',()=>{for(const n in live)"
    "if(!d[n])f[n].value=f.kind.value==='live_case'?live[n]:base[n];});})();</script>"
)


def _grant_prefill(cases: list[Case]) -> tuple[str, str]:
    """D-112 item 2: (form attributes, note + script) carrying the bounds derived from the
    planned cases. Picking kind `live_case` fills the three inputs with them; a field the
    human has edited is never overwritten. No planned cases: nothing, the old defaults stand."""
    if not cases:
        return "", ""
    got = derive_live_case_grant(cases)
    attrs = (f" data-live-actions='{got.actions}' data-live-probes='{got.probes}'"
             f" data-live-wall='{got.wall_clock_s:g}'")
    note = (f"<p class='meta'>For a live_case run the bounds are derived from "
            f"{len(cases)} planned case(s): {got.actions} actions, {got.probes} probes, "
            f"{got.wall_clock_s:g}s of target time (with margin). Pick the kind to fill them; "
            "edit any value.</p>")
    return attrs, note + _GRANT_SCRIPT


@router.get("/projects/{slug}/env", response_class=HTMLResponse)
def env_editor_view(slug: str, saved: str = "", existing: str = "", *, error: str = "",
                    typed: dict[str, str] | None = None) -> str:
    """The Credentials page. `error`/`typed` (AT-1417, passed by `env_add_credential`, never by
    the query string) are a refused submit's plain message and its NON-secret fields; the page
    never refills a value box."""
    store, project = _load_project_or_404(slug)
    paths = ProjectPaths(slug)
    on_disk = (
        parse_env(paths.env_file.read_text(encoding="utf-8")) if paths.env_file.exists() else {}
    )
    present = resolve_credentials(on_disk, slug, {s.key for s in project.secrets})[0]
    name = escape(project.name)
    safe_slug = escape(slug)
    show = can_view_credentials()
    typed = typed or {}
    table = env_table(project, present, show)
    prefill = _grant_prefill(planned_cases(store))
    note = ("Saved values are shown here so you can verify and edit them. "
            "They stay masked as ●●● until you press show." if show else
            "Each key shows only whether it is set. Type a new value to replace it; "
            "saved values are visible only to accounts with credentials.view.")
    login = account_login_card(slug, typed.get("login_scope") or host_of(project.base_url),
                       all(project.secret(k) is not None for k in login_keys(slug)))
    body = (
        theme.breadcrumb(
            ("Projects", "/"), (name, f"/projects/{safe_slug}"), ("Credentials", None),
        )
        + "<h1>Credentials</h1>"
        + (theme.form_error(error) if error else "")
        + f"<p class='subtitle'>{note} They never leave this page — "
        "no prompt, log, or screenshot ever carries them.</p>"
        f"{login}"
        f"{theme.card(table)}"
        f"{_platform_url_card(slug, project)}"
        f"{custom_credential_card(slug, ', '.join(project.allowed_domains), typed)}"
        f"{_crawl_approval_form(slug, project.base_url, project.production, prefill)}"
        f"{_approvals_card(store.list_approvals(), slug, project.base_url, saved, bool(existing))}"
    )
    return theme.page(f"{name} — credentials", body, active_slug=slug)


@router.post("/projects/{slug}/env")
def env_editor_submit(
    slug: str, key: str = Form(...), value: str = Form("")
) -> Response:
    _store, project = _load_project_or_404(slug)
    if project.secret(key) is None:
        raise HTTPException(400, f"'{key}' is not a declared secret for '{slug}'")
    refuse_server_key(key)  # AU21: even a legacy declaration cannot write a server key
    if not value.strip():
        # An empty field means "nothing typed", never "erase" — the input is a
        # masked write-only box (placeholder 'new value'), so a submit with
        # nothing in it is a stray Save press. Overwriting a stored secret
        # with '' was a silent credential WIPE (2026-09-21: a password saved
        # while its neighbour email's Save was pressed with an empty field
        # blanked the email). Refuse; the stored value survives.
        safe = escape(slug)
        body = theme.breadcrumb(("Projects", "/"), (escape(project.name), f"/projects/{safe}"),
                                ("Credentials", None))
        body += "<h1>Credential not saved</h1>" + theme.card(
            f"<p>No new value was typed for <code>{escape(key)}</code>, so nothing was "
            f"changed — the stored value (if any) is untouched.</p>"
            f"<p><a class='btn' href='/projects/{safe}/env'>Return to credentials</a></p>",
            title="Empty fields are ignored",
        )
        return HTMLResponse(theme.page("Credential not saved", body, active_slug=slug),
                            status_code=400)
    try:
        save_credentials(slug, repo_root() / ".env", {key: value})
    except InvalidEnvValue as exc:
        raise HTTPException(400, str(exc)) from exc
    return RedirectResponse(f"/projects/{slug}/env", status_code=303)


