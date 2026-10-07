"""Who can reach one project: owner, assignees (project.assign) and shared-with
(video.share). The data the scopes `own`, `assigned` and `shared` read (auth.md AU12/13).
"""

from __future__ import annotations

from html import escape

from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from autotester.auth import accounts, audit
from autotester.auth.access import authorize, resource_for, set_relation
from autotester.auth.context import current_principal
from autotester.schema.auth import PermissionKey, ProjectRelation
from autotester.ui import theme
from autotester.ui.helpers import _load_project_or_404

router = APIRouter()

_KEY_FOR = {ProjectRelation.ASSIGNED: PermissionKey.PROJECT_ASSIGN,
            ProjectRelation.SHARED: PermissionKey.VIDEO_SHARE}


def _people(title: str, emails: list[str]) -> str:
    items = "".join(f"<li>{escape(e)}</li>" for e in emails) or "<li>nobody</li>"
    return f"<h3>{title}</h3><ul>{items}</ul>"


@router.get("/projects/{slug}/access", response_class=HTMLResponse)
def project_access_view(slug: str) -> str:
    _store, project = _load_project_or_404(slug)
    res = resource_for(slug)
    form = (
        f"<form method='post' action='/projects/{escape(slug)}/access'>"
        "<div class='field'><label for='email'>Account email</label>"
        "<input id='email' name='email' type='email' required></div>"
        "<div class='field'><label for='relation'>Relation</label>"
        "<select id='relation' name='relation'><option value='shared'>shared with</option>"
        "<option value='assigned'>assigned to (sub-admin)</option></select></div>"
        "<div class='field'><label for='change'>Change</label><select id='change' "
        "name='change'><option value='add'>add</option><option value='remove'>remove"
        "</option></select></div><button class='btn' type='submit'>Save</button></form>"
    )
    body = (theme.breadcrumb(("Projects", "/"), (escape(project.name), f"/projects/{slug}"),
                             ("Access", None))
            + "<h1>Access</h1>"
            + theme.card(_people("Owner", [res.owner_email] if res.owner_email else [])
                         + _people("Assigned", sorted(res.assignees))
                         + _people("Shared with", sorted(res.shared_with)))
            + theme.card(form, title="Change access"))
    return theme.page(f"{escape(project.name)} — access", body, active_slug=slug)


@router.post("/projects/{slug}/access")
def project_access_submit(slug: str, email: str = Form(...), relation: str = Form(...),
                          change: str = Form("add")) -> Response:
    _load_project_or_404(slug)
    who = current_principal()
    try:
        rel = ProjectRelation(relation)
        key = _KEY_FOR[rel]
    except (ValueError, KeyError) as exc:
        raise HTTPException(400, "relation must be 'assigned' or 'shared'") from exc
    if who is None or not authorize(who, key, resource_for(slug)):
        raise HTTPException(403, "you do not have permission for this action")
    target = accounts.find_user(email)
    if target is None:
        raise HTTPException(400, "no account with that email")
    set_relation(slug, target.id, rel, change != "remove")
    audit.record_action(actor=who.email, target=f"{slug}:{target.email}",
                        action=f"project.{rel.value}.{'remove' if change == 'remove' else 'add'}")
    return RedirectResponse(f"/projects/{slug}/access", status_code=303)
