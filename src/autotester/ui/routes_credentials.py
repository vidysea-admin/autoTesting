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

from autotester.browser.secrets import SecretStore, parse_env
from autotester.core.paths import ProjectPaths, repo_root
from autotester.ui import theme
from autotester.ui.env_editor import InvalidEnvValue, set_env_value
from autotester.ui.helpers import _load_project_or_404, _refuse_unsafe_submission
from autotester.ui.routes_crawl_approval import _approvals_card, _crawl_approval_form
from autotester.ui.routes_project_edit import build_secret_ref

router = APIRouter()



def _env_table(project: object, present: dict[str, str]) -> str:
    """The editable credentials table. 2026-09-21 UX amendment (Umesh,
    Approver): the write-only masked editor read as "everything wipes on
    Save". The stored value is now shown IN the field (prefilled) so the
    operator sees what is saved and can edit it; password-shaped keys stay
    masked with a show/hide toggle. Owner-only display in the local UI — the
    SecretStore boundary (values never reach a prompt, log, or screenshot)
    is unchanged."""
    if not project.secrets:  # type: ignore[attr-defined]
        return theme.empty_state("🔑", "This project declares no credentials.")
    _EYE = ("<button type='button' class='btn btn-sm' tabindex='-1' "
            "onclick=\"var i=this.parentNode.querySelector('input');"
            "i.type=i.type==='password'?'text':'password';"
            "this.textContent=i.type==='password'?'show':'hide';\">show</button>")

    def _status_cell(key: str) -> str:
        return (theme.pill("● Set", "positive") if present.get(key)
                else theme.pill("○ Not set", "neutral"))

    def _row(ref: object) -> str:
        key = ref.key  # type: ignore[attr-defined]
        is_secret = "_PASSWORD" in key or "_KEY" in key
        return (
            f"<tr><td>{escape(key)}</td>"
            f"<td>{_status_cell(key)}</td>"
            f"<form method='post' action='env'>"
            f"<input type='hidden' name='key' value='{escape(key)}'>"
            f"<td style='display:flex;gap:6px'>"
            f"<input type='{'password' if is_secret else 'text'}' name='value' "
            f"value='{escape(present.get(key, ''))}' "
            f"placeholder='new value' style='flex:1'>{_EYE if is_secret else ''}"
            f"</td>"
            f"<td><button class='btn btn-sm' type='submit'>Save</button></td></form></tr>"
        )

    rows = "".join(_row(ref) for ref in project.secrets)  # type: ignore[attr-defined]
    header = "<tr><th>Key</th><th>Status</th><th>Value (edit and Save)</th><th></th></tr>"
    return f"<table>{header}{rows}</table>"


def _platform_url_card(slug: str, project: object) -> str:
    """Edit the platform's own URL (base_url) and allowed domains inline.

    2026-09-21 (Umesh): the URL is a credential-adjacent fact an operator
    fixes on the same page as the values — no trip to the project settings
    form, which needs the name and every field re-entered."""
    safe = escape(slug)
    domains = ", ".join(project.allowed_domains)  # type: ignore[attr-defined]
    return theme.card(
        f"<form method='post' action='/projects/{safe}/env/url'>"
        f"<div class='field'><label>Platform URL (base URL)</label>"
        f"<input name='base_url' value='{escape(project.base_url)}' required></div>"  # type: ignore[attr-defined]"
        f"<div class='field'><label>Allowed domains (comma-separated — the browser's "
        f"hard boundary)</label>"
        f"<input name='allowed_domains' value='{escape(domains)}' required></div>"
        "<button class='btn' type='submit'>Save URL</button></form>",
        title="Platform URL",
    )


def _custom_credential_card(slug: str, project: object) -> str:
    """Declare a NEW custom credential AND save its value in one submit."""
    safe = escape(slug)
    scope = ", ".join(project.allowed_domains)  # type: ignore[attr-defined]
    return theme.card(
        f"<form method='post' action='/projects/{safe}/env/add'>"
        f"<div class='field'><label>Key (UPPER_SNAKE_CASE)</label>"
        f"<input name='key' required placeholder='e.g. ERP_TENANT_ID'></div>"
        f"<div class='field'><label>Value</label>"
        f"<input name='value' required placeholder='the value to store'></div>"
        f"<div class='field'><label>Allowed domains (where it may be typed)</label>"
        f"<input name='domains' value='{escape(scope)}' required></div>"
        f"<div class='field'><label>Description (optional)</label>"
        f"<input name='description' placeholder='what this key is for'></div>"
        f"<button class='btn' type='submit'>Add credential</button></form>",
        title="Add a custom credential",
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


@router.post("/projects/{slug}/env/add")
def env_add_credential(
    slug: str, key: str = Form(...), value: str = Form(...),
    domains: str = Form(...), description: str = Form(""),
) -> Response:
    """Declare a custom credential AND save its value in one step.

    Declaration reuses `build_secret_ref` (the same validators the settings
    page uses); the value goes through the one legitimate `.env` write path.
    Refuses a key that is already declared, and a scope outside the project's
    allowed domains — a SecretRef can never widen the browser's boundary."""
    store, project = _load_project_or_404(slug)
    ref = build_secret_ref(project, key, domains, description)
    if project.secret(ref.key) is not None:
        raise HTTPException(400, f"'{ref.key}' is already declared on this project")
    if not value.strip():
        raise HTTPException(400, "a credential needs a value")
    _refuse_unsafe_submission(
        [("the value", value)], project,
        SecretStore.load(project, ProjectPaths(slug).env_file, strict=False),
    )
    store.save_project(project.model_copy(update={"secrets": [*project.secrets, ref]}))
    try:
        set_env_value(repo_root() / ".env", ref.key, value)
    except InvalidEnvValue as exc:
        raise HTTPException(400, str(exc)) from exc
    return RedirectResponse(f"/projects/{slug}/env", status_code=303)


@router.get("/projects/{slug}/env", response_class=HTMLResponse)
def env_editor_view(slug: str, saved: str = "", existing: str = "") -> str:
    store, project = _load_project_or_404(slug)
    paths = ProjectPaths(slug)
    present = (
        parse_env(paths.env_file.read_text(encoding="utf-8")) if paths.env_file.exists() else {}
    )
    name = escape(project.name)
    safe_slug = escape(slug)
    table = _env_table(project, present)
    body = (
        theme.breadcrumb(
            ("Projects", "/"), (name, f"/projects/{safe_slug}"), ("Credentials", None),
        )
        + "<h1>Credentials</h1>"
        "<p class='subtitle'>Saved values are shown here so you can verify and edit them. "
        "They stay masked as ●●● until you press show. They never leave this page — "
        "no prompt, log, or screenshot ever carries them.</p>"
        f"{theme.card(table)}"
        f"{_platform_url_card(slug, project)}"
        f"{_custom_credential_card(slug, project)}"
        f"{_crawl_approval_form(slug, project.base_url)}"
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
        set_env_value(repo_root() / ".env", key, value)
    except InvalidEnvValue as exc:
        raise HTTPException(400, str(exc)) from exc
    return RedirectResponse(f"/projects/{slug}/env", status_code=303)


