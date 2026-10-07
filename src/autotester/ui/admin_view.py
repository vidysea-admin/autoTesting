"""Markup for the admin pages: accounts, groups and the permission checkboxes (AU8, AU10).

Every control has a visible label; permissions are grouped by area and each scoped key
shows one checkbox per scope the catalogue allows.
"""

from __future__ import annotations

from html import escape

from autotester.auth.defaults import PERMISSION_SECTIONS
from autotester.schema.auth import CATALOGUE, Group, User
from autotester.ui import theme


def _post(action: str, inner: str, label: str, tone: str = "btn btn-sm") -> str:
    return (f"<form method='post' action='{action}' style='display:inline'>{inner}"
            f"<button class='{tone}' type='submit'>{label}</button></form>")


def _group_boxes(user: User, groups: list[Group]) -> str:
    boxes = "".join(
        f"<label style='margin-right:10px'><input type='checkbox' name='group_id' "
        f"value='{g.id}'{' checked' if user.id in g.member_ids else ''}> {escape(g.name)}</label>"
        for g in groups)
    return _post(f"/admin/users/{user.id}/groups", boxes, "Save groups")


def _user_row(user: User, groups: list[Group]) -> str:
    base = f"/admin/users/{user.id}"
    toggle = (_post(f"{base}/enable", "", "Enable") if user.disabled
              else _post(f"{base}/disable", "", "Disable"))
    reset = _post(f"{base}/password",
                  "<label>New password <input type='password' name='password' "
                  "minlength='10' maxlength='128' required></label> ", "Reset password")
    name = _post(f"{base}/name",
                 f"<label>Display name <input name='display_name' "
                 f"value='{escape(user.display_name)}' maxlength='80'></label> ", "Save name")
    state = theme.pill("disabled", "neutral") if user.disabled else theme.pill("active",
                                                                               "positive")
    return (f"<tr><td>{escape(user.email)}<br>{state}</td><td>{_group_boxes(user, groups)}</td>"
            f"<td>{name}<br>{reset}</td><td>{toggle} "
            f"{_post(f'{base}/delete', '', 'Delete', 'btn btn-sm btn-danger')}</td></tr>")


def users_body(users: list[User], groups: list[Group], message: str = "") -> str:
    note = f"<p class='subtitle' role='alert'>{escape(message)}</p>" if message else ""
    rows = "".join(_user_row(u, groups) for u in users)
    table = ("<table><tr><th>Account</th><th>Groups</th><th>Details</th><th>Actions</th>"
             f"</tr>{rows}</table>")
    return (theme.breadcrumb(("Projects", "/"), ("Users", None)) + "<h1>Users</h1>"
            "<p class='subtitle'>A new account has no access until you add it to a group. "
            "<a href='/admin/groups'>Edit groups</a></p>" + note + theme.card(table))


def permission_boxes(selected: set[str]) -> str:
    sections = []
    for heading, keys in PERMISSION_SECTIONS:
        items = []
        for key in keys:
            values = ([key.value] if not CATALOGUE[key]
                      else [f"{key.value}@{s.value}" for s in CATALOGUE[key]])
            boxes = "".join(
                f"<label style='margin-right:10px'><input type='checkbox' name='permission' "
                f"value='{v}'{' checked' if v in selected else ''}> "
                f"{escape(v.partition('@')[2] or 'on')}</label>" for v in values)
            items.append(f"<div><code>{key.value}</code>: {boxes}</div>")
        sections.append(f"<fieldset><legend>{escape(heading)}</legend>{''.join(items)}"
                        "</fieldset>")
    return "".join(sections)


def groups_body(groups: list[Group], message: str = "") -> str:
    note = f"<p class='subtitle' role='alert'>{escape(message)}</p>" if message else ""
    rows = "".join(
        f"<tr><td><a href='/admin/groups/{g.id}'>{escape(g.name)}</a></td>"
        f"<td>{len(g.member_ids)}</td><td>{len(g.permissions)}</td></tr>" for g in groups)
    create = ("<form method='post' action='/admin/groups'><div class='field'>"
              "<label for='name'>Group name</label><input id='name' name='name' required "
              "maxlength='64'></div>" + permission_boxes(set())
              + "<button class='btn btn-primary' type='submit'>Create group</button></form>")
    return (theme.breadcrumb(("Projects", "/"), ("Groups", None)) + "<h1>Groups</h1>" + note
            + theme.card("<table><tr><th>Group</th><th>Members</th><th>Permissions</th></tr>"
                         f"{rows}</table>")
            + theme.card(create, title="New group"))


def group_body(group: Group, users: list[User], can_members: bool, message: str = "") -> str:
    note = f"<p class='subtitle' role='alert'>{escape(message)}</p>" if message else ""
    members = "".join(
        f"<label style='margin-right:10px'><input type='checkbox' name='member_id' "
        f"value='{u.id}'{' checked' if u.id in group.member_ids else ''}> "
        f"{escape(u.email)}</label>" for u in users) if can_members else ""
    member_box = (f"<fieldset><legend>Members</legend>{members}"
                  "<input type='hidden' name='members_shown' value='1'></fieldset>"
                  if can_members else "")
    form = (f"<form method='post' action='/admin/groups/{group.id}'><div class='field'>"
            f"<label for='name'>Group name</label><input id='name' name='name' required "
            f"maxlength='64' value='{escape(group.name)}'></div>"
            + permission_boxes(set(group.permissions)) + member_box
            + "<button class='btn btn-primary' type='submit'>Save group</button></form>")
    delete = _post(f"/admin/groups/{group.id}/delete", "", "Delete group…",
                   "btn btn-danger")
    return (theme.breadcrumb(("Projects", "/"), ("Groups", "/admin/groups"),
                             (escape(group.name), None))
            + f"<h1>{escape(group.name)}</h1>" + note + theme.card(form) + delete)


def confirm_delete_body(group: Group) -> str:
    count = len(group.member_ids)
    inner = "<input type='hidden' name='confirm' value='yes'>"
    return (f"<h1>Delete {escape(group.name)}?</h1>" + theme.card(
        f"<p>{count} member{'s' if count != 1 else ''} will lose the permissions of this "
        "group and keep only those of their other groups.</p>"
        + _post(f"/admin/groups/{group.id}/delete", inner, "Delete group", "btn btn-danger")
        + " <a class='btn' href='/admin/groups'>Cancel</a>"))
