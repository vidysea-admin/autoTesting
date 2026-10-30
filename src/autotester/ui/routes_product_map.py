"""Product-map cards, recorded journeys, and guarded learned-frame serving."""

from __future__ import annotations

import re
from html import escape

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

from autotester.store.run_store import local_blob
from autotester.ui import theme
from autotester.ui.helpers import _load_project_or_404, _require_safe_id

router = APIRouter()
_FRAME_RE = re.compile(r"^\d{8}\.png$")


def _journey_html(journey) -> str:
    stops = "".join(
        f"<li><span class='tree-node'><strong>{escape(stop.name)}</strong>"
        f"<span class='meta'> {stop.t_start:.1f}s"
        f"{' · ' + escape(stop.what_user_does) if stop.what_user_does else ''}</span>"
        "</span></li>"
        for stop in journey.stops
    ) or "<li><span class='meta'>no stops learned</span></li>"
    return theme.card(f"<ul class='flow-tree'>{stops}</ul>", title=escape(journey.label))


def _screen_card(slug: str, screen) -> str:
    image = ""
    if screen.frame_ref:
        parts = screen.frame_ref.split("/")
        if len(parts) == 4:
            image = (
                f"<img loading='lazy' alt='{escape(screen.name)}' "
                f"src='/projects/{escape(slug)}/frames/{escape(parts[1])}/{escape(parts[3])}'>"
            )
    fields = ", ".join(escape(value) for value in screen.fields) or "—"
    controls = ", ".join(escape(value) for value in screen.ui_elements) or "—"
    visits = ", ".join(
        f"{escape(visit.source_id)} @ {visit.t_start:.1f}s" for visit in screen.visits
    )
    body = (
        image + f"<p>{escape(screen.purpose or 'Purpose not learned yet.')}</p>"
        f"<p><strong>URL</strong> <code>{escape(screen.url_pattern or '—')}</code></p>"
        f"<p><strong>Fields</strong> {fields}</p>"
        f"<p><strong>Controls</strong> {controls}</p>"
        f"<p class='meta'>{len(screen.visits)} visit(s): {visits}</p>"
    )
    return theme.card(body, title=escape(screen.name))


@router.get("/projects/{slug}/product-map", response_class=HTMLResponse)
def product_map_page(slug: str) -> str:
    store, project = _load_project_or_404(slug)
    screen_map = store.load_screen_map()
    name = escape(project.name)
    crumbs = theme.breadcrumb(("Projects", "/"), (name, f"/projects/{slug}"),
                              ("Product map", None))
    if screen_map is None:
        body = crumbs + "<h1>Product map</h1>" + theme.empty_state(
            "🗺", "No analysed recording has produced a product map yet.",
            f"<a class='btn' href='/projects/{escape(slug)}/sources'>Analyze a recording</a>",
        )
        return theme.page(f"{name} · Product map", body, active_slug=slug)
    screens = "".join(_screen_card(slug, screen) for screen in screen_map.screens)
    journeys = "".join(_journey_html(journey) for journey in screen_map.journeys)
    body = (
        crumbs + "<h1>Product map</h1>"
        f"<p class='subtitle'>{len(screen_map.screens)} learned screen(s) across "
        f"{len(screen_map.source_ids)} recording(s).</p>"
        + (f"<div class='project-grid'>{screens}</div>" if screens else
           theme.empty_state("🗺", "The analyses contain no screens."))
        + theme.card(journeys or "<p class='meta'>no journeys learned</p>",
                     title="Recorded journeys")
    )
    return theme.page(f"{name} · Product map", body, active_slug=slug)


@router.get("/projects/{slug}/frames/{source_id}/{name:path}")
def learned_frame(slug: str, source_id: str, name: str) -> FileResponse:
    store, _project = _load_project_or_404(slug)
    _require_safe_id(source_id, "source_id")
    if not _FRAME_RE.fullmatch(name):
        raise HTTPException(400, "invalid frame name")
    path = local_blob(store.paths.source_frames_dir(source_id) / name)
    if not path.is_file():
        raise HTTPException(404, "frame not found")
    return FileResponse(path, media_type="image/png")
