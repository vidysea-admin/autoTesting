"""HTML for the role-account onboarding form and the saved-accounts listing (T-208, MP4).

One job: render. It never reads a stored value: value inputs are always empty and write-only,
and the listing shows account ids, roles, platforms, tenant labels and KEY names only. Every
interpolated string is escaped.
"""

from __future__ import annotations

from collections.abc import Sequence
from html import escape

from autotester.schema.platform import Platform
from autotester.schema.project import Project
from autotester.schema.role_account import RoleAccount
from autotester.ui import theme

_ADD_ROW = (
    "<script>document.querySelectorAll('[data-add-row]').forEach(b=>b.onclick=()=>{"
    "const body=document.getElementById(b.dataset.addRow);"
    "const row=body.lastElementChild.cloneNode(true);"
    "row.querySelectorAll('input').forEach(i=>{i.value='';});body.appendChild(row);});</script>"
)


def _input(name: str, label: str, value: str = "", *, kind: str = "text", hint: str = "") -> str:
    auto = " autocomplete='new-password'" if kind == "password" else " autocomplete='off'"
    return (f"<td><input name='{name}' type='{kind}' value='{escape(value, quote=True)}' "
            f"aria-label='{escape(label)}' placeholder='{escape(hint, quote=True)}'{auto}></td>")


def platform_row(plat: Platform | None = None) -> str:
    subs = "no" if plat is not None and not plat.include_subdomains else "yes"
    select = (f"<td><select name='platform_subdomains' aria-label='Include subdomains'>"
              f"<option value='yes'{' selected' if subs == 'yes' else ''}>yes</option>"
              f"<option value='no'{' selected' if subs == 'no' else ''}>no (exact hosts)</option>"
              "</select></td>")
    return ("<tr>"
            + _input("platform_id", "Platform id", plat.id if plat else "", hint="school")
            + _input("platform_name", "Platform name", plat.name if plat else "",
                     hint="School portal")
            + _input("platform_base_url", "Platform URL", plat.base_url if plat else "",
                     hint="https://school.example.com/")
            + _input("platform_domains", "Allowed domains",
                     ", ".join(plat.allowed_domains) if plat else "", hint="school.example.com")
            + select + "</tr>")


def account_row(acct: RoleAccount | None = None, scope: str = "", *, values: bool = True) -> str:
    a = acct
    cells = (
        _input("account_id", "Account id", a.id if a else "", hint="teacher1")
        + _input("account_role", "Role", a.role if a else "", hint="Class teacher")
        + _input("account_platform", "Platform id", a.platform_id if a else "", hint="school")
        + _input("account_tenant", "Tenant label", (a.tenant_label or "") if a else "",
                 hint="school A")
        + _input("account_scope", "May be typed into", scope, hint="platform domains")
        + _input("account_user_key", "Username key", a.username_key if a else "",
                 hint="PROJ_T1_USER")
    )
    cells += (_input("account_user_value", "Username value (write-only)", hint="set or change")
              if values else "<td class='meta'>-</td>")
    cells += _input("account_pass_key", "Password key", a.password_key if a else "",
                    hint="PROJ_T1_PASS")
    cells += (_input("account_pass_value", "Password value (write-only)", kind="password",
                     hint="set or change") if values else "<td class='meta'>-</td>")
    return f"<tr>{cells}</tr>"


def form_html(action: str, *, platforms: Sequence[Platform] = (),
              accounts: Sequence[tuple[RoleAccount, str]] = (), new_project: bool,
              values: bool = True, min_platforms: int = 3, min_accounts: int = 8) -> str:
    """The submission form. Saved rows are prefilled; blank rows pad up to the minimums."""
    plat_rows = [platform_row(p) for p in platforms]
    plat_rows += [platform_row() for _ in range(max(0, min_platforms - len(plat_rows)))]
    acct_rows = [account_row(a, scope, values=values) for a, scope in accounts]
    acct_rows += [account_row(values=values) for _ in range(max(0, min_accounts - len(acct_rows)))]
    basics = (
        "<div class='field'><label for='f-slug'>Project slug</label>"
        "<input id='f-slug' name='slug' placeholder='my-product' required></div>"
        "<div class='field'><label for='f-name'>Name</label>"
        "<input id='f-name' name='name' required></div>" if new_project else "")
    plat_head = ("<tr><th>Id</th><th>Name</th><th>URL</th><th>Allowed domains</th>"
                 "<th>Subdomains</th></tr>")
    acct_head = ("<tr><th>Id</th><th>Role</th><th>Platform</th><th>Tenant</th>"
                 "<th>May be typed into</th><th>Username key</th>"
                 + ("<th>Username value</th>" if values else "<th></th>")
                 + "<th>Password key</th>" + ("<th>Password value</th>" if values else "<th></th>")
                 + "</tr>")
    return (
        f"<form method='post' action='{escape(action, quote=True)}'>{basics}"
        "<h3>Platforms</h3><p class='meta'>Each linked product the accounts sign in to.</p>"
        f"<table><thead>{plat_head}</thead><tbody id='platform-rows'>{''.join(plat_rows)}"
        "</tbody></table><button type='button' class='btn' data-add-row='platform-rows'>"
        "Add platform</button>"
        "<h3>Role accounts</h3><p class='meta'>Keys must start with the project's own "
        "prefix. Values are written to the repo-root .env and never shown again; leave a value "
        "empty to declare the account only. Leave the scope empty to use the platform's "
        "domains.</p>"
        f"<table><thead>{acct_head}</thead><tbody id='account-rows'>{''.join(acct_rows)}"
        "</tbody></table><button type='button' class='btn' data-add-row='account-rows'>"
        "Add account</button>"
        "<p><button class='btn btn-primary' type='submit'>Save role accounts</button></p>"
        f"</form>{_ADD_ROW}")


def accounts_card(project: Project) -> str:
    """Every account with role, platform and tenant label, and the keys (never values)."""
    rows = "".join(
        "<tr>" + "".join(f"<td>{escape(cell)}</td>" for cell in (
            a.id, a.role, a.platform_id, a.tenant_label or "-", a.username_key, a.password_key))
        + "</tr>" for a in project.role_accounts or [])
    if not rows:
        return theme.empty_state("👥", "No role accounts declared yet.")
    head = ("<tr><th>Account</th><th>Role</th><th>Platform</th><th>Tenant</th>"
            "<th>Username key</th><th>Password key</th></tr>")
    return theme.card(f"<table>{head}{rows}</table>", title="Role accounts")


def platforms_card(project: Project) -> str:
    rows = "".join(
        "<tr>" + "".join(f"<td>{escape(cell)}</td>" for cell in (
            p.id, p.name, p.base_url, ", ".join(p.allowed_domains),
            "yes" if p.include_subdomains else "exact hosts")) + "</tr>"
        for p in project.effective_platforms())
    head = "<tr><th>Id</th><th>Name</th><th>URL</th><th>Domains</th><th>Subdomains</th></tr>"
    return theme.card(f"<table>{head}{rows}</table>", title="Platforms")
