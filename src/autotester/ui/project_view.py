"""The project page's action card — the operator's control panel for one product.

Split out of `app.py` when that file crossed its 300-line cap. It sits beside
`case_form.py`, `crawl_view.py` and `env_editor.py`, which are the same idea:
`app.py` owns routes, these own the markup a route renders.
"""

from __future__ import annotations

from html import escape

from autotester.stages.report_export import valid_runs_newest_first
from autotester.store.project_store import ProjectStore
from autotester.ui import team_run_view, theme
from autotester.ui.routes_report import _run_counts


def _credential_row() -> str:
    return (
        "<div class='intake-row credential-row'>"
        "<input name='credential_key' placeholder='DEMO_EMAIL'>"
        "<input type='password' name='credential_value' placeholder='value (stored only in .env)'>"
        "<input name='credential_domains' placeholder='app.example.com'>"
        "<input name='credential_description' placeholder='test account email'></div>"
    )


def _source_row() -> str:
    return (
        "<div class='intake-row source-row'><select name='source_kind'>"
        "<option value=''>Choose type</option><option value='url'>URL / Drive link</option>"
        "<option value='video'>Video path</option><option value='doc'>Document path</option>"
        "<option value='text'>Inline text</option></select>"
        "<input name='source_value' placeholder='link, path, or text'>"
        "<input name='source_label' placeholder='what this source teaches'></div>"
    )


def intake_form() -> str:
    """The single operator entry point for both taught and URL/account-only modes."""
    basics = (
        "<div class='field'><label>Project slug</label><input name='slug' "
        "placeholder='my-product' required></div>"
        "<div class='field'><label>Name</label><input name='name' required></div>"
        "<div class='field'><label>URL</label><input name='base_url' type='url' required "
        "placeholder='https://app.example.com/signin'></div>"
        "<div class='field'><label>Allowed domains</label><input name='allowed_domains' "
        "required placeholder='app.example.com'><span class='hint'>Comma-separated; the browser "
        "never leaves these hosts.</span></div>"
    )
    teaching = (
        "<div class='field'><label>Evals (one per line)</label>"
        "<textarea name='evals'></textarea></div>"
        "<div class='field'><label>Conditions / business rules</label>"
        "<textarea name='conditions'></textarea></div>"
        "<div class='field'><label>Use cases / taught flows</label>"
        "<textarea name='use_cases'></textarea></div>"
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
        f"<a class='btn' href='/projects/{safe_slug}/cases'>🧪 Cases</a>"
        f"<a class='btn' href='/projects/{safe_slug}/cases/new'>+ Add case</a>"
        f"<a class='btn' href='/projects/{safe_slug}/env'>🔑 Credentials</a>"
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

def _latest_run_status(slug: str) -> tuple[str | None, dict[str, int]]:
    """The latest run id (or None if the project has never run) and its verdict
    counts — same lookup `routes_report.py`'s report page already does per
    project, reused here rather than a second way to compute "how did the
    last run go" (ui.md U2/U4: real persisted state, never recomputed)."""
    store = ProjectStore(slug)
    runs = valid_runs_newest_first(store)
    if not runs:
        return None, {}
    return runs[0].id, _run_counts(store, runs[0].id)


def project_card(slug: str) -> str:
    store = ProjectStore(slug)
    project = store.load_project()
    name = escape(project.name) if project else escape(slug)
    case_count = len(store.list_cases())
    safe_slug = escape(slug)
    run_id, counts = _latest_run_status(slug)
    if run_id is None:
        status = "<span class='meta'>never run</span>"
    else:
        status = "".join(theme.badge(escape(k), count=v) for k, v in counts.items())
    return (
        f"<a class='project-card' href='/projects/{safe_slug}'>"
        f"<span class='name'>{name}</span>"
        f"<span class='meta'>{case_count} case{'s' if case_count != 1 else ''}</span>"
        f"<span class='card-status'>{status}</span></a>"
    )


def portfolio_stats(slugs: list[str]) -> str:
    """Aggregate health across every onboarded project — the piece a
    non-technical user needs before clicking into any one project (feedback
    2026-09-06: the home page showed names and case counts only, nothing
    saying what's actually passing or failing)."""
    total_cases = 0
    never_run = 0
    failing = 0
    healthy = 0
    for slug in slugs:
        total_cases += len(ProjectStore(slug).list_cases())
        _run_id, counts = _latest_run_status(slug)
        if _run_id is None:
            never_run += 1
        elif counts.get("FAIL", 0) > 0 or counts.get("BLOCKED", 0) > 0:
            failing += 1
        else:
            healthy += 1
    tiles = [
        theme.stat(str(len(slugs)), "projects"),
        theme.stat(str(total_cases), "cases"),
        theme.stat(str(healthy), "latest run clean"),
    ]
    if failing:
        tiles.append(theme.stat(str(failing), "latest run failing"))
    if never_run:
        tiles.append(theme.stat(str(never_run), "never run"))
    return f"<div class='stat-row'>{''.join(tiles)}</div>"
