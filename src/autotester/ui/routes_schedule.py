"""The schedule routes (TS1): view the card, save, pause, resume and delete one project's schedule.

The key lives in `auth/policy.py`: GET needs `project.view`, every POST `schedule.manage` on the
project (the login gate refuses first, with a 403, and the Origin guard runs before that). A
value that does not parse is refused with its field named and nothing is stored. The schedule is
`Project.schedule`; the scheduler core (`stages/scheduler.py`) reads it and is not touched here.
"""

from __future__ import annotations

from datetime import UTC, datetime
from html import escape

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from autotester.auth import audit
from autotester.auth.access import authorize, resource_for
from autotester.auth.context import current_principal
from autotester.schema.auth import PermissionKey
from autotester.schema.schedule import ScheduleConfig, ScheduleInvalid, ScheduleMode
from autotester.stages.schedule_store import project_records_path, purge_project
from autotester.stages.schedule_wiring import schedule_paths
from autotester.ui import schedule_view, theme
from autotester.ui.helpers import _load_project_or_404

router = APIRouter()


def can_manage(slug: str) -> bool:
    who = current_principal()
    return who is not None and authorize(who, PermissionKey.SCHEDULE_MANAGE, resource_for(slug))


def _form_data(form: dict[str, object], weekdays: list[str]) -> dict[str, object]:
    """The posted fields as a `ScheduleConfig` dict. Empty boxes mean 'not given'."""
    def text(name: str) -> str:
        return str(form.get(name) or "").strip()

    data: dict[str, object] = {"mode": text("mode") or "manual",
                               "timezone": text("timezone") or "UTC"}
    if text("fixed_at"):
        data["fixed_at"] = text("fixed_at")
    try:
        days = [int(d) for d in weekdays]
    except ValueError as exc:
        raise ScheduleInvalid("weekdays", "must be numbers 0 (Mon) to 6 (Sun)") from exc
    if days or text("weekly_at"):
        data["weekly"] = {"weekdays": days, "at": text("weekly_at")}
    lines = [ln.strip() for ln in text("one_offs").splitlines() if ln.strip()]
    try:
        data["one_offs"] = [datetime.fromisoformat(ln) for ln in lines]
    except ValueError as exc:
        raise ScheduleInvalid("one_offs", "each line must be YYYY-MM-DDTHH:MM") from exc
    return data


def _back(slug: str) -> Response:
    return RedirectResponse(f"/projects/{slug}/schedule", status_code=303)


def _who() -> str:
    who = current_principal()
    if who is None:
        raise HTTPException(401, "authentication required")
    return who.email


def _page(slug: str, *, error: str | None = None, draft: dict[str, object] | None = None,
          preview: ScheduleConfig | None = None) -> str:
    store, project = _load_project_or_404(slug)
    name = escape(project.name)
    body = (theme.breadcrumb(("Projects", "/"), (name, f"/projects/{escape(slug)}"),
                             ("Schedule", None))
            + "<h1>Schedule</h1>"
            + schedule_view.schedule_card(slug, project, store, manage=can_manage(slug),
                                          error=error, draft=draft, preview=preview))
    return theme.page(f"{name} - schedule", body, active_slug=slug)


@router.get("/projects/{slug}/schedule", response_class=HTMLResponse)
def schedule_page(slug: str) -> str:
    return _page(slug)


def _draft(form: object) -> dict[str, object]:
    """The typed values, kept so a refusal or a preview re-renders the form as the user left it."""
    out: dict[str, object] = {k: str(form.get(k) or "") for k in (  # type: ignore[attr-defined]
        "mode", "timezone", "fixed_at", "weekly_at", "one_offs")}
    out["weekdays"] = [str(v) for v in form.getlist("weekdays")]  # type: ignore[attr-defined]
    return out


@router.post("/projects/{slug}/schedule")
async def schedule_save(slug: str, request: Request) -> Response:
    store, project = _load_project_or_404(slug)
    owner = _who()
    form = await request.form()
    try:
        data = _form_data(dict(form), [str(v) for v in form.getlist("weekdays")])
        cfg = ScheduleConfig.parse_for_save({**data, "owner": owner}, now=datetime.now(UTC))
    except ScheduleInvalid as exc:
        return HTMLResponse(_page(slug, error=f"{exc.field}: {exc.reason}", draft=_draft(form)),
                            status_code=400)
    if form.get("intent") == "preview":
        return HTMLResponse(_page(slug, preview=cfg, draft=_draft(form)))
    store.save_project(project.model_copy(update={"schedule": cfg}))
    audit.record_action(actor=owner, target=slug, action="schedule.save")
    return _back(slug)


def _set_paused(slug: str, paused: bool) -> Response:
    store, project = _load_project_or_404(slug)
    cfg = project.schedule
    if cfg is None or cfg.mode is ScheduleMode.MANUAL:
        raise HTTPException(400, "this project has no schedule to pause or resume")
    store.save_project(project.model_copy(update={"schedule": cfg.model_copy(
        update={"paused": paused})}))
    audit.record_action(actor=_who(), target=slug,
                        action="schedule.pause" if paused else "schedule.resume")
    return _back(slug)


@router.post("/projects/{slug}/schedule/pause")
def schedule_pause(slug: str) -> Response:
    return _set_paused(slug, True)


@router.post("/projects/{slug}/schedule/resume")
def schedule_resume(slug: str) -> Response:
    return _set_paused(slug, False)


@router.post("/projects/{slug}/schedule/delete")
def schedule_delete(slug: str) -> Response:
    store, project = _load_project_or_404(slug)
    paths = schedule_paths()
    purge_project(paths.claims, project_records_path(paths.records, slug), slug)
    store.save_project(project.model_copy(update={"schedule": None}))
    audit.record_action(actor=_who(), target=slug, action="schedule.delete")
    return _back(slug)
