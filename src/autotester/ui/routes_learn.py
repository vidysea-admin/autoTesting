"""The learning loop on screen — review the FlowSpec, generate cases, see the asks.

Contract: qa/contracts/ui.md (U1-U6), review-gate R1-R3, expand.md X1.

**AT-241 — the cold start was a dead end.** A freshly onboarded product's only
route to being runnable was hand-writing cases one at a time. INGEST was
CLI-only, the review gate was CLI-only, and EXPAND — the feature this repo's own
ledger calls "the differentiator" — had no entry point at all. So T-100's
acceptance note, *"full onboarding → report without touching the CLI"*, was
false, and the business-truth campaign proved it by driving the real UI.

Three surfaces close that loop:

* **the review page** — what the system thinks it learned, and the gate, which
  swings **both ways**. A review page with only an Approve button is a rubber
  stamp, not a gate.
* **Generate cases** — EXPAND's button. Persisting stays with the caller because
  expand.md's no-fire list puts it there, so this route saves what it gets.
* **the request queue** — the first place the product's "ask me for a video"
  promise is visible to the human it is asking. A `VideoRequest` written to a
  file nothing renders is indistinguishable from not asking.

Plain server-rendered HTML, no JS framework (ui.md's no-fire list), matching
`routes_cases.py`.
"""

from __future__ import annotations

from html import escape

from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from autotester.browser.secrets import SecretStore
from autotester.core.paths import ProjectPaths, RepoDocs
from autotester.providers import ProviderError, for_role, why_unavailable
from autotester.schema.enums import ReviewStatus
from autotester.stages import review as review_stage
from autotester.stages.expand import expand, propose_cases
from autotester.store.project_store import ProjectStore
from autotester.ui import theme
from autotester.ui.helpers import _load_project_or_404, _refuse_unsafe_submission

router = APIRouter()

TONE = {ReviewStatus.APPROVED: "good", ReviewStatus.NEEDS_EDIT: "warn",
        ReviewStatus.DRAFT: "neutral"}


def _refusal(slug: str, title: str, message: str, onward: str) -> HTMLResponse:
    """A refusal an operator reaches by clicking a button, as a PAGE.

    AT-244: raising `HTTPException` here hands a non-technical user the raw
    `{"detail": ...}` blob, which tells them nothing about what to do next. A
    refusal is part of the interface, so it gets the same frame as every other
    page and always carries a way onward."""
    body = theme.card(
        f"<p>{escape(message)}</p><p style='margin-top:14px'>{onward}</p>", title=title)
    return HTMLResponse(theme.page(title, body, active_slug=slug), status_code=400)


def _link(href: str, text: str) -> str:
    return f"<a class='btn' href='{escape(href)}'>{escape(text)}</a>"


@router.get("/projects/{slug}/flowspec", response_class=HTMLResponse)
def flowspec_page(slug: str) -> str:
    """What the system believes it learned, and the gate over it."""
    store, project = _load_project_or_404(slug)
    spec = store.load_flowspec()
    # theme.breadcrumb and theme.empty_state take CALLER-ESCAPED labels -- their own
    # docstring says so, and U5 is the reason. A project named
    # `<script>alert(1)</script>` is the probe every other route already survives.
    name = escape(project.name)
    crumbs = theme.breadcrumb(("Projects", "/"), (name, f"/projects/{slug}"),
                              ("FlowSpec", None))
    if spec is None:
        body = crumbs + theme.card(theme.empty_state(
            "🎬",
            f"No flowspec yet for {name}. AutoTester has not been shown this "
            f"product, so it cannot generate cases for it.",
            _link(f"/projects/{slug}/sources", "Add a recording")
            + " " + _link(f"/projects/{slug}/cases/new", "Write a case by hand"),
        ), title="Nothing learned yet")
        return theme.page(f"{name} · FlowSpec", body, active_slug=slug)

    corrective_evidence = theme.card(
        "<p class='muted'>Show AutoTester another recording when this map is incomplete "
        "or wrong.</p>" + _link(f"/projects/{slug}/sources", "Add a recording"),
        title="Correct what it learned",
    )
    return theme.page(
        f"{name} · FlowSpec",
        crumbs + _learned_card(spec, name) + corrective_evidence + _gate_cards(slug, spec),
        active_slug=slug,
    )


def _learned_card(spec, name: str) -> str:
    """What the system believes it learned, as a card."""
    status = spec.review.status
    screens = "".join(
        f"<tr><td><strong>{escape(s.name)}</strong></td>"
        f"<td><code>{escape(s.url_pattern or '—')}</code></td>"
        f"<td>{len(s.signals)} signal(s)</td></tr>"
        for s in spec.screens) or "<tr><td colspan='3'>no screens</td></tr>"
    flows = "".join(
        f"<tr><td>{escape(f.name)}</td><td>{len(f.steps)} step(s)</td></tr>"
        for f in spec.flows) or "<tr><td colspan='2'>no flows</td></tr>"

    reviewed = (f"reviewed by {escape(spec.review.by)}" if spec.review.by else "not yet signed")
    note = f"<p class='muted'>{escape(spec.review.note)}</p>" if spec.review.note else ""

    return theme.card(
        f"<p>{theme.pill(status.value, TONE.get(status, 'neutral'))} &nbsp; {reviewed}</p>"
        f"{note}"
        f"<table><thead><tr><th>Screen</th><th>URL pattern</th><th>Signals</th></tr></thead>"
        f"<tbody>{screens}</tbody></table>"
        f"<table><thead><tr><th>Flow</th><th>Steps</th></tr></thead>"
        f"<tbody>{flows}</tbody></table>",
        title=f"What AutoTester learned about {name}")


def _gate_cards(slug: str, spec) -> str:
    """The review gate, and -- only once approved -- the Generate button.

    Both directions are here on purpose: a review page with only an Approve
    button is a rubber stamp, not a gate."""
    gate = f"""
      <form method="post" action="/projects/{escape(slug)}/flowspec/approve" class="row">
        <input name="by" placeholder="your name" required>
        <input name="note" placeholder="note (optional)">
        <button type="submit">Approve</button>
      </form>
      <form method="post" action="/projects/{escape(slug)}/flowspec/request-edit" class="row">
        <input name="by" placeholder="your name" required>
        <input name="note" placeholder="what is wrong" required>
        <button type="submit" class="secondary">Request edit</button>
      </form>"""

    body = theme.card(gate, title="Review gate")
    if spec.review.status is ReviewStatus.APPROVED:
        body += theme.card(
            f"<form method='post' action='/projects/{escape(slug)}/cases/generate'>"
            f"<button type='submit'>Generate cases</button></form>"
            f"<p class='muted'>Covers best / worst / edge for every flow above.</p>",
            title="Generate test cases")
    return body


def _signed(slug: str, by: str, note: str) -> tuple[ProjectStore, str, str] | HTMLResponse:
    """A signer and a guarded note, or a themed refusal page.

    An approval nobody signed is not an approval (R2), and `flowspec.json` is a
    git-tracked file in a PUBLIC repo, so its free text gets the same credential
    guard the case form has (U8/U9)."""
    store, project = _load_project_or_404(slug)
    if not by.strip():
        return _refusal(
            slug, "This review is not signed",
            "An approval needs a name so the audit trail says who reviewed it.",
            _link(f"/projects/{slug}/flowspec", "Return to the review"),
        )
    secrets = SecretStore.load(project, ProjectPaths(slug).env_file, strict=False)
    try:
        _refuse_unsafe_submission([("name", by), ("note", note)], project, secrets)
    except HTTPException as exc:
        return _refusal(
            slug, "This review cannot be saved", str(exc.detail),
            _link(f"/projects/{slug}/flowspec", "Return to the review"),
        )
    return store, by.strip(), note.strip()


@router.post("/projects/{slug}/flowspec/approve")
def approve_flowspec(
    slug: str, by: str = Form(""), note: str = Form("")
) -> Response:
    signed = _signed(slug, by, note)
    if isinstance(signed, HTMLResponse):
        return signed
    store, signer, text = signed
    spec = store.load_flowspec()
    if spec is None:
        return _refusal(
            slug, "Nothing to approve", "There is no flowspec to approve yet.",
            _link(f"/projects/{slug}/sources", "Add a recording"),
        )
    store.save_flowspec(review_stage.approve(spec, signer, text or None))
    return RedirectResponse(f"/projects/{slug}/flowspec", status_code=303)


@router.post("/projects/{slug}/flowspec/request-edit")
def request_edit_flowspec(slug: str, by: str = Form(""),
                          note: str = Form("")) -> Response:
    """The other direction. Without it the page is a rubber stamp."""
    signed = _signed(slug, by, note)
    if isinstance(signed, HTMLResponse):
        return signed
    store, signer, text = signed
    if not text:
        return _refusal(
            slug, "Say what needs to change",
            "Describe what is wrong so the next learning pass can fix it.",
            _link(f"/projects/{slug}/flowspec", "Return to the review"),
        )
    spec = store.load_flowspec()
    if spec is None:
        return _refusal(
            slug, "Nothing to send back", "There is no flowspec to send back yet.",
            _link(f"/projects/{slug}/sources", "Add a recording"),
        )
    store.save_flowspec(review_stage.request_edit(spec, signer, text))
    return RedirectResponse(f"/projects/{slug}/flowspec", status_code=303)


@router.post("/projects/{slug}/cases/generate")
def generate_cases(slug: str):
    """EXPAND's button — AT-239's UI half.

    Refusals are pages, not JSON: this is a button a non-technical operator
    clicks, and every reason it can fail has a different next action."""
    store, project = _load_project_or_404(slug)
    spec = store.load_flowspec()
    if spec is None:
        return _refusal(
            slug, "Nothing to generate from",
            f"{project.name} has no flowspec yet, so there are no flows to expand.",
            _link(f"/projects/{slug}/sources", "Add a recording"))
    if spec.review.status is not ReviewStatus.APPROVED:
        return _refusal(
            slug, "The flowspec is not approved yet",
            f"Generating from an unreviewed flowspec would build cases on top of "
            f"whatever the model guessed. It is currently {spec.review.status.value}.",
            _link(f"/projects/{slug}/flowspec", "Review it"))

    try:
        store.stage_case_proposals(propose_cases(spec))
        store.preflight_case_proposals(spec)
    except ValueError as exc:
        return _refusal(
            slug, "Case proposals need human review", str(exc),
            f"<p>Review/prune with <code>autotester expand {escape(slug)} --proposals</code>; "
            "use --approve or --prune with a proposal ID and --by your name.</p>")
    try:
        why = why_unavailable(provider := for_role(project, "agent"))  # LL2: the one factory
    except ProviderError as exc:
        why = str(exc)
    if why:
        return _refusal(slug, "No model provider configured",
                        f"Generating cases needs a model. {why}, so nothing was generated.",
                        _link(f"/projects/{slug}/env", "Add a credential"))

    try:  # AT-264: a failure after the gates (model, or the secret guard) is a page, not a 500
        cases = expand(spec, provider, RepoDocs(), store=store)
    except (ProviderError, ValueError) as exc:
        return _refusal(
            slug, "The model could not complete this",
            "Generating cases failed partway through: "
            f"{exc if isinstance(exc, ProviderError) else 'a prompt was refused unsent'}",
            _link(f"/projects/{slug}/env", "Check the provider's credentials"))
    for case in cases:
        store.add_case(case)
    return RedirectResponse(f"/projects/{slug}/cases", status_code=303)


@router.get("/projects/{slug}/requests", response_class=HTMLResponse)
def requests_page(slug: str) -> str:
    """What the system is asking a human to record.

    coverage.md's no-fire list makes surfacing a `VideoRequest` T-100's job.
    Until this page there was no such surface, so the request went to a file
    nothing rendered — which, from the human's side, is not asking at all."""
    store, project = _load_project_or_404(slug)
    requests = store.list_requests()
    name = escape(project.name)
    crumbs = theme.breadcrumb(("Projects", "/"), (name, f"/projects/{slug}"),
                              ("Video requests", None))

    if not requests:
        body = crumbs + theme.card(theme.empty_state(
            "📭",
            f"AutoTester is asking for nothing right now — no video requests are open "
            f"for {name}.",
            _link(f"/projects/{slug}/flowspec", "See what it has learned"),
        ), title="No open requests")
        return theme.page(f"{name} · Video requests", body, active_slug=slug)

    rows = "".join(
        f"<tr><td>{theme.pill(r.status.value)}</td>"
        f"<td>{escape(r.prompt)}</td>"
        f"<td><code>{escape(r.gap_id)}</code></td></tr>"
        for r in requests)
    body = crumbs + theme.card(
        f"<p class='muted'>{len(requests)} open ask(s). Each one is a screen AutoTester "
        f"met and could not recognise.</p>"
        f"<table><thead><tr><th>Status</th><th>What to record</th><th>Gap</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>",
        title=f"{name} — what to record next")
    return theme.page(f"{name} · Video requests", body, active_slug=slug)
