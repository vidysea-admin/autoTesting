"""Edit a project's own settings after onboarding. Contract: qa/contracts/ui.md.

AT-058: getting the allowed domains wrong once made a project permanently
unrunnable, and there was no route anywhere to change them — `routes_credentials`
edits `.env` values only, never `project.json`. So a user who mistyped at
onboarding had to either abandon the project or edit JSON by hand.

Only the three fields a human can get wrong at onboarding are editable here:
name, base_url, allowed_domains. The slug is the project's identity (it names
the directory every artifact already lives under) and is deliberately NOT
editable — renaming it would orphan runs, cases and the browser profile.

This module also owns the project's `SecretRef` declarations (Track 0, Unit 0.1 of
the 2026-09-07 plan; gate `qa/gates/at052-bfs-video-corpus-grill.md`).
Until now nothing anywhere wrote `project.json::secrets`, so a project always
declared zero credentials — which made `/projects/<slug>/env` render "This
project declares no credentials" and reject every save. A logged-in test was
therefore impossible to set up through the UI at all. Declaring a key here is
what makes that page usable; the VALUE still only ever lives in the repo-root
`.env`, written by `ui/env_editor.py`, and is never handled by this module.
"""

from __future__ import annotations

from html import escape

from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError

from autotester.browser.secrets import SecretStore
from autotester.core.paths import ProjectPaths
from autotester.schema.project import Project, SecretRef
from autotester.ui import theme
from autotester.ui.helpers import (
    _load_project_or_404,
    _refuse_unsafe_submission,
    _require_project_name,
    _require_reachable_base_url,
)

router = APIRouter()


def build_secret_ref(
    project: Project, key: str, domains: str, description: str = "",
    *, mask_in_screenshot: bool = True,
) -> SecretRef:
    """Build one scoped reference without ever including its submitted value in errors."""
    scope = [domain.strip() for domain in domains.split(",") if domain.strip()]
    if not scope:
        raise HTTPException(400, "name at least one host this credential may be typed into")
    if any(not project.allows_domain(domain.lower().lstrip(".")) for domain in scope):
        raise HTTPException(400, "credential scope must stay inside the project's allowed domains")
    try:
        return SecretRef(
            key=key.strip(), description=description.strip() or None, domains=scope,
            mask_in_screenshot=mask_in_screenshot,
        )
    except ValidationError as exc:
        why = exc.errors()[0]["msg"]
        raise HTTPException(400, f"cannot declare this credential: {why}") from exc


def parse_secret_rows(
    project: Project, keys: list[str], values: list[str], domains: list[str],
    descriptions: list[str],
) -> tuple[list[SecretRef], dict[str, str]]:
    """Validate repeated onboarding rows as one all-or-nothing credential batch."""
    counts = {len(keys), len(values), len(domains), len(descriptions)}
    if len(counts) != 1:
        raise HTTPException(400, "credential rows are incomplete")
    refs: list[SecretRef] = []
    secret_values: dict[str, str] = {}
    for key, value, scope, description in zip(keys, values, domains, descriptions, strict=True):
        if not any(item.strip() for item in (key, value, scope, description)):
            continue
        if not key.strip() or not scope.strip():
            raise HTTPException(400, "each credential needs a key and allowed domain")
        ref = build_secret_ref(project, key, scope, description)
        if ref.key in {item.key for item in refs}:
            raise HTTPException(400, "credential keys must be unique")
        refs.append(ref)
        if value:
            secret_values[ref.key] = value
    return refs, secret_values


def _secret_row(safe_slug: str, ref: SecretRef) -> str:
    """One declared key. Shows the KEY and its scope only — a SecretRef holds no
    value, and this module never touches one."""
    key = escape(ref.key)
    mask = "masked" if ref.mask_in_screenshot else "not masked"
    return (
        "<tr>"
        f"<td><code>{key}</code></td>"
        f"<td class='meta'>{escape(ref.description or '')}</td>"
        f"<td class='meta'>{escape(', '.join(ref.domains))}</td>"
        f"<td class='meta'>{mask}</td>"
        f"<td><form method='post' action='/projects/{safe_slug}/secrets/{key}/delete'>"
        "<button class='btn btn-danger' type='submit'>Remove</button></form></td>"
        "</tr>"
    )


def _secrets_card(safe_slug: str, project: Project) -> str:
    """Declare which credentials this project needs. Values are entered
    separately on the Credentials page and stored only in the repo-root
    `.env` — nothing here ever sees one."""
    default_domains = escape(", ".join(project.allowed_domains))
    if project.secrets:
        rows = "".join(_secret_row(safe_slug, r) for r in project.secrets)
        table = (
            "<table><tr><th>Key</th><th>What it is</th><th>May be typed into</th>"
            "<th>Screenshots</th><th></th></tr>"
            f"{rows}</table>"
        )
    else:
        table = (
            "<p class='meta'>No credentials declared yet — this project can only test "
            "pages that need no login.</p>"
        )
    form = (
        f"<form method='post' action='/projects/{safe_slug}/secrets'>"
        "<div class='field'><label for='key'>Key</label>"
        "<input id='key' name='key' placeholder='ERP_PASSWORD' required>"
        "<span class='hint'>a NAME for the credential in CAPITALS, digits and underscores "
        "— e.g. ERP_PASSWORD. The value itself is entered later, on the Credentials "
        "page.</span></div>"
        "<div class='field'><label for='description'>What it is</label>"
        "<input id='description' name='description' "
        "placeholder='the test account's password'></div>"
        "<div class='field'><label for='domains'>May be typed into</label>"
        f"<input id='domains' name='domains' value='{default_domains}' required>"
        "<span class='hint'>comma-separated hosts. The value is only ever typed on "
        "these, never anywhere else.</span></div>"
        "<div class='field'><label><input type='checkbox' name='mask_in_screenshot' "
        "value='on' checked> Hide it in screenshots</label></div>"
        "<button class='btn btn-primary' type='submit'>Declare credential</button>"
        "</form>"
    )
    return theme.card(
        "<p class='subtitle' style='margin-bottom:1rem'>Which credentials this project needs. "
        "Declaring a key here makes it enterable on the "
        f"<a href='/projects/{safe_slug}/env'>Credentials</a> page — the value itself is "
        "stored outside the project and is never shown again.</p>"
        f"{table}<hr style='border:0;border-top:1px solid var(--border);margin:1.4rem 0'>{form}",
        title="Credentials this project needs",
    )


@router.get("/projects/{slug}/edit", response_class=HTMLResponse)
def edit_project_form(slug: str) -> str:
    _store, project = _load_project_or_404(slug)
    safe_slug = escape(slug)
    name = escape(project.name)
    fields = (
        "<div class='field'><label for='name'>Name</label>"
        f"<input id='name' name='name' value='{name}' required></div>"
        "<div class='field'><label for='base_url'>Base URL</label>"
        f"<input id='base_url' name='base_url' value='{escape(project.base_url)}' required>"
        "<span class='hint'>where a run starts — its host must be covered below</span></div>"
        "<div class='field'><label for='allowed_domains'>Allowed domains</label>"
        "<input id='allowed_domains' name='allowed_domains' "
        f"value='{escape(', '.join(project.allowed_domains))}' required>"
        "<span class='hint'>comma-separated — the browser will never navigate outside "
        "these. There is no wildcard: name every host you mean.</span></div>"
        "<button class='btn btn-primary' type='submit'>Save changes</button>"
    )
    form = f"<form method='post' action='/projects/{safe_slug}/edit'>{fields}</form>"
    body = (
        theme.breadcrumb(("Projects", "/"), (name, f"/projects/{safe_slug}"),
                          ("Settings", None))
        + "<h1>Project settings</h1>"
        "<p class='subtitle'>The slug never changes — every run, case and browser profile "
        "is filed under it.</p>"
        f"{theme.card(form)}"
        f"{_secrets_card(safe_slug, project)}"
    )
    return theme.page("Project settings", body, active_slug=slug)


@router.post("/projects/{slug}/edit")
def edit_project_submit(
    slug: str,
    name: str = Form(...),
    base_url: str = Form(...),
    allowed_domains: str = Form(...),
) -> RedirectResponse:
    store, project = _load_project_or_404(slug)
    _require_project_name(name)
    domains = [d.strip() for d in allowed_domains.split(",") if d.strip()]
    if not domains:
        raise HTTPException(400, "a project needs at least one allowed domain")
    _require_reachable_base_url(base_url, domains)
    _refuse_unsafe_submission(
        [("the name", name), ("the base URL", base_url),
         ("allowed domains", allowed_domains)],
        project, SecretStore.load(project, ProjectPaths(slug).env_file, strict=False),
        # AT-078/AT-087: re-saving this project's own stored value for EACH
        # field is a no-op, not a paste -- per-field, never cross-field.
        exempt={
            "the name": project.name,
            "the base URL": project.base_url,
            "allowed domains": ", ".join(project.allowed_domains),
        },
    )

    store.save_project(project.model_copy(update={
        "name": name.strip(), "base_url": base_url.strip(), "allowed_domains": domains,
    }))
    return RedirectResponse(f"/projects/{slug}", status_code=303)


@router.post("/projects/{slug}/secrets")
def declare_secret(
    slug: str,
    key: str = Form(...),
    domains: str = Form(...),
    description: str = Form(default=""),
    mask_in_screenshot: str = Form(default=""),
) -> RedirectResponse:
    """Declare a credential this project needs. Stores the KEY and its scope on
    `project.json::secrets`; the value is entered separately and lives only in
    the repo-root `.env`. `SecretRef`'s own validators do the checking — this
    route only turns their ValidationError into a readable 400."""
    store, project = _load_project_or_404(slug)
    # AT-073/AT-080: `key` is the FIRST box on this form and was never checked --
    # an all-uppercase credential satisfies SecretRef's own key pattern, so only
    # the description/scope boxes stood between a pasted value and a git-tracked
    # project.json. Checked alongside them now, not just the ones beside it.
    _refuse_unsafe_submission(
        [("the key", key), ("the description", description), ("the scope", domains)],
        project, SecretStore.load(project, ProjectPaths(slug).env_file, strict=False),
        exempt={"the scope": ", ".join(project.allowed_domains)},
    )
    ref = build_secret_ref(
        project, key, domains, description, mask_in_screenshot=bool(mask_in_screenshot),
    )
    if project.secret(ref.key) is not None:
        raise HTTPException(400, f"'{ref.key}' is already declared on this project")

    store.save_project(project.model_copy(update={"secrets": [*project.secrets, ref]}))
    return RedirectResponse(f"/projects/{slug}/edit", status_code=303)


@router.post("/projects/{slug}/secrets/{key}/delete")
def undeclare_secret(slug: str, key: str) -> RedirectResponse:
    """Stop declaring a key. Any value already in `.env` is left alone — this
    module never touches values — but the key becomes unusable, which is the
    point: an undeclared key is refused at typing time."""
    store, project = _load_project_or_404(slug)
    if project.secret(key) is None:
        raise HTTPException(404, f"no declared credential '{key}'")
    kept = [r for r in project.secrets if r.key != key]
    store.save_project(project.model_copy(update={"secrets": kept}))
    return RedirectResponse(f"/projects/{slug}/edit", status_code=303)
