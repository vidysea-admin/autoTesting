"""The project page's action card — the operator's control panel for one product.

Split out of `app.py` when that file crossed its 300-line cap. It sits beside
`case_form.py`, `crawl_view.py` and `env_editor.py`, which are the same idea:
`app.py` owns routes, these own the markup a route renders.
"""

from __future__ import annotations

from datetime import UTC, datetime
from html import escape

from autotester.auth.access import authorize, resource_for
from autotester.auth.context import current_principal
from autotester.schema.auth import PermissionKey
from autotester.stages.report_export import valid_runs_newest_first
from autotester.store.project_store import ProjectStore
from autotester.ui import team_run_view, theme
from autotester.ui.routes_report import _run_counts


def _credential_row() -> str:
    return (
        "<div class='intake-row credential-row'>"
        "<input name='credential_key' aria-label='Credential key' placeholder='DEMO_EMAIL'>"
        "<input type='password' name='credential_value' aria-label='Credential value' "
        "placeholder='value (stored only in .env)'>"
        "<input name='credential_domains' aria-label='Credential domains' "
        "placeholder='app.example.com'>"
        "<input name='credential_description' aria-label='Credential description' "
        "placeholder='test account email'></div>"
    )


def _source_row() -> str:
    return (
        "<div class='intake-row source-row'><select name='source_kind' "
        "aria-label='Source type'>"
        "<option value=''>Choose type</option><option value='url'>URL / Drive link</option>"
        "<option value='video'>Video path</option><option value='doc'>Document path</option>"
        "<option value='text'>Inline text</option></select>"
        "<input name='source_value' aria-label='Source value' placeholder='link, path, or text'>"
        "<input name='source_label' aria-label='Source label' "
        "placeholder='what this source teaches'></div>"
    )


def intake_form() -> str:
    """The single operator entry point for both taught and URL/account-only modes."""
    basics = (
        "<div class='field'><label for='f-slug'>Project slug</label><input id='f-slug' name='slug' "
        "placeholder='my-product' required></div>"
        "<div class='field'>"
        "<label for='f-name'>Name</label>"
        "<input id='f-name' name='name' required></div>"
        "<div class='field'>"
        "<label for='f-base-url'>URL</label>"
        "<input id='f-base-url' name='base_url' type='url' required "
        "placeholder='https://app.example.com/signin'></div>"
        "<div class='field'>"
        "<label for='f-allowed-domains'>Allowed domains</label>"
        "<input id='f-allowed-domains' name='allowed_domains' "
        "required placeholder='app.example.com'><span class='hint'>Comma-separated; the browser "
        "never leaves these hosts.</span></div>"
    )
    teaching = (
        "<div class='field'><label for='f-evals'>Evals (one per line)</label>"
        "<textarea id='f-evals' name='evals'></textarea></div>"
        "<div class='field'><label for='f-conditions'>Conditions / business rules</label>"
        "<textarea id='f-conditions' name='conditions'></textarea></div>"
        "<div class='field'><label for='f-use-cases'>Use cases / taught flows</label>"
        "<textarea id='f-use-cases' name='use_cases'></textarea></div>"
    )
    repeaters = (
        f"<h3>Test-account credentials</h3><div id='credential-rows'>{_credential_row()}</div>"
        "<button type='button' data-add='credential'>Add another credential</button>"
        f"<h3>Optional sources</h3><div id='source-rows'>{_source_row()}</div>"
        "<button type='button' data-add='source'>Add another source</button>"
        "<script>document.querySelectorAll('[data-add]').forEach(b=>b.onclick=()=>{"
        "const kind=b.dataset.add,box=document.getElementById(kind+'-rows');"
        "box.insertAdjacentHTML('beforeend',box.firstElementChild.outerHTML);});</script>"
    )
    return (f"<form method='post' action='/onboard'>{basics}{repeaters}{teaching}"
            "<button class='btn btn-primary' type='submit'>Create project</button></form>")


def _tracker_link(safe_slug: str) -> str:
    """The bug-tracker link, only for a principal holding report.view on this project
    (the same rule the route enforces centrally); no principal means the gate is off."""
    who = current_principal()
    if who is not None and not authorize(who, PermissionKey.REPORT_VIEW,
                                         resource_for(safe_slug)):
        return ""
    return f"<a class='btn' href='/projects/{safe_slug}/tracker'>🐞 Bug tracker</a>"


def _actions_card(safe_slug: str, run_button: str, case_count: int) -> str:
    """The project's action row, plus — when it has no cases yet — a prompt
    saying what to do next. AT-057: a project with zero cases can run nothing,
    so a disabled Run button on its own was a dead end for a non-technical
    user, with no route anywhere to add the case that would fix it."""
    card = theme.card(
        "<p class='subtitle' style='margin-bottom:1rem'>Manage this project.</p>"
        "<div class='card-actions'>"
        f"{run_button}"
        f"{team_run_view.button_html(safe_slug)}"
        f"<a class='btn' href='/projects/{safe_slug}/flowspec'>🎬 FlowSpec</a>"
        f"<a class='btn' href='/projects/{safe_slug}/sources'>📼 Sources</a>"
        f"<a class='btn' href='/projects/{safe_slug}/product-map'>🗺 Product map</a>"
        f"<a class='btn' href='/projects/{safe_slug}/issues'>⚠ Issues</a>"
        f"{_tracker_link(safe_slug)}"
        f"<a class='btn' href='/projects/{safe_slug}/cases'>🧪 Cases</a>"
        f"<a class='btn' href='/projects/{safe_slug}/cases/new'>+ Add case</a>"
        f"<a class='btn' href='/projects/{safe_slug}/env'>🔑 Credentials</a>"
        f"<a class='btn' href='/projects/{safe_slug}/accounts'>👥 Role accounts</a>"
        f"<a class='btn' href='/projects/{safe_slug}/bench'>📏 Benchmark inputs</a>"
        f"<a class='btn' href='/projects/{safe_slug}/report'>📋 Latest report</a>"
        f"<a class='btn' href='/projects/{safe_slug}/damage-report'>🩹 Damage-control report</a>"
        f"<a class='btn' href='/projects/{safe_slug}/flow-diagram'>🌳 Flow diagram</a>"
        f"<a class='btn' href='/projects/{safe_slug}/crawls'>🕸 Crawls</a>"
        f"<a class='btn' href='/projects/{safe_slug}/edit'>⚙ Project settings</a>"
        "<a class='btn' href='/live'>▶ Watch live</a>"
        "</div>",
        title="Actions",
    )
    if case_count:
        return card
    return theme.empty_state(
        "🧪",
        "No cases yet — nothing can run until this project has at least one. "
        "A case is one claim about the product, checked in a real browser.",
        f"<a class='btn btn-primary' href='/projects/{safe_slug}/cases/new'>"
        "+ Add the first case</a> "
        # AT-241: hand-writing cases was the ONLY remedy offered here, which made
        # the product's own generator invisible to the operator and T-100's
        # "onboard without touching the CLI" false. The learning route is the
        # other half of the way out of a cold start.
        f"<a class='btn' href='/projects/{safe_slug}/flowspec'>"
        "Teach it from a recording</a>",
    ) + card


# -- home-page cards (moved from ui/app.py by T-204 to keep app.py under 300 lines) --

def _ago(then: datetime, now: datetime) -> str:
    """Whole-unit age in the largest unit that fits ("3 hours ago"); never rounds up to 0."""
    seconds = max(int((now - then).total_seconds()), 0)
    for unit, size in (("day", 86400), ("hour", 3600), ("minute", 60)):
        if seconds >= size:
            n = seconds // size
            return f"{n} {unit}{'s' if n != 1 else ''} ago"
    return "just now"


def _last_change(store: ProjectStore) -> datetime | None:
    """When the project's own definition (settings or cases) last changed on disk."""
    stamps = [p.stat().st_mtime for p in (store.paths.config, store.paths.cases) if p.exists()]
    return datetime.fromtimestamp(max(stamps), UTC) if stamps else None


def _has_corrupt_run(store: ProjectStore) -> bool:
    """A run dir whose run.json exists but will not load -- `valid_runs_newest_first` skips
    it silently, which would make the project read as "never run" (U15 forbids that)."""
    runs_dir = store.paths.runs_dir
    if not runs_dir.exists():
        return False
    for path in runs_dir.iterdir():
        if path.is_dir() and (path / "run.json").exists():
            try:
                store.load_run(path.name)
            except ValueError:
                return True
    return False


def _standing(slug: str) -> dict:
    """One project's home-page standing, read from persisted evidence only (U15/U4).

    `state` is "none" (no runs), "unreadable" (any evidence failed to load) or "ok";
    "ok" carries the latest verdict `counts`, its `ago` age and whether it is `stale`
    (older than the project's last change). `cases` is None when it cannot be read."""
    store = ProjectStore(slug)
    try:
        cases = len(store.list_cases())
        project = store.load_project()
        if _has_corrupt_run(store):
            raise ValueError("corrupt run")
        runs = valid_runs_newest_first(store)
        counts = _run_counts(store, runs[0].id) if runs else {}
    except (ValueError, OSError):
        return {"state": "unreadable", "cases": None, "name": slug}
    name = project.name if project else slug
    if not runs:
        return {"state": "none", "cases": cases, "name": name}
    now = datetime.now(UTC)
    when = runs[0].finished_at or runs[0].created_at
    when = when if when.tzinfo else when.replace(tzinfo=UTC)
    changed = _last_change(store)
    return {"state": "ok", "cases": cases, "name": name, "counts": counts,
            "ago": _ago(when, now), "stale": changed is not None and when < changed}


def _status_html(standing: dict) -> str:
    if standing["state"] == "unreadable":
        return "<span class='meta'>unreadable</span>"
    if standing["state"] == "none":
        return "<span class='meta'>no runs</span>"
    counts = standing["counts"]
    badges = ("".join(theme.badge(escape(k), count=v) for k, v in counts.items())
              or "<span class='meta'>no verdicts recorded</span>")
    stale = (" <span class='meta'>stale: project changed since this run</span>"
             if standing["stale"] else "")
    return f"{badges} <span class='meta'>{standing['ago']}</span>{stale}"


def project_card(slug: str) -> str:
    standing = _standing(slug)
    cases = standing["cases"]
    count = ("" if cases is None
             else f"{cases} case{'s' if cases != 1 else ''}")
    safe_slug = escape(slug)
    return (
        f"<a class='project-card' href='/projects/{safe_slug}'>"
        f"<span class='name'>{escape(standing['name'])}</span>"
        f"<span class='meta'>{count}</span>"
        f"<span class='card-status'>{_status_html(standing)}</span></a>"
    )


def portfolio_stats(slugs: list[str]) -> str:
    """Aggregate health across every onboarded project -- the piece a non-technical
    user needs before clicking into any one project (feedback 2026-09-06; U15). A
    project whose evidence cannot be read is named and counted as skipped, never
    folded into a zero."""
    standings = {slug: _standing(slug) for slug in slugs}
    ok = [s for s in standings.values() if s["state"] == "ok"]
    skipped = [slug for slug, s in standings.items() if s["state"] == "unreadable"]
    never_run = sum(1 for s in standings.values() if s["state"] == "none")
    failing = sum(1 for s in ok if s["counts"].get("FAIL") or s["counts"].get("BLOCKED"))
    healthy = sum(1 for s in ok if s["counts"] and not (
        s["counts"].get("FAIL") or s["counts"].get("BLOCKED")))
    stale = sum(1 for s in ok if s["stale"])
    total_cases = sum(s["cases"] or 0 for s in standings.values())
    tiles = [
        theme.stat(str(len(slugs)), "projects"),
        theme.stat(str(total_cases), "cases"),
        theme.stat(str(len(ok)), "have run"),
        theme.stat(str(healthy), "latest run clean"),
    ]
    if failing:
        tiles.append(theme.stat(str(failing), "latest run failing"))
    if never_run:
        tiles.append(theme.stat(str(never_run), "never run"))
    if stale:
        tiles.append(theme.stat(str(stale), "latest run stale"))
    if skipped:
        names = ", ".join(escape(s) for s in skipped)
        tiles.append(theme.stat(str(len(skipped)), f"skipped (unreadable): {names}"))
    return f"<div class='stat-row'>{''.join(tiles)}</div>"
