"""The Add-videos upload door: one form field takes a recording or a zip of them.

Contract: team-intake.md TI3/TI5 (the per-member table), TI9 (the limit), TI10 seam, TI11;
hosting.md HO30. Order matters and is the point of this module: the gate runs first and a refusal
reads no body; the body is streamed to a private staging folder under the limit; only then is the
project's secret check run on the label and the bytes handed to the shared commit code
(`commit_video` for a recording, `expand_zip` for a zip). The staging folder is removed on every
exit, and `uploaded_by` is whatever the gate returned, never a form field.
"""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from html import escape

from fastapi import Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from autotester.browser.secrets import SecretStore
from autotester.core.ids import ulid
from autotester.core.paths import ProjectPaths, work_dir
from autotester.core.upload_limit import UploadLimit, human_bytes, read_max_upload_bytes
from autotester.schema.intake import IntakeActor, IntakeReport, IntakeStatus, UploadOrigin
from autotester.sources.intake_commit import IntakeBusy, commit_video, intake_session
from autotester.sources.zip_intake import expand_zip
from autotester.sources.zip_names import display_name
from autotester.stages.ingest import project_redactor, require_recording_suffix
from autotester.ui import theme
from autotester.ui.helpers import _load_project_or_404, _refuse_unsafe_submission
from autotester.ui.intake_gate import IntakeRefused, get_gate
from autotester.ui.upload_stream import StagedUpload, UploadRefused, stream_upload

_HEADINGS = {IntakeStatus.OK: "Added", IntakeStatus.PARTIAL: "Partial: some were not added",
             IntakeStatus.FAILED: "Nothing was added"}


def refusal_page(slug: str, message: str, *, title: str = "Recording not found",
                 status: int = 400, link_text: str = "Try another path") -> HTMLResponse:
    body = theme.card(
        f"<p>{escape(message)}</p><p style='margin-top:14px'>"
        f"<a class='btn' href='/projects/{escape(slug)}/sources'>{escape(link_text)}</a></p>",
        title=title)
    return HTMLResponse(theme.page(escape(title), body, active_slug=slug), status_code=status)


def gate_refusal(slug: str, exc: IntakeRefused) -> HTMLResponse:
    return refusal_page(slug, exc.message, title="Not allowed", status=exc.status,
                        link_text="Back to sources")


def report_table(report: IntakeReport) -> str:
    """The per-member table: one row per member, every name and reason escaped."""
    rows = "".join(
        f"<tr><td><code>{escape(m.member)}</code></td><td>{escape(m.outcome.value)}</td>"
        f"<td>{escape(m.reason or '')}</td></tr>" for m in report.members)
    notes = "".join(f"<p class='meta'>{escape(n)}</p>" for n in report.notes)
    counts = ", ".join(f"{n} {name}" for name, n in report.counts.items() if n)
    return (f"<p>{escape(counts or 'no files')}</p>{notes}"
            "<table><thead><tr><th>File</th><th>Result</th><th>Why</th></tr></thead>"
            f"<tbody>{rows}</tbody></table>")


def report_page(slug: str, report: IntakeReport) -> HTMLResponse:
    heading = f"{_HEADINGS[report.status]}: {escape(report.archive)}"
    back = f"<p style='margin-top:14px'><a class='btn' href='/projects/{escape(slug)}/sources'>" \
           "Back to sources</a></p>"
    page = theme.page("Add videos", theme.card(report_table(report) + back, title=heading),
                      active_slug=slug)
    return HTMLResponse(page)


def intake_forms(slug: str, limit: UploadLimit) -> str:
    """The two Add-videos forms (HO30: the page states the current limit)."""
    safe = escape(slug)
    upload = f"""
      <form method="post" enctype="multipart/form-data" action="/projects/{safe}/sources/upload">
        <div class="field"><label for="upload-label">What this recording shows</label>
          <input id="upload-label" name="label" placeholder="Trainer onboarding - edge cases">
        </div>
        <div class="field"><label for="recording">A recording, or a .zip of recordings</label>
          <input id="recording" type="file" name="recording" required accept="video/*,.zip">
          <span class="hint">Largest file accepted: {escape(human_bytes(limit.bytes))}. A .zip
          is opened and each video in it is added; anything that is not a video is listed and
          skipped.</span>
        </div>
        <button class="btn btn-primary" type="submit">Upload</button>
      </form>"""
    drive = f"""
      <form method="post" action="/projects/{safe}/sources/drive">
        <div class="field"><label for="drive-link">A Google Drive link</label>
          <input id="drive-link" name="link" required placeholder="https://drive.google.com/...">
          <span class="hint">A video, a zip, or a folder of videos. The file must be shared
          with the server's Google account or with anyone who has the link.</span>
        </div>
        <button class="btn btn-primary" type="submit">Fetch from Drive</button>
      </form>"""
    return theme.card(upload, title="Upload videos") + theme.card(drive, title="From Google Drive")


def _commit_recording(store, staged: StagedUpload, label: str, actor: IntakeActor, scrub):
    suffix = require_recording_suffix(staged.filename.replace("\\", "/").rsplit("/", 1)[-1])
    with intake_session(store):
        commit_video(store, staged.path, digest=staged.sha256, suffix=suffix,
                     label=label or None, uploaded_by=actor.email,
                     uploaded_at=datetime.now(UTC),
                     origin=UploadOrigin(file_name=scrub(display_name(staged.filename))))


async def handle_upload(request: Request, slug: str) -> Response:
    """POST /projects/{slug}/sources/upload: gate, stream under the limit, then commit."""
    try:
        actor = get_gate().check(request, slug)
    except IntakeRefused as exc:
        return gate_refusal(slug, exc)
    store, project = _load_project_or_404(slug)
    limit = read_max_upload_bytes(store.paths.root)
    staging = work_dir(store.paths.root) / "uploads" / slug / ulid()
    try:
        staged = await stream_upload(request, staging, limit.bytes)
        label = staged.fields.get("label", "").strip()
        secrets = SecretStore.load(project, ProjectPaths(slug).env_file, strict=False)
        _refuse_unsafe_submission([("label", label)], project, secrets)
        scrub = project_redactor(slug).scrub
        if staged.is_zip:
            report = await run_in_threadpool(
                expand_zip, store, staged.path, archive_name=staged.filename,
                uploaded_by=actor.email, scrub=scrub)
            return report_page(slug, report)
        await run_in_threadpool(_commit_recording, store, staged, label, actor, scrub)
    except UploadRefused as exc:
        return refusal_page(slug, exc.message, title="Upload refused", status=exc.status,
                            link_text="Back to sources")
    except IntakeBusy as exc:
        return refusal_page(slug, str(exc), title="Try again shortly", status=503,
                            link_text="Back to sources")
    except OSError:
        return refusal_page(slug, "The uploaded recording could not be stored.",
                            title="Upload failed", status=500, link_text="Back to sources")
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return RedirectResponse(f"/projects/{slug}/sources", status_code=303)
