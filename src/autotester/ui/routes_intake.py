"""The Google Drive door of Add-videos: paste a link, get a background job and its result page.

Contract: team-intake.md TI7/TI8/TI10-seam/TI11, hosting.md HO32/HO33. The pasted text is parsed
to a Drive id by `parse_drive_link` (a hostile link is refused without being echoed and makes no
job). The fetch runs on a worker thread so a long download never hangs the request; the page for
the job polls itself while it is `fetching`. The worker asks the gate again before it fetches a
byte, because the member's permission may have changed while the job waited.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from contextlib import suppress
from html import escape

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from autotester.core.ids import ulid
from autotester.schema.intake import DriveJob, DriveRef, IntakeActor
from autotester.sources.drive_intake import default_drive, intake_drive
from autotester.sources.drive_jobs import effective_state, load_job, save_job
from autotester.sources.drive_link import DriveLinkError, parse_drive_link
from autotester.stages.ingest import project_redactor
from autotester.store.project_store import ProjectStore
from autotester.ui import theme
from autotester.ui.helpers import _load_project_or_404, _require_slug
from autotester.ui.intake_gate import IntakeRefused, get_gate
from autotester.ui.intake_upload import gate_refusal, refusal_page, report_table
from autotester.ui.upload_stream import UploadRefused, read_small_form

router = APIRouter()
log = logging.getLogger(__name__)

drive_factory = default_drive
"""How a job gets its Drive. Looked up per job so a test (or T-204) can replace it."""
WAIT_FOR_QUICK_JOB_S = 3.0
_FAILED = ("The fetch stopped unexpectedly. Nothing was added. Try again, or upload the file "
           "directly.")


def _run_job(store: ProjectStore, job: DriveJob, ref: DriveRef, actor: IntakeActor) -> None:
    """The worker: recheck the gate, fetch, and record the outcome. Never raises."""
    root, slug = store.paths.root, store.paths.slug
    try:
        try:
            get_gate().recheck(actor, slug)
        except IntakeRefused as exc:
            save_job(root, job.model_copy(update={"state": "refused", "message": exc.message}))
            return
        job = job.model_copy(update={"state": "fetching"})
        save_job(root, job)
        report = intake_drive(store, ref, drive_factory(store), uploaded_by=actor.email,
                              scrub=project_redactor(slug).scrub)
        save_job(root, job.model_copy(update={"state": "done", "report": report}))
    except Exception:
        log.exception("drive job %s failed", job.id)
        with suppress(OSError):
            save_job(root, job.model_copy(update={"state": "failed", "message": _FAILED}))


@router.post("/projects/{slug}/sources/drive")
async def add_drive_link(request: Request, slug: str) -> Response:
    """Gate, parse the link, queue a job, and show it (done already if the fetch was quick)."""
    try:
        actor = get_gate().check(request, slug)
    except IntakeRefused as exc:
        return gate_refusal(slug, exc)
    store, _project = _load_project_or_404(slug)
    try:
        form = await read_small_form(request)
        ref = parse_drive_link(form.get("link", ""))
    except UploadRefused as exc:
        return refusal_page(slug, exc.message, title="Not a Drive link", status=exc.status,
                            link_text="Back to sources")
    except DriveLinkError as exc:
        return refusal_page(slug, str(exc), title="Not a Drive link", link_text="Back to sources")
    job = DriveJob(id=ulid(), project=slug, drive_id=ref.id)
    save_job(store.paths.root, job)
    worker = threading.Thread(target=_run_job, args=(store, job, ref, actor), daemon=True,
                              name=f"drive-job-{job.id}")
    worker.start()
    await asyncio.to_thread(worker.join, WAIT_FOR_QUICK_JOB_S)
    return RedirectResponse(f"/projects/{slug}/sources/drive/{job.id}", status_code=303)


def _job_card(slug: str, job: DriveJob, state: str) -> str:
    back = (f"<p style='margin-top:14px'><a class='btn' href='/projects/{escape(slug)}/sources'>"
            "Back to sources</a></p>")
    if state in ("queued", "fetching"):
        return (f"<p>Status: <strong>{escape(state)}</strong>. Fetching from Google Drive; this "
                "page refreshes itself.</p>" + back)
    if state == "done" and job.report is not None:
        return report_table(job.report) + back
    if state == "interrupted":
        return ("<p>This fetch was interrupted (the server restarted). Nothing was added. "
                "Paste the link again.</p>" + back)
    return f"<p>Status: <strong>{escape(state)}</strong>. {escape(job.message or '')}</p>" + back


@router.get("/projects/{slug}/sources/drive/{job_id}", response_class=HTMLResponse)
def drive_job_page(slug: str, job_id: str) -> HTMLResponse:
    _require_slug(slug)
    store, _project = _load_project_or_404(slug)
    job = load_job(store.paths.root, slug, job_id)
    if job is None:
        raise HTTPException(404, "no such fetch")
    state = effective_state(job)
    title = {"done": "Drive fetch finished", "refused": "Drive fetch refused"}.get(
        state, "Drive fetch")
    page = theme.page("Drive fetch", theme.card(_job_card(slug, job, state), title=title),
                      active_slug=slug)
    if state in ("queued", "fetching"):
        page = page.replace("<!doctype html>", "<!doctype html><meta http-equiv=\"refresh\" "
                                               "content=\"3\">", 1)
    return HTMLResponse(page)
