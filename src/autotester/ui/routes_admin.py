"""Admin routes: accounts (users.manage, AU8) and groups (groups.manage, AU10).

The route policy table already requires the key before any handler runs; the handlers
re-check it through `authorize` (AU12) and refuse with a message, never a partial
write, when the store refuses (last admin, unknown permission, unknown group).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from autotester.auth import accounts, audit, groups
from autotester.auth.access import authorize
from autotester.auth.context import current_principal
from autotester.auth.db import LastAdmin
from autotester.auth.passwords import WeakPassword
from autotester.schema.auth import PermissionKey, Principal
from autotester.ui import admin_view, theme

router = APIRouter()
_REFUSED = (accounts.AccountError, groups.GroupError, LastAdmin, WeakPassword)


def _require(key: PermissionKey) -> Principal:
    who = current_principal()
    if who is None or not authorize(who, key):
        raise HTTPException(403, "you do not have permission")
    return who


def _users_page(message: str = "", status: int = 200) -> HTMLResponse:
    body = admin_view.users_body(accounts.list_users(), groups.list_groups(), message)
    return HTMLResponse(theme.page("Users", body), status_code=status)


def _ints(values: list[object]) -> list[int]:
    try:
        return [int(str(v)) for v in values]
    except ValueError as exc:
        raise HTTPException(400, "invalid id") from exc


@router.get("/admin/users", response_class=HTMLResponse)
def admin_users() -> HTMLResponse:
    _require(PermissionKey.USERS_MANAGE)
    return _users_page()


@router.post("/admin/users/{user_id}/{action}")
async def admin_user_action(user_id: int, action: str, request: Request) -> Response:
    who = _require(PermissionKey.USERS_MANAGE)
    form = await request.form()
    target = accounts.get_user(user_id)
    if target is None:
        raise HTTPException(404, "no such account")
    try:
        if action == "groups":
            accounts.set_user_groups(user_id, _ints(form.getlist("group_id")))
        elif action in {"disable", "enable"}:
            accounts.set_disabled(user_id, action == "disable")
        elif action == "delete":
            accounts.delete_user(user_id)
        elif action == "password":
            accounts.reset_password(user_id, str(form.get("password", "")))
        elif action == "name":
            accounts.set_display_name(user_id, str(form.get("display_name", "")))
        else:
            raise HTTPException(404, "unknown action")
    except _REFUSED as exc:
        return _users_page(str(exc), status=400)
    audit.record_action(actor=who.email, target=target.email, action=f"user.{action}")
    return RedirectResponse("/admin/users", status_code=303)


@router.get("/admin/groups", response_class=HTMLResponse)
def admin_groups() -> HTMLResponse:
    _require(PermissionKey.GROUPS_MANAGE)
    return HTMLResponse(theme.page("Groups", admin_view.groups_body(groups.list_groups())))


@router.post("/admin/groups")
async def admin_group_create(request: Request) -> Response:
    who = _require(PermissionKey.GROUPS_MANAGE)
    form = await request.form()
    try:
        group = groups.create_group(str(form.get("name", "")),
                                    [str(v) for v in form.getlist("permission")])
    except _REFUSED as exc:
        body = admin_view.groups_body(groups.list_groups(), str(exc))
        return HTMLResponse(theme.page("Groups", body), status_code=400)
    audit.record_action(actor=who.email, target=group.name, action="group.create")
    return RedirectResponse(f"/admin/groups/{group.id}", status_code=303)


def _group_or_404(group_id: int):
    group = groups.get_group(group_id)
    if group is None:
        raise HTTPException(404, "no such group")
    return group


@router.get("/admin/groups/{group_id}", response_class=HTMLResponse)
def admin_group_view(group_id: int) -> HTMLResponse:
    who = _require(PermissionKey.GROUPS_MANAGE)
    group = _group_or_404(group_id)
    body = admin_view.group_body(group, accounts.list_users(),
                                 authorize(who, PermissionKey.USERS_MANAGE))
    return HTMLResponse(theme.page(group.name, body))


@router.post("/admin/groups/{group_id}")
async def admin_group_update(group_id: int, request: Request) -> Response:
    """Members change only for a holder of users.manage who was shown the member boxes."""
    who = _require(PermissionKey.GROUPS_MANAGE)
    group = _group_or_404(group_id)
    form = await request.form()
    can_members = authorize(who, PermissionKey.USERS_MANAGE)
    members = (_ints(form.getlist("member_id"))
               if can_members and form.get("members_shown") else None)
    try:
        groups.update_group(group_id, str(form.get("name", "")),
                            [str(v) for v in form.getlist("permission")], members)
    except _REFUSED as exc:
        body = admin_view.group_body(group, accounts.list_users(), can_members, str(exc))
        return HTMLResponse(theme.page(group.name, body), status_code=400)
    audit.record_action(actor=who.email, target=group.name, action="group.update")
    return RedirectResponse(f"/admin/groups/{group_id}", status_code=303)


@router.post("/admin/groups/{group_id}/delete")
async def admin_group_delete(group_id: int, request: Request) -> Response:
    """First POST shows how many members lose access; the confirmed POST deletes."""
    who = _require(PermissionKey.GROUPS_MANAGE)
    group = _group_or_404(group_id)
    form = await request.form()
    if form.get("confirm") != "yes":
        return HTMLResponse(theme.page("Delete group", admin_view.confirm_delete_body(group)))
    try:
        groups.delete_group(group_id)
    except _REFUSED as exc:
        body = admin_view.groups_body(groups.list_groups(), str(exc))
        return HTMLResponse(theme.page("Groups", body), status_code=400)
    audit.record_action(actor=who.email, target=group.name, action="group.delete")
    return RedirectResponse("/admin/groups", status_code=303)
