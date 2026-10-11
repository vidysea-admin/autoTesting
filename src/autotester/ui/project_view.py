"""The project page's action card — the operator's control panel for one product.

Split out of `app.py` when that file crossed its 300-line cap. It sits beside
`case_form.py`, `crawl_view.py` and `env_editor.py`, which are the same idea:
`app.py` owns routes, these own the markup a route renders.
"""

from __future__ import annotations

from autotester.ui import theme


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
