"""Shared visual system for every UI route. Contract: qa/contracts/docker.md D5.

One place for styling (anti-drift C3) — every route in `ui/app.py` calls
`page()`/`card()`/`stat()`/`empty_state()` to build its HTML; no route writes
its own `<style>` block or reinvents a layout primitive.

Design identity: a "technical instrument," not a generic SaaS dashboard —
Fraunces (a characterful serif with real optical weight) for headings and the
wordmark, IBM Plex Sans for body copy, IBM Plex Mono for anything that reads
like data (ids, run numbers, badges) — this is a tool that drives a real
browser and reports real evidence, and the type should feel like an
instrument panel, not a marketing page. One committed accent (signal amber,
`--accent`) carries every primary action and the brand mark; PASS/FAIL/etc.
keep their own semantic colors so a result badge is never confused with a
button.
"""

from __future__ import annotations

from html import escape

from autotester.auth.access import authorize, visible_slugs
from autotester.auth.context import current_principal
from autotester.schema.auth import PermissionKey
from autotester.store.project_store import ProjectStore
from autotester.ui.helpers import _project_slugs
from autotester.ui.theme_style import PAGE_STYLE

# (permission, href, label, extra class): shown only to an account that holds the key (AU25)
_NAV_LINKS = (
    (None, "/", "Projects", ""),
    (None, "/profile", "My profile", ""),
    (PermissionKey.PROJECT_CREATE, "/onboard", "+ New project", ""),
    (PermissionKey.REPORT_VIEW, "/inbox", "My reports", ""),
    (PermissionKey.VIDEO_VIEW, "/shared", "Videos", ""),
    (PermissionKey.ACCESS_APPROVE, "/access-requests", "Access requests", ""),
    (PermissionKey.LIVE_VIEW, "/live", "● Live view", " class=\"nav-live\""),
    (PermissionKey.SETTINGS_MANAGE, "/settings/providers", "⚙ Settings", ""),
)


def may(key: PermissionKey | None) -> bool:
    who = current_principal()
    return key is None or who is None or authorize(who, key)


def _nav_html() -> str:
    """The top bar. A link the account would get a 403 on is not rendered."""
    links = "".join(f"<a href=\"{href}\"{extra}>{label}</a>"
                    for key, href, label, extra in _NAV_LINKS if may(key))
    return ("<header class=\"topbar\"><a class=\"brand\" href=\"/\">"
            "<span class=\"brand-mark\">AT</span><span class=\"brand-name\">AutoTester"
            f"</span></a><nav>{links}</nav></header>")


_BADGE_CLASS = {
    "PASS": ("badge-pass", "✓"), "FAIL": ("badge-fail", "✕"),
    "BLOCKED": ("badge-blocked", "⏸"), "INCONCLUSIVE": ("badge-inconclusive", "?"),
}


def badge(value: str, count: int | None = None) -> str:
    """A colored `<span>` for a test RESULT value (PASS/FAIL/BLOCKED/INCONCLUSIVE)
    already HTML-escaped by the caller. Never reuse this for a non-test-result
    status (credential presence, review state) — that's what `pill()` is for;
    the two vocabularies read as the same thing to a user otherwise. Pass
    `count` to render a compact "N RESULT" summary badge (e.g. a run-history
    row) instead of a single case's own result — same color/icon lookup."""
    cls, icon = _BADGE_CLASS.get(value, ("badge-inconclusive", ""))
    label = f"{count} {value}" if count is not None else value
    return f"<span class='badge {cls}'>{icon} {label}</span>"


_PILL_CLASS = {
    "positive": "badge-pass", "warning": "badge-blocked", "neutral": "badge-inconclusive",
    "danger": "badge-fail",
}


def pill(text: str, tone: str = "neutral") -> str:
    """A colored status label for anything that ISN'T a test result — credential
    presence, review state, connection state. `text` must already be escaped."""
    cls = _PILL_CLASS.get(tone, "badge-inconclusive")
    return f"<span class='badge {cls}'>{text}</span>"


def stat(value: str, label: str) -> str:
    """One metric tile — a big number/value with a small label under it."""
    return (
        f"<div class='stat'><div class='value'>{value}</div>"
        f"<div class='label'>{label}</div></div>"
    )


def breadcrumb(*crumbs: tuple[str, str | None]) -> str:
    """A real "← Back" button plus the trail, for every page that isn't home.

    Each crumb is `(label, href)`; the current page passes `href=None`. The
    back button targets the LAST crumb that has an href — the natural parent —
    so `Projects / Demo / Credentials` goes back to Demo, not all the way home.

    Labels must already be caller-escaped, same discipline as `page()`. This
    exists because the trail alone was a 0.78rem muted uppercase line that read
    as a location label, not a control: "there is no back button for easy
    navigation" (Umesh, 2026-09-07), and eight routes had each hand-written
    their own copy of the same markup."""
    parent = next((href for _label, href in reversed(crumbs) if href), None)
    back = (
        f"<a class='btn btn-back' href='{parent}'>&larr; Back</a>" if parent else ""
    )
    trail = " / ".join(
        f"<a href='{href}'>{label}</a>" if href else label for label, href in crumbs
    )
    return f"<div class='crumbs'>{back}<div class='breadcrumb'>{trail}</div></div>"


def card(body: str, title: str | None = None) -> str:
    heading = f"<h2>{title}</h2>" if title else ""
    return f"<div class='card'>{heading}{body}</div>"


def empty_state(icon: str, message: str, action_html: str = "") -> str:
    return (
        f"<div class='empty-state'><div class='icon'>{icon}</div>"
        f"<p>{message}</p>{action_html}</div>"
    )


def _sidebar_html(active_slug: str | None) -> str:
    """Every onboarded project, one place, on every page (ui-sidebar.md
    US1-US4) — the same `_project_slugs()`/`ProjectStore` lookup `index()`
    already uses, so this is never a second source of truth for what
    projects exist."""
    who = current_principal()  # T-204 AU13: only what this account may view
    slugs = _project_slugs() if who is None else visible_slugs(who, _project_slugs())
    if not slugs:
        links = "<p class='sidebar-empty'>No projects yet.</p>"
    else:
        rows = []
        for slug in slugs:
            project = ProjectStore(slug).load_project()
            name = escape(project.name) if project else escape(slug)
            cls = " active" if slug == active_slug else ""
            rows.append(
                f"<a class='sidebar-link{cls}' href='/projects/{escape(slug)}'>{name}</a>"
            )
            if cls:  # the open project's benchmark inputs (T-136 marks, T-218 answer list)
                rows.append(f"<a class='sidebar-sub' href='/projects/{escape(slug)}/bench'>"
                            "Benchmark inputs</a>")
        links = "".join(rows)
    add = ("<a class='sidebar-add' href='/onboard'>+ New project</a>"
           if may(PermissionKey.PROJECT_CREATE) else "")
    return (
        "<aside class='sidebar'>"
        "<div class='sidebar-header'>Projects</div>"
        f"<nav class='sidebar-nav'>{links}</nav>"
        f"{add}</aside>"
    )


def _account_html() -> str:
    """T-204 AU25: the signed-in identity chip, the admin links this account may use,
    and the sign-out control. Empty outside a signed-in request."""
    who = current_principal()
    if who is None or not who.user_id:
        return ""
    links = "".join(
        f"<a href='{href}'>{label}</a>" for key, href, label in (
            (PermissionKey.USERS_MANAGE, "/admin/users", "Users"),
            (PermissionKey.GROUPS_MANAGE, "/admin/groups", "Groups"))
        if authorize(who, key))
    return (f"<div class='account-bar' style='display:flex;gap:10px;align-items:center;"
            f"justify-content:flex-end;padding:4px 16px'>{links}"
            f"<span class='pill' title='signed in'>{escape(who.display_name or who.email)}"
            "</span><form method='post' action='/auth/logout' style='display:inline'>"
            "<button class='btn btn-sm' type='submit'>Sign out</button></form></div>")


def page(title: str, body: str, active_slug: str | None = None) -> str:
    """Wrap one route's HTML fragment in the shared stylesheet + nav +
    sidebar + main container. `title` and `body` must already be
    caller-escaped where they carry user/project data — this function adds
    no escaping of its own, matching every route's existing `html.escape`
    discipline (ui.md U5). `active_slug` highlights the current project in
    the sidebar on a project-scoped page; omit it on a global page."""
    sidebar = _sidebar_html(active_slug)
    top = f"{_nav_html()}{_account_html()}"
    return (
        f"<!doctype html><title>{title} — AutoTester</title>{PAGE_STYLE}{top}"
        f"<div class='layout'>{sidebar}<main>{body}</main></div>"
    )
